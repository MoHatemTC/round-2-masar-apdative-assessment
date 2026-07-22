"""
Confirms the frozen {score, rationale, flagged} contract holds on every
grade_answer return path -- not just the ones that were already flagged.

Run with:
    cd backend
    python -m pytest tests/test_grading_contract.py -v
"""
import pytest
from app.services.grading import grade_answer


@pytest.fixture
def mcq_question():
    return {
        "id": "q-1",
        "tool_type": "mcq",
        "payload": {"answer_key": {"correct_id": "b"}},
    }


@pytest.mark.asyncio
async def test_skip_includes_flagged_key(mcq_question):
    result = await grade_answer("mcq", mcq_question, {"skipped": True})
    assert "flagged" in result
    assert result["flagged"] is False


@pytest.mark.asyncio
async def test_mcq_correct_includes_flagged_key(mcq_question):
    result = await grade_answer("mcq", mcq_question, {"selected_id": "b"})
    assert "flagged" in result
    assert result["flagged"] is False


@pytest.mark.asyncio
async def test_mcq_incorrect_includes_flagged_key(mcq_question):
    result = await grade_answer("mcq", mcq_question, {"selected_id": "a"})
    assert "flagged" in result
    assert result["flagged"] is False


@pytest.mark.asyncio
async def test_missing_rubric_still_includes_flagged_key():
    """Sanity check the already-flagged paths still say True (not broken by this fix)."""
    voice_question = {"id": "q-2", "tool_type": "voice", "payload": {}}  # no evaluation_criteria
    result = await grade_answer("voice", voice_question, {"answer_text": "some answer"})
    assert "flagged" in result
    assert result["flagged"] is True