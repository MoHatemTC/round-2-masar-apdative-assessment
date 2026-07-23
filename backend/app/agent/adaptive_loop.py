"""The adaptive competency-verification engine.  [THE CORE — this is what you build]

One HTTP turn = one call to `run_turn`. The whole loop state lives in `sessions.agent_state`
and is round-tripped every turn (stateless server, resumable client). Follow docs/ARCHITECTURE.md.

Flow per turn:
  • not initialized      → init_session, then pick a question
  • answer came in       → grade → estimate → check_convergence → pick the next question
  • all competencies done → finalize

Fill in every TODO. Keep the golden rules:
  - never send the answer key to the browser (strip before emitting)
  - one answer can't trigger the confidence stop (confidence ceiling)
  - idempotent + resumable
"""
from __future__ import annotations
from app.services.selection import select_competency_question
from app.services.grading import grade_answer
from app.services.estimation import estimate_level

# ── Tunable convergence knobs (start here; see ARCHITECTURE.md) ──────────────
CONFIDENCE_TARGET = 0.90
MAX_QUESTIONS = 10          # per competency
STABLE_WINDOW = 3           # same level N times in a row → converged
# Every answer-bearing field, stripped before a question reaches the browser. Covers all tool_types:
# MCQ key + explanation, coding tests, and the rubric keys the open-ended/voice/data-analysis graders read.
_ANSWER_KEYS = {"answer_key", "correct_id", "explanation", "test_cases", "expected_output",
                "evaluation_criteria", "expected_insights", "rubric"}
# ── Transient State Keys ──────────────
# Keys prefixed with '_' are strictly stripped in chat.py before DB persistence.
# _emit: The public question payload sent to the frontend.
# _complete: Boolean flag signaling the assessment has finished.
# _grading: Temporary hold of the grade output to pass between grade() and estimate().

LEVEL_BANDS = [(20, 1, "Novice"), (40, 2, "Developing"), (60, 3, "Proficient"),
               (80, 4, "Advanced"), (100, 5, "Expert")]


def _pct(level: int) -> int:
    return round(max(0, min(5, level)) / 5 * 100)


def _band(pct: float):
    for ceiling, lvl, label in LEVEL_BANDS:
        if pct <= ceiling:
            return lvl, label
    return 5, "Expert"


def _confidence_ceiling(questions_asked: int) -> float:
    return {1: 0.5, 2: 0.7, 3: 0.85}.get(questions_asked, 0.97)


def _public_payload(payload: dict | None) -> dict:
    """Strip answer-bearing fields before a question goes to the browser."""
    return {k: v for k, v in (payload or {}).items() if k not in _ANSWER_KEYS}


# ── The turn entrypoint ──────────────────────────────────────────────────────
async def run_turn(db, session: dict, state: dict, tool_result: dict | None) -> dict:
    """Return the updated `state` plus a `_emit` (the next question) or `_complete` flag.
    `state` is `session['agent_state']`; persist it back to the row after this returns."""
    if not state.get("initialized"):
        await init_session(db, session, state)
        return await pick_question(db, session, state)

    if tool_result is not None and state.get("current_question"):
        await grade(db, session, state, tool_result)
        await estimate(db, session, state)
        await check_convergence(db, session, state)

    return await pick_question(db, session, state)


async def init_session(db, session: dict, state: dict) -> None:
    """Once per session. Build the per-competency starting belief."""
    assessment_id = session.get("assessment_id")
    
    # 1. Load the assessment's competency_ids
    assess_res = await db.table("assessments").select("*").eq("id", assessment_id).maybe_single().execute()
    assessment = assess_res.data or {}
    comp_ids = assessment.get("competency_ids", [])

    # 2. Read self-ratings (1–5) from intake
    intake = session.get("intake_answers", {})
    
    state["queue"] = comp_ids
    state["active_index"] = 0
    state["initialized"] = True
    state["question_language"] = assessment.get("language", "en")
    state["question_set_id"] = assessment.get("question_set_id")
    state["per_competency"] = {}
    
    # Initialize Bayesian prior parameters per competency
    for cid in comp_ids:
        self_rating = intake.get(cid, 3)
        # 3 & 4. Mocking cv_estimate blend for now; default to self_rating[cite: 1]
        start = self_rating
        
        # Seed the Bayesian posterior peaked on `start` at low confidence
        posterior = [0.1] * 5
        posterior[start - 1] = 0.6 
        
        # 5. Populate state tracking dicts
        state["per_competency"][cid] = {
            "self_rating": self_rating,
            "initial_estimate": start,
            "level": start,
            "confidence": 0.0,
            "posterior": posterior,
            "level_history": [],
            "questions_asked": 0,
            "used_ids": [],
            "asked_types": {},
            "converged": False
        }


async def pick_question(db, session: dict, state: dict) -> dict:
    """Emit the next question, or finalize when all competencies converged."""
    queue = state.get("queue", [])
    pc_dict = state.get("per_competency", {})
    
    # 1. Advance active_index past converged competencies.
    while state["active_index"] < len(queue):
        cid = queue[state["active_index"]]
        if not pc_dict[cid].get("converged"):
            break
        state["active_index"] += 1
        
    # If none left → finalize
    if state["active_index"] >= len(queue):
        return await finalize(db, session, state)
        
    cid = queue[state["active_index"]]
    pc = pc_dict[cid]
    
    # 2. Difficulty-adaptive logic: aim at the current estimate[cite: 2]
    target_difficulty = round(pc["level"])
    
    # 3. Call selection service with difficulty and type counts
    q = await select_competency_question(
        supabase=db,
        competency=cid,
        sub_ids=pc["used_ids"],
        current_estimate=target_difficulty,
        tool_type_counts=pc.get("asked_types", {}),
        question_set_id=state.get("question_set_id")
    )
    
    # 4. Bank exhaustion handling
    if not q:
        pc["converged"] = True
        pc["converged_reason"] = "max_questions"
        state["active_index"] += 1
        return await pick_question(db, session, state)
        
    # 5. Lock in the question state for the upcoming grade cycle
    state["current_question"] = q
    q_num = state.get("question_number", 0) + 1
    state["question_number"] = q_num
    
    # 6. Emit sanitized payload to frontend
    state["_emit"] = {
        "question_number": q_num,
        "body": q.get("body"),
        "tool_type": q.get("tool_type"),
        "payload": _public_payload(q.get("payload"))
    }
    return state


async def grade(db, session: dict, state: dict, tool_result: dict) -> None:
    """Grade the answer to state['current_question'] → 0–5 + rationale; write to `answers`."""
    q = state.get("current_question", {})
    tool_type = q.get("tool_type")
    
    # Grade the answer defensively using the teammate's contract[cite: 2]
    result = await grade_answer(tool_type, q, tool_result, session["id"])
    
    # Persist the answer with the unique resumability constraint applied in DB migration[cite: 2]
    answer_row = {
        "session_id": session["id"],
        "question_number": state.get("question_number"),
        "question_id": q.get("id"),
        "question_body": q.get("body"),
        "competency_id": q.get("competency_id"),
        "tool_type": q.get("tool_type"),
        "score": result.get("score"),
        "rationale": result.get("rationale"),
        "answer_text": str(tool_result) if isinstance(tool_result, dict) else str(tool_result)
    }
    # Make grading idempotent: if a retry hits this, it safely overwrites the same score
    await db.table("answers").upsert(answer_row, on_conflict="session_id,question_number").execute()
    
    state["_grading"] = result
    
    # Update tracking for used questions and asked tool types[cite: 2]
    cid = q.get("competency_id")
    pc = state["per_competency"][cid]
    pc["used_ids"].append(str(q.get("id")))
    pc["questions_asked"] += 1
    
    t_types = pc.get("asked_types", {})
    t_types[tool_type] = t_types.get(tool_type, 0) + 1
    pc["asked_types"] = t_types


async def estimate(db, session: dict, state: dict) -> None:
    """Bayesian update of the active competency's 1–5 posterior from the latest grade."""
    grading = state.get("_grading", {})
    q = state.get("current_question", {})
    
    # Defensive programming: Do not estimate if grading failed[cite: 2]
    if grading.get("flagged", False) or grading.get("score") is None:
        return
        
    cid = q.get("competency_id")
    pc = state["per_competency"][cid]
    
    # 1. Map difficulty to the 1-5 scale[cite: 1]
    diff_raw = q.get("difficulty", "medium")
    diff_val = 3
    if isinstance(diff_raw, str):
        d = diff_raw.lower()
        if d == "easy": diff_val = 2
        elif d == "hard": diff_val = 4
    elif isinstance(diff_raw, (int, float)):
        diff_val = round(diff_raw)
        
    # 2. Update posterior deterministically without LLM calls[cite: 1]
    res = estimate_level(pc["posterior"], grading["score"], diff_val)
    
    # 3. Apply results
    pc["posterior"] = res["posterior"]
    pc["level"] = res["level"]
    
    # 4. Cap confidence ceiling to prevent one answer from triggering an early stop[cite: 1]
    raw_conf = res.get("confidence", 0.0)
    ceiling = _confidence_ceiling(pc["questions_asked"])
    pc["confidence"] = min(raw_conf, ceiling)
    
    # 5. Append history for stable-convergence check
    pc["level_history"].append(pc["level"])


async def check_convergence(db, session: dict, state: dict) -> None:
    """Mark the active competency converged when confident / stable / capped."""
    q = state.get("current_question")
    if not q:
        return
        
    cid = q.get("competency_id")
    pc = state["per_competency"][cid]
    
    reason = None
    
    # Evaluate stopping conditions[cite: 1]
    if pc["confidence"] >= CONFIDENCE_TARGET:
        reason = "confidence"
    elif pc["questions_asked"] >= MAX_QUESTIONS:
        reason = "max_questions"
    elif len(pc["level_history"]) >= STABLE_WINDOW:
        last_levels = pc["level_history"][-STABLE_WINDOW:]
        if len(set(last_levels)) == 1:
            reason = "stable"
            
    # Mark converged and persist snapshot
    if reason:
        pc["converged"] = True
        pc["converged_reason"] = reason
        
        from app.services.scoring import competency_result_from_state, session_competency_result_row
        result = competency_result_from_state(cid, pc)
        row = session_competency_result_row(session["id"], pc, result)
        await db.table("session_competency_results").upsert(row, on_conflict="session_id,competency_id").execute()
        
        # Clear question context so pick_question handles the next queue item
        state["current_question"] = None


async def finalize(db, session: dict, state: dict) -> dict:
    """Compute per-competency level → %/band, overall %, write final_reports, mark the
    session completed, set _complete.

    All scoring math (pct = level*20, band mapping, the low-confidence rule) is
    delegated to app.services.scoring — the Scoring, Reporting, Email & Observability
    lane — so this function only orchestrates reading state and writing rows. See
    app/services/scoring.py and backend/migrations/005_reports.sql for the schema and
    the tested scoring logic.

    TODO (outside the scoring lane's current scope): send report + admin emails, log
    each send. finalize() sets state['_complete']/state['_emit'] so the email step can
    be added here later without touching the scoring/persistence logic above it.
    """
    from datetime import datetime, timezone

    from app.services.scoring import (
        competency_result_from_state,
        final_report_row,
        session_competency_result_row,
    )

    per_competency: dict = state.get("per_competency", {})
    if not per_competency:
        raise ValueError("finalize() called with no per_competency results in state")

    results = []
    competency_rows = []
    for competency_id, pc in per_competency.items():
        result = competency_result_from_state(competency_id, pc)
        results.append(result)
        competency_rows.append(session_competency_result_row(session["id"], pc, result))

    # Authoritative final write per competency
    await (
        db.table("session_competency_results")
        .upsert(competency_rows, on_conflict="session_id,competency_id")
        .execute()
    )

    report_row = final_report_row(session["id"], results)
    await db.table("final_reports").upsert(report_row, on_conflict="session_id").execute()

    await (
        db.table("sessions")
        .update({"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", session["id"])
        .execute()
    )

    state["_complete"] = True
    state["_emit"] = {
        "type": "complete",
        "message": "Assessment complete — your report is ready.",
        "overall_pct": report_row["overall_pct"],
        "level_label": report_row["level_label"],
    }
    return state