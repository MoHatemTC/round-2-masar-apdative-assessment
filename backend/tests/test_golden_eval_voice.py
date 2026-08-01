"""Golden-answer eval suite — runs grade_answer against the LIVE model, not mocked.
Run with: pytest -m eval tests/test_golden_eval.py -v
Excluded from normal runs via: pytest -m "not eval"
"""
import json
import os
import pytest
from app.services.grading import grade_answer

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden", "graded_answers.json")
QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "golden", "questions.json")

with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
    CASES = json.load(f)["cases"]

with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)  # {"AIE-1-Q02": {"body": ..., "payload": {...}}, ...}

RUBRIC_CASES = [c for c in CASES if c["kind"] == "rubric"]
CODING_CASES = [c for c in CASES if c["kind"] == "coding"]


def _question_and_result(case: dict):
    q = QUESTIONS[case["question_source_ref"]]
    question = {"body": q["body"], "payload": q["payload"]}
    tool_result = {"answer_text": case["answer"]}
    return question, tool_result


@pytest.mark.eval
@pytest.mark.asyncio
@pytest.mark.parametrize("case", RUBRIC_CASES, ids=[c["case_id"] for c in RUBRIC_CASES])
async def test_golden_rubric_case(case):
    question, tool_result = _question_and_result(case)
    result = await grade_answer(tool_type="voice", question=question, tool_result=tool_result)

    assert result["score"] is not None, f"{case['case_id']}: got None — {result['rationale']}"
    assert case["expected_min"] <= result["score"] <= case["expected_max"], (
        f"{case['case_id']}: score {result['score']} not in "
        f"[{case['expected_min']}, {case['expected_max']}]. Rationale: {result['rationale']}"
    )
    if "expected_flagged" in case:
        assert result["flagged"] == case["expected_flagged"], (
            f"{case['case_id']}: flagged={result['flagged']}, expected={case['expected_flagged']}"
        )

    # Rationale must be substantive, not a generic one-liner disconnected from the rubric
    assert result["rationale"], f"{case['case_id']}: rationale is empty"
    assert len(result["rationale"].strip()) >= 15, (
        f"{case['case_id']}: rationale too short to plausibly reference rubric criteria: "
        f"{result['rationale']!r}"
    )


@pytest.mark.skip(reason="coding grading not implemented yet (grade_answer raises NotImplementedError)")
@pytest.mark.parametrize("case", CODING_CASES, ids=[c["case_id"] for c in CODING_CASES])
def test_golden_coding_case(case):
    pass


@pytest.mark.eval
@pytest.mark.asyncio
async def test_repeat_grading_stability():
    """Same input graded twice — scores must land within ±1."""
    case = RUBRIC_CASES[0]
    question, tool_result = _question_and_result(case)

    result_a = await grade_answer(tool_type="voice", question=question, tool_result=tool_result)
    result_b = await grade_answer(tool_type="voice", question=question, tool_result=tool_result)

    assert result_a["score"] is not None and result_b["score"] is not None
    diff = abs(result_a["score"] - result_b["score"])
    assert diff <= 1.0, f"Stability failed: {result_a['score']} vs {result_b['score']} (diff {diff})"