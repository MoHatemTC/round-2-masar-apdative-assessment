import pytest

from app.services import question_bank


@pytest.mark.asyncio
async def test_generate_fallback_question(monkeypatch):

    async def fake_call_llm(*args, **kwargs):
        return {
            "success": True,
            "text": """
{
    "id": "dummy-id",
    "body":"Explain polymorphism.",
    "tool_type":"voice",
    "difficulty":3,
    "competency_id":"java",
    "payload":{
        "evaluation_criteria":[
            "Accuracy",
            "Clarity",
            "Depth"
        ]
    }
}
"""
        }

    monkeypatch.setattr(question_bank, "call_llm", fake_call_llm)

    q = await question_bank.generate_fallback_question(
        competency_id="java",
        difficulty=3,
    )

    assert q["tool_type"] == "voice"
    assert q["difficulty"] == 3
    assert q["competency_id"] == "java"
    assert "body" in q
    assert q["payload"]["evaluation_criteria"]
    assert q["id"]


@pytest.mark.asyncio
async def test_generate_fallback_question_rejects_wrong_tool_type(monkeypatch):

    async def fake_call_llm(*args, **kwargs):
        return {
            "success": True,
            "text": '{"body": "x", "tool_type": "open_ended", "difficulty": 3, "competency_id": "java"}',
        }

    monkeypatch.setattr(question_bank, "call_llm", fake_call_llm)

    with pytest.raises(ValueError):
        await question_bank.generate_fallback_question(competency_id="java", difficulty=3)
