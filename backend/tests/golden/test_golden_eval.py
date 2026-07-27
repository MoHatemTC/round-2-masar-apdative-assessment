import json
from pathlib import Path

import pytest

from app.services.grading import grade_answer


# ---------------------------------------------------
# Golden answers
# ---------------------------------------------------

GOLDEN = (
    Path(__file__).parent
    / "graded_answers.json"
)

with open(GOLDEN, encoding="utf8") as f:
    CASES = json.load(f)["cases"]


# ---------------------------------------------------
# Question bank
# ---------------------------------------------------

QUESTION_BANK = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "sample_question_bank.json"
)

with open(QUESTION_BANK, encoding="utf8") as f:
    QUESTION_BANK_DATA = json.load(f)


QUESTION_MAP = {
    q["source_ref"]: q
    for q in QUESTION_BANK_DATA
}


# ---------------------------------------------------
# Tests
# ---------------------------------------------------

@pytest.mark.eval
@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda c: c["case_id"],
)
@pytest.mark.asyncio
async def test_golden_answers(case):

    question = QUESTION_MAP[case["question_source_ref"]]

    if case["kind"] == "coding":

        tool_result = {
            "code": case["answer"],
        }

    else:

        tool_result = {
            "answer_text": case["answer"],
        }

    result = await grade_answer(
        case["kind"],
        question,
        tool_result,
    )

    score = result["score"]

    assert score >= case["expected_min"]
    assert score <= case["expected_max"]

    if "expected_flagged" in case:
        assert (
            result["flagged"]
            == case["expected_flagged"]
        )