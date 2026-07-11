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

# ── Tunable convergence knobs (start here; see ARCHITECTURE.md) ──────────────
CONFIDENCE_TARGET = 0.90
MAX_QUESTIONS = 10          # per competency
STABLE_WINDOW = 3           # same level N times in a row → converged
# Every answer-bearing field, stripped before a question reaches the browser. Covers all tool_types:
# MCQ key + explanation, coding tests, and the rubric keys the open-ended/voice/data-analysis graders read.
_ANSWER_KEYS = {"answer_key", "correct_id", "explanation", "test_cases", "expected_output",
                "evaluation_criteria", "expected_insights", "rubric"}

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
    """Once per session. Build the per-competency starting belief.
    TODO:
      1. Load the assessment's competency_ids → the competency queue.
      2. Read self-ratings (1–5) from session['intake_answers'].
      3. cv_estimate = await cv_estimate_levels(session.get('cv_json'), queue)  # one LLM call
      4. start = round(0.5*cv_estimate + 0.5*self_rating) per competency; self_rating alone with no CV;
         fallback 3. Seed the Bayesian posterior peaked on `start` at low confidence (a belief, not a measurement).
      5. state['per_competency'][cid] = {self_rating, initial_estimate: start, level: start, confidence,
             posterior: prior_distribution(start),   # [p1..p5] over levels 1..5, peaked on `start`
             level_history: [], questions_asked: 0, used_ids: [], asked_types: [], converged: False}
      6. state['queue'], state['active_index'] = 0, state['initialized'] = True,
         state['question_language'], state['question_set_id'] (from the assessment).
    """
    raise NotImplementedError


async def pick_question(db, session: dict, state: dict) -> dict:
    """Emit the next question, or finalize when all competencies converged.
    TODO:
      1. Advance active_index past converged competencies. If none left → return await finalize(...).
      2. target_difficulty = round(pc['level'])  # difficulty-adaptive: aim at the current estimate.
      3. comp = queue[active_index]; q = await make_question(db, comp, pc, cv_context,
             target_difficulty=target_difficulty,          # select a bank question near this difficulty
             language=state['question_language'], question_set_id=state['question_set_id'])
      4. If the bank is dry, make_question falls back to a GENERATED open-ended question and keeps
         probing — it only returns None once questions_asked >= MAX_QUESTIONS. On None → mark converged
         (reason 'max_questions', flag low-confidence if pc['confidence'] < CONFIDENCE_TARGET), continue.
      5. state['current_question'] = q (FULL payload, kept server-side for grading).
      6. state['_emit'] = {question_number, body, tool_type, payload: _public_payload(q['payload'])}
      7. return state
    """
    raise NotImplementedError


async def grade(db, session: dict, state: dict, tool_result: dict) -> None:
    """Grade the answer to state['current_question'] → 0–5 + rationale; write to `answers`.
    TODO: dispatch by tool_type to services.grading; store with a unique (session, question_number)
    guard so a reload can't double-count. Set state['_grading'] and clear current_question."""
    raise NotImplementedError


async def estimate(db, session: dict, state: dict) -> None:
    """Bayesian update of the active competency's 1–5 posterior from the latest grade.
    TODO:
      1. difficulty = level_of(current_question['difficulty'])  # map easy/medium/hard → 1..5 (see
         schemas.question_types.DIFFICULTY_TO_LEVEL); a high score on a HARD question shifts mass up.
      2. res = estimate_level(pc['posterior'], score, difficulty)  # deterministic, no LLM.
         estimate_level returns {'posterior': [p1..p5], 'level': argmax, 'confidence': 1 - spread}.
      3. pc['posterior'] = res['posterior']; pc['level'] = res['level'].
      4. pc['confidence'] = min(res['confidence'], _confidence_ceiling(questions_asked)).
      5. pc['level_history'].append(pc['level']).
    The self-rating/CV live in the INITIAL posterior (the prior) — they aren't re-fed each turn."""
    raise NotImplementedError


async def check_convergence(db, session: dict, state: dict) -> None:
    """Mark the active competency converged when confident / stable / capped.
    TODO:
      reason = 'confidence' if confidence >= CONFIDENCE_TARGET
               else 'stable'  if last STABLE_WINDOW levels are identical
               else 'max_questions' if questions_asked >= MAX_QUESTIONS
      if reason: pc['converged']=True; persist session_competency_results.
    """
    raise NotImplementedError


async def finalize(db, session: dict, state: dict) -> dict:
    """Compute per-competency level → %/band, overall %, write final_reports, (email), set _complete.
    TODO:
      per competency: pct=_pct(level); low_confidence = pc['confidence'] < CONFIDENCE_TARGET;
      overall_pct = avg(level)*20; (level, label)=_band(overall_pct)
      insert final_reports {overall_pct, overall_level, level_label, skill_scores (incl. low_confidence flag)};
      mark session completed; send report + admin emails (log each send); state['_complete'] = True;
      state['_emit'] = a closing message. return state.
    """
    raise NotImplementedError
