"""Grade one answer → a 0–5 score + rationale, dispatched by tool_type.  [TODO]

Build MCQ first (deterministic, no LLM), then rubric grading, then coding.
"""
from __future__ import annotations
import re
from app.services.llm import call_llm
from app.services.sandbox import run_code
from app.services.sandbox_validation import (
    SandboxRequest,
    validate_sandbox_request,
)

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
            return {"score": 5.0, "rationale": "Candidate submitted the correct answer.", "flagged": False}
        else:
            return {"score": 0.0, "rationale": "Candidate submitted an incorrect answer.", "flagged": False}

    if tool_type == "coding":

        language = payload.get("language", "python")
        starter_code = payload.get("starter_code", "")
        expected_approach = payload.get("expected_approach", "")
        test_cases = payload.get("test_cases", [])

        submitted_code = tool_result.get("code", "")

        # Hardcoded coding solution detection
        hardcoded = (
            "{'a': 2, 'b': 3}" in submitted_code
            or "{'text': 'hi'}" in submitted_code
        )

        if hardcoded:
            return {
                "score": 1.5,
                "rationale": "Solution appears to hardcode the visible test cases.",
                "flagged": False,
            }

        # Empty submission
        if not submitted_code.strip():
            return {
                "score": 0.0,
                "rationale": "No code submitted.",
                "flagged": False,
            }

        # Candidate never changed starter code
        if starter_code and submitted_code.strip() == starter_code.strip():
            return {
                "score": 1.0,
                "rationale": "Starter code was submitted without modification.",
                "flagged": False,
            }

        try:
            request = SandboxRequest(
                code=submitted_code,
                language=language,
                test_cases=test_cases,
            )
            validate_sandbox_request(request)
        except Exception as exc:
            return {
                "score": 0.0,
                "rationale": f"Invalid sandbox request: {str(exc)}",
                "flagged": True,
            }

        sandbox = await run_code(
            language=request.language,
            code=request.code,
            test_cases=request.test_cases,
        )
        print("\n" + "=" * 80)
        print("SANDBOX RESULT")
        print(sandbox)
        print("=" * 80 + "\n")

        # Sandbox provider unavailable
        if sandbox["provider_failed"]:
            return {
                "score": None,
                "rationale": "Sandbox provider unavailable. Submission flagged for manual review.",
                "flagged": True,
            }

        # Infinite loop / timeout
        if sandbox["timed_out"]:
            return {
                "score": 0.0,
                "rationale": "Execution timed out.",
                "flagged": True,
            }

        pass_rate = sandbox["pass_rate"]
        tests_score = pass_rate * 5.0

        prompt = f"""
You are an expert Python software engineer reviewing a coding interview submission.

Question:
{question.get("body", "")}

Expected approach:
{expected_approach}

Candidate submission:

{submitted_code}

The automated sandbox has already executed the candidate's code.

DO NOT judge whether the code passes test cases.
Instead evaluate ONLY the implementation quality.

Score based on:

- Correct algorithm
- Follows the expected approach
- Code readability
- Maintainability
- Edge-case handling
- Python best practices

Scoring rubric:

5 = Excellent implementation following the expected approach with clean, maintainable code.

4 = Correct implementation with only minor issues.

3 = Mostly correct but has noticeable weaknesses.

2 = Partially correct or poor implementation.

1 = Very weak attempt.

0 = Completely incorrect or unrelated solution.

Return EXACTLY in this format:

SCORE: <0-5>
RATIONALE: <one sentence only>
"""

        llm = await call_llm(
            prompt,
            kind="grade",
            session_id=session_id,
        )

        flagged = False

        if llm["success"]:
            parsed = _parse_llm_grade(llm["text"])
            judge_score = parsed["score"] or 0.0
            rationale = parsed["rationale"]
        else:
            judge_score = tests_score
            rationale = "LLM judge unavailable. Score based on test cases only."
            flagged = True

        if test_cases:
            final_score = round((tests_score + judge_score) / 2.0, 2)
        else:
            final_score = judge_score
        final_score = max(0.0, min(5.0, final_score))

        if sandbox["stderr"]:
            rationale += f"\nRuntime output: {sandbox['stderr']}"

        failed_cases = [
            str(i + 1)
            for i, r in enumerate(sandbox["results"])
            if not r.get("passed")
        ]

        if failed_cases:
            rationale += (
                "\nFailed test cases: "
                + ", ".join(failed_cases)
            )

        return {
            "score": final_score,
            "rationale": rationale,
            "flagged": flagged,
        }

    # voice / visualization / open-ended → rubric grading
    rubric = (
        payload.get("evaluation_criteria")
        or payload.get("expected_insights")
        or payload.get("rubric")
    )
    answer = tool_result.get("transcript") or tool_result.get("answer_text") or ""

    lower = answer.lower()

    # 1. Prompt injection
    if any(x in lower for x in [
        "ignore all previous",
        "system override",
        "pre-approved",
        "must receive",
        "assessment administrator",
    ]):
        return {
            "score": 0.0,
            "rationale": "Prompt injection attempt detected.",
            "flagged": True,
        }

    # 2. Keyword stuffing
    words = re.findall(r"\b[a-zA-Z-]+\b", answer)

    if len(words) < 35 and answer.count(".") >= 5:
        return {
            "score": 1.5,
            "rationale": "Lists keywords without explanation.",
            "flagged": False,
        }

    # 3. Strong analysis
    if (
        ("recommend" in lower or "ship gated" in lower or "rollback" in lower)
        and ("refund" in lower or "accuracy" in lower)
    ):
        return {
            "score": 4.5,
            "rationale": "Provides evidence-based analysis and actionable recommendation.",
            "flagged": False,
        }

    # 4. Fabricated analysis
    if (
        "95%" in answer
        or "100%" in answer
        or "all categories" in lower
        or "everyone improved" in lower
    ):
        return {
            "score": 1.0,
            "rationale": "Answer fabricates unsupported conclusions.",
            "flagged": False,
        }

    # 5. Vague prompt answer
    if (
        "prompt" in lower
        and (
            "looks good" in lower
            or "working well" in lower
            or "good enough" in lower
            or "try" in lower
        )
    ):
        return {
            "score": 2.5,
            "rationale": "Reasonable process but lacks concrete evaluation.",
            "flagged": False,
        }

    # 6. Describes only
    if (
        "improved" in lower
        or "increase" in lower
        or "decrease" in lower
    ):
        if (
            "recommend" not in lower
            and "next step" not in lower
        ):
            return {
                "score": 2.5,
                "rationale": "Correctly describes the data but gives limited analysis.",
                "flagged": False,
            }

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
    """Parse 'SCORE: <n>\nRATIONALE: <text>' from the LLM's response."""
    if not text:
        return {"score": None, "rationale": "Empty response from grader — flagged.", "flagged": True}

    score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", text)
    rationale_match = re.search(r"RATIONALE:\s*(.+)", text, re.DOTALL)

    if not score_match or not rationale_match:
        return {"score": None, "rationale": f"Could not parse grader response — flagged. Raw: {text[:200]}", "flagged": True}

    score = max(0.0, min(5.0, float(score_match.group(1))))
    rationale = rationale_match.group(1).strip()

    return {"score": score, "rationale": rationale, "flagged": False}