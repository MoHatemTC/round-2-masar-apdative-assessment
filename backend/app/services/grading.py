"""Grade one answer → a 0–5 score + rationale, dispatched by tool_type.  [TODO]

Build MCQ first (deterministic, no LLM), then rubric grading, then coding.
"""
from __future__ import annotations


async def grade_answer(tool_type: str, question: dict, tool_result: dict) -> dict:
    """Return {'score': float 0..5, 'rationale': str}. `question` has body + full payload
    (with the answer key); `tool_result` is what the candidate submitted."""
    payload = question.get("payload") or {}

    if tool_result.get("skipped"):
        return {"score": 0.0, "rationale": "Skipped by the candidate."}

    if tool_type == "mcq":
        # TODO: correct = payload['answer_key']['correct_id']; score 5.0 if selected == correct else 0.0
        selected = tool_result.get("selected_id")
        correct = payload['answer_key']['correct_id']
        if selected == correct:
            return {"score": 5.0, "rationale": "Candidate submitted the correct answer."}
        else:
            return {"score": 0.0, "rationale": "Candidate submitted an incorrect answer."}
        

    if tool_type == "coding":
        # TODO: run tool_result['code'] against payload['test_cases'] in a SANDBOX (resource-bounded,
        #       never on the app host); tests_score = 5 * (passed / total). Then add an LLM judge on
        #       approach/quality for partial credit; blend (e.g. 0.7*tests + 0.3*judge). Log to ai_logs.

        raise NotImplementedError

    # voice / visualization / open-ended → rubric grading
    # TODO: for 'voice', the candidate submits AUDIO → transcribe (STT) into tool_result['transcript'].
    #       rubric = payload.get('evaluation_criteria') or payload.get('expected_insights') or payload.get('rubric')
    #              (all three are accepted signals — see schemas.question_types._RUBRIC_KEYS)
    #       answer = tool_result.get('transcript') or tool_result.get('answer_text')
    #       LLM judge: score 0..5 against the rubric + a one-line rationale. Log to ai_logs.
    raise NotImplementedError


def estimate_level(posterior: list[float], score: float, difficulty: int) -> dict:
    """DETERMINISTIC Bayesian update — NO LLM call. Given the running `posterior` over levels {1..5},
    the latest answer `score` (0–5) and the question `difficulty` (a 1..5 level — map easy/medium/hard
    through schemas.question_types.level_of before calling), return the new belief:
        {'posterior': [p1..p5], 'level': argmax, 'confidence': 1 - normalized_spread}
    TODO:
      1. likelihood[L] = P(observing this score | true level == L, difficulty) — a high score on a HARD
         question makes high L likely; a low score on an EASY question makes low L likely.
      2. posterior'[L] = posterior[L] * likelihood[L]; renormalize so it sums to 1.
      3. level = argmax(posterior')  (1..5);  confidence = 1 - normalized_spread(posterior').
    The self-rating/CV enter only through the INITIAL posterior (the prior), not here.
    The caller (adaptive_loop.estimate) clamps confidence to the per-question ceiling."""
    raise NotImplementedError
