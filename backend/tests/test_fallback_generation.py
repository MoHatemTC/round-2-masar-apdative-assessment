import pytest

from app.services import llm


@pytest.mark.asyncio
async def test_generate_fallback_question(monkeypatch):

    async def fake_call_llm(*args, **kwargs):
        return {
            "success": True,
            "text": """
{
    "body":"Explain polymorphism.",
    "tool_type":"open_ended",
    "difficulty":3,
    "competency_id":"java"
}
"""
        }

    monkeypatch.setattr(llm, "call_llm", fake_call_llm)

    q = await llm.generate_fallback_question(
        competency_id="java",
        difficulty=3,
    )

    assert q["tool_type"] == "open_ended"
    assert q["difficulty"] == 3
    assert q["competency_id"] == "java"
    assert "body" in q