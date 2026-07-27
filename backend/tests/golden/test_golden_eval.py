import json
from pathlib import Path

import pytest

from app.services.grading import grade_answer


GOLDEN = (
    Path(__file__)
    .parent
    / "graded_answers.json"
)

with open(GOLDEN, encoding="utf8") as f:
    CASES = json.load(f)["cases"]


@pytest.mark.eval
@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda c: c["case_id"],
)
@pytest.mark.asyncio
async def test_golden_answers(case):

    if case["kind"] == "coding":

        question = {
            "body": "",
            "payload": {
                "language": "python",
                "expected_approach": "",
                "starter_code": "",
                "test_cases": [],
            },
        }

        tool_result = {
            "code": case["answer"],
        }

    else:

        question = {
            "body": "",
            "payload": {
                "rubric": [],
            },
        }

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