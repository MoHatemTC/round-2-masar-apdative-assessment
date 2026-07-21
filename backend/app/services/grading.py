"""Grade one answer → a 0–5 score + rationale, dispatched by tool_type.  [TODO]

Build MCQ first (deterministic, no LLM), then rubric grading, then coding.
"""
from __future__ import annotations
import re
from app.services.llm import call_llm

async def grade_answer(tool_type: str, question: dict, tool_result: dict, session_id: str | None = None) -> dict:
    """Return {'score': float 0..5, 'rationale': str}. `question` has body + full payload
    (with the answer key); `tool_result` is what the candidate submitted."""
    payload = question.get("payload") or {}

    if tool_result.get("skipped"):
        return {"score": 0.0, "rationale": "Skipped by the candidate.", "flagged": False}
    
    if tool_type == "mcq":
        selected = tool_result.get("selected_id")
        correct = (payload.get("answer_key") or {}).get("correct_id")
        if correct is not None and selected == correct:
            return {"score": 5.0, "rationale": "Candidate submitted the correct answer.","flagged": False}
        else:
            return {"score": 0.0, "rationale": "Candidate submitted an incorrect answer.","flagged": False}
        

    if tool_type == "coding":

        # TODO: run tool_result['code'] against payload['test_cases'] in a SANDBOX (resource-bounded,
        #       never on the app host); tests_score = 5 * (passed / total). Then add an LLM judge on
        #       approach/quality for partial credit; blend (e.g. 0.7*tests + 0.3*judge). Log to ai_logs.

        raise NotImplementedError

    # voice / visualization / open-ended → rubric grading
    rubric = (
        payload.get("evaluation_criteria")
        or payload.get("expected_insights")
        or payload.get("rubric")
    )
    answer = tool_result.get("transcript") or tool_result.get("answer_text")

    if not rubric or not answer:
        return {
            "score": None,
            "rationale": "Missing rubric or answer — flagged for manual review.",
            "flagged": True,
        }

    rubric_text = "\n".join(f"- {criterion}" for criterion in rubric)
    prompt = (
        f"Question: {question.get('body', '')}\n\n"
        f"Candidate's answer: {answer}\n\n"
        f"Evaluate the answer against these criteria:\n{rubric_text}\n\n"
        f"Respond with a score from 0 to 5, then a one-line rationale, "
        f"in the exact format:\nSCORE: <number>\nRATIONALE: <text>"
    )

    result = await call_llm(prompt, kind="grade", session_id=session_id)

    if not result["success"]:
        return {
            "score": None,
            "rationale": "Grading failed — flagged for manual review.",
            "flagged": True,
        }

    return _parse_llm_grade(result["text"])

def _parse_llm_grade(text: str | None) -> dict:
    if not text:
        return {"score": None, "rationale": "Empty response from grader — flagged.", "flagged": True}

    score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", text)
    rationale_match = re.search(r"RATIONALE:\s*(.+)", text, re.DOTALL)

    if not score_match or not rationale_match:
        return {"score": None, "rationale": f"Could not parse grader response — flagged. Raw: {text[:200]}", "flagged": True}

    score = max(0.0, min(5.0, float(score_match.group(1))))
    rationale = rationale_match.group(1).strip()

    return {"score": score, "rationale": rationale, "flagged": False}   

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
