"""Selecting + personalizing bank questions for the adaptive loop.  [TODO]

`sub_ids`, `select_competency_question`, and `generate_fallback_question` belong to the
question-selection lane and are untouched here. `cv_estimate_levels` and `personalize_question`
are this lane's (Intake, CV & Personalization) responsibility.
"""
from __future__ import annotations

import json

from app.services.llm import call_llm

# Same answer-bearing field names the adaptive loop strips before a question reaches the browser
# (`_public_payload` in app/agent/adaptive_loop.py). Imported rather than redefined so there is
# exactly one list of "fields an LLM rewrite must never be allowed to touch" in the codebase.
from app.agent.adaptive_loop import _ANSWER_KEYS


def _clamp_level(value) -> int | None:
    """Coerce an LLM-provided value to an int 1-5, or None if it isn't usable at all."""
    try:
        level = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(5, level))


def _extract_json_from_text(text: str | None) -> dict:
    """Best-effort parser for a JSON object inside an LLM reply. `call_llm` returns raw text (it
    doesn't parse JSON itself), so every caller that expects structured JSON back does its own
    parsing here. Handles the common case of a model wrapping its reply in a ```json fence even
    when told not to. Returns {} (never None, never raises) on anything unparseable, so callers
    can always safely do `.get(...)` on the result and treat an empty dict as "no usable reply."
    """
    if not text or not text.strip():
        return {}

    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]

    try:
        parsed = json.loads(clean_text.strip())
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def sub_ids(db, track_id: str) -> list[str]:
    """A track + its sub-competency ids (questions are usually linked to subs).
    TODO: return [track_id] + [children ids]."""
    raise NotImplementedError


async def select_competency_question(db, competency_ids: list[str], exclude_ids: list[str],
                                     asked_types: list[str], target_difficulty: int | None = None,
                                     question_set_id: str | None = None) -> dict | None:
    """Pick the next bank question: not-yet-used, DIFFICULTY-adaptive, and VARIED by tool type.
    If `question_set_id` is given, restrict to that set. Return None when the bank is exhausted.
    TODO:
      1. Query question_bank where competency_id in competency_ids, is_active, id not in exclude_ids.
      2. If question_set_id: intersect with question_set_items for that set.
      3. Difficulty-adaptive: `target_difficulty` is a 1..5 level (= round(current level estimate)). Map each
         candidate row's easy/medium/hard via schemas.question_types.level_of, then prefer the pool whose
         mapped level is closest to `target_difficulty`; widen the window only if nothing is left at/near it.
      4. Among those, group by tool_type and pick from the least-asked type (per asked_types) for variety.
      5. Return one, or None when nothing remains.
    """
    raise NotImplementedError


async def personalize_question(bank_q: dict, cv_context: str, candidate_level: str = "intermediate",
                               language: str = "English", session_id: str | None = None) -> dict:
    """Rewrite the question stem AND its MCQ options to the candidate's background WITHOUT changing what's
    tested. The correct answer MUST stay invariant so the measured competency is deterministic: after the
    LLM rewrite, force the ORIGINAL answer_key / test_cases / evaluation_criteria back into the payload
    server-side (the model may relabel option text but not which option is correct). Optionally write in
    `language`. `call_llm` logs the prompt + response to ai_logs itself, keyed by `session_id`.
    """
    payload = bank_q.get("payload") or {}
    original_body = bank_q.get("body", "")

    if not (cv_context or "").strip():
        # Nothing to personalize against — return the question exactly as-is rather than spend an
        # LLM call rewriting toward no particular background.
        return bank_q

    original_options = payload.get("options") if isinstance(payload.get("options"), list) else None

    instructions = (
        "You rewrite assessment question text so it references a specific candidate's professional "
        "background, WITHOUT changing what skill is being tested and WITHOUT changing which answer "
        f"is correct. Write in {language}, at a register appropriate for a {candidate_level} candidate. "
        "If the question has multiple-choice options, you may reword each option's TEXT but you must "
        "keep exactly the same number of options, in the same order, referenced by the same ids — "
        "never add, remove, reorder, or swap which option means what. "
        'Respond with ONLY a JSON object: {"body": "...", "options": [{"id": "...", "text": "..."}]} '
        '(omit "options" entirely if the question has none).'
    )
    # Only ever put the parts that are safe to rewrite into the prompt — the stem and option TEXT.
    # Anything answer-bearing (answer_key, test_cases, evaluation_criteria, ...) never appears here,
    # so there's nothing for the model to echo back even before the re-injection step below runs.
    context_parts = [
        f"Candidate background: {cv_context}",
        f"Original question: {original_body}",
    ]
    if original_options:
        context_parts.append(
            "Original options (id/text only): "
            + str([{"id": o.get("id"), "text": o.get("text")} for o in original_options])
        )
    prompt = instructions + "\n\n" + "\n".join(context_parts)

    result = await call_llm(prompt, kind="personalize", session_id=session_id)
    parsed_data = _extract_json_from_text(result.get("text"))

    rewritten_body = parsed_data.get("body")
    new_body = rewritten_body if isinstance(rewritten_body, str) and rewritten_body.strip() else original_body

    personalized_payload = dict(payload)  # start from the ORIGINAL — every field is preserved by default

    rewritten_options = parsed_data.get("options")
    if original_options and isinstance(rewritten_options, list):
        rewritten_text_by_id = {
            o.get("id"): o.get("text") for o in rewritten_options
            if isinstance(o, dict) and isinstance(o.get("text"), str) and o.get("text").strip()
        }
        original_ids = [o.get("id") for o in original_options]
        # Only accept the rewrite if it named every original id, exactly, with nothing extra —
        # otherwise a malformed rewrite could scramble which id maps to which correct answer.
        # A partial/mismatched rewrite is discarded wholesale; original option text wins instead.
        if set(rewritten_text_by_id) == set(original_ids):
            personalized_payload["options"] = [
                {**o, "text": rewritten_text_by_id[o.get("id")]} for o in original_options
            ]
        # else: fall through — personalized_payload["options"] stays the original, untouched list.

    # Hard rule, enforced unconditionally regardless of anything above: the fields that determine
    # correctness are re-copied from the ORIGINAL payload, verbatim. Even if a future change to this
    # function started passing more of the model's reply through, this line is what guarantees the
    # answer can never drift from what was actually authored in the question bank.
    for key in _ANSWER_KEYS:
        if key in payload:
            personalized_payload[key] = payload[key]

    personalized = dict(bank_q)
    personalized["body"] = new_body
    personalized["payload"] = personalized_payload
    return personalized


async def generate_fallback_question(competency_name: str, rubric: str, cv_context: str,
                                     language: str = "English", exclude_ids: list[str] | None = None) -> dict:
    """An AI-generated OPEN-ENDED question used when a competency's bank is exhausted before it converges
    (never an MCQ — an invented answer key can't be trusted). The loop keeps calling this to KEEP PROBING
    until the competency converges or hits MAX_QUESTIONS, so avoid repeating earlier prompts (use
    exclude_ids / vary the angle). Return the same shape as a personalized question with tool_type='voice'."""
    raise NotImplementedError


async def cv_estimate_levels(cv_json: dict | None, queue: list[dict], session_id: str | None = None) -> dict[str, int]:
    """One LLM pass: read the CV and estimate a 1-5 level per competency in `queue`.
    Return {competency_id: 1..5}. Empty dict when there's no CV. `call_llm` logs to ai_logs itself.
    This feeds ONLY the starting prior (blended 50/50 with the self-rating), not the per-answer update.

    `queue` items are expected to have at least an "id"; "name" (or "code") is used as the
    human-readable label shown to the model, falling back to the id if neither is present.
    """
    if not cv_json:
        return {}

    cv_text = (cv_json.get("raw_text") or cv_json.get("summary") or "").strip() if isinstance(cv_json, dict) else ""
    if not cv_text:
        return {}  # a cv_json blob with no extractable text carries no signal — don't spend a call on it

    competencies = [
        {"id": c["id"], "name": c.get("name") or c.get("code") or c["id"]}
        for c in queue if isinstance(c, dict) and c.get("id")
    ]
    if not competencies:
        return {}

    instructions = (
        "You estimate a candidate's skill level (1-5, where 1 = novice and 5 = expert) for each named "
        "competency, based ONLY on evidence in their CV/resume text below. If the CV gives no real signal "
        "for a competency, omit that competency from your answer entirely rather than guessing. "
        'Respond with ONLY a JSON object mapping competency id -> integer 1-5, e.g. {"<competency_id>": 4}.'
    )
    prompt = instructions + f"\n\nCompetencies:\n{competencies}\n\nCV text:\n{cv_text}"

    result = await call_llm(prompt, kind="cv_estimate", session_id=session_id)
    parsed_data = _extract_json_from_text(result.get("text"))

    valid_ids = {c["id"] for c in competencies}
    estimates: dict[str, int] = {}
    for competency_id, raw_level in parsed_data.items():
        if competency_id not in valid_ids:
            continue  # the model must not invent an estimate for a competency we didn't ask about
        level = _clamp_level(raw_level)
        if level is not None:
            estimates[competency_id] = level
    return estimates