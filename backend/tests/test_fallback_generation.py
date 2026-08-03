import pytest

from app.services import question_bank

@pytest.mark.asyncio
async def test_generate_fallback_question(monkeypatch):

    async def fake_call_llm(*args, **kwargs):
        return {
            "success": True,
            "text": """
{
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