"""Selecting + personalizing bank questions for the adaptive loop.  [TODO]"""
from __future__ import annotations

# from app.db import get_db
# from app.services.llm import chat_json   # a thin wrapper around your OpenAI-compatible client


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
                               language: str = "English") -> dict:
    """Rewrite the question stem AND its MCQ options to the candidate's background WITHOUT changing what's
    tested. The correct answer MUST stay invariant so the measured competency is deterministic: after the
    LLM rewrite, force the ORIGINAL answer_key / test_cases / evaluation_criteria back into the payload
    server-side (the model may relabel option text but not which option is correct). Optionally write in
    `language`. Log the prompt + response to ai_logs."""
    raise NotImplementedError


async def generate_fallback_question(competency_name: str, rubric: str, cv_context: str,
                                     language: str = "English", exclude_ids: list[str] | None = None) -> dict:
    """An AI-generated OPEN-ENDED question used when a competency's bank is exhausted before it converges
    (never an MCQ — an invented answer key can't be trusted). The loop keeps calling this to KEEP PROBING
    until the competency converges or hits MAX_QUESTIONS, so avoid repeating earlier prompts (use
    exclude_ids / vary the angle). Return the same shape as a personalized question with tool_type='voice'."""
    raise NotImplementedError


async def cv_estimate_levels(cv_json: dict | None, queue: list[dict]) -> dict[str, int]:
    """One LLM pass: read the CV and estimate a 1–5 level per competency in `queue`.
    Return {competency_id: 1..5}. Empty dict when there's no CV. Log to ai_logs.
    This feeds ONLY the starting prior (blended 50/50 with the self-rating), not the per-answer update."""
    raise NotImplementedError
