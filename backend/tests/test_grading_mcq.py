"""
test_grading_mcq.py

Run with:
    cd backend
    pytest tests/test_grading_mcq.py -v
"""

import pytest
from app.services.grading import grade_answer


@pytest.fixture
def mcq_question():
    return {
        "id": "q-1",
        "tool_type": "mcq",
        "body": "You need an LLM to return data your code can parse every time. Which approach is the most reliable?",
        "payload": {
            "options": [
                {"id": "a", "text": "Ask nicely in the prompt to 'return JSON' and hope for the best"},
                {"id": "b", "text": "Use function-calling / a structured-output schema and validate the result against it"},
                {"id": "c", "text": "Raise the temperature so the model is more creative with formatting"},
                {"id": "d", "text": "Parse the response with a regular expression after the fact"},
            ],
            "answer_key": {"correct_id": "b"},
        },
    }

@pytest.mark.asyncio
async def test_mcq_skipped_answer_scores_zero(mcq_question):
    #  tool_result represents "skipped" 
    # grade_answer actually detects a skip (what key does it check?) — assert score is 0.0
    tool_result = {"skipped": True}  # question was skipped by the candidate
    result = await grade_answer("mcq", mcq_question, tool_result)
    assert result["score"] == 0.0


@pytest.mark.asyncio
async def test_mcq_correct_answer_scores_five(mcq_question):
    # tool_result dict with the correct selected_id ("b"), assert score is 5.0
    tool_result = {"selected_id": "b"}  # "b" is the correct one, per the fixture's answer_key
    result = await grade_answer("mcq", mcq_question, tool_result)
    assert result["score"] == 5.0


@pytest.mark.asyncio
async def test_mcq_incorrect_answer_scores_zero(mcq_question):
    # same, but selected_id is wrong  — assert score is 0.0
    tool_result = {"selected_id": "a"}  # "a" is the incorrect one, per the fixture's answer_key
    result = await grade_answer("mcq", mcq_question, tool_result)
    assert result["score"] == 0.0


