"""
Tests for coding question grading.

Covers:

- correct solution
- partial solution
- syntax error
- empty submission
- unchanged starter code
- provider unavailable
- LLM failure fallback
"""

import pytest

from app.services.grading import grade_answer


# -------------------------------------------------------
# Common coding question
# -------------------------------------------------------

QUESTION = {
    "body": "Write add(a,b).",
    "payload": {
        "language": "python",
        "starter_code": "def add(a,b):\n    pass",
        "expected_approach": "Return a+b.",
        "test_cases": [
            {
                "input": [1, 2],
                "expected": 3,
            },
            {
                "input": [5, 8],
                "expected": 13,
            },
        ],
    },
}


# -------------------------------------------------------
# Empty submission
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_submission():

    result = await grade_answer(
        "coding",
        QUESTION,
        {"code": ""},
    )

    assert result["score"] == 0
    assert result["flagged"] is False
    assert "No code" in result["rationale"]


# -------------------------------------------------------
# Starter code unchanged
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_starter_code():

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": QUESTION["payload"]["starter_code"],
        },
    )

    assert result["score"] <= 1
    assert result["flagged"] is False


# -------------------------------------------------------
# Perfect solution
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_solution(monkeypatch):

    async def fake_run_code(**kwargs):
        return {
            "provider_failed": False,
            "timed_out": False,
            "pass_rate": 1.0,
            "stderr": "",
            "results": [
                {"passed": True},
                {"passed": True},
            ],
        }

    async def fake_llm(*args, **kwargs):
        return {
            "success": True,
            "text": "SCORE: 5\nRATIONALE: Excellent solution.",
        }

    monkeypatch.setattr(
        "app.services.grading.run_code",
        fake_run_code,
    )

    monkeypatch.setattr(
        "app.services.grading.call_llm",
        fake_llm,
    )

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": "def add(a,b): return a+b",
        },
    )

    assert result["score"] >= 4.9
    assert result["flagged"] is False


# -------------------------------------------------------
# Partial solution
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_partial_solution(monkeypatch):

    async def fake_run_code(**kwargs):
        return {
            "provider_failed": False,
            "timed_out": False,
            "pass_rate": 0.5,
            "stderr": "",
            "results": [
                {"passed": True},
                {"passed": False},
            ],
        }

    async def fake_llm(*args, **kwargs):
        return {
            "success": True,
            "text": "SCORE: 3\nRATIONALE: Mostly correct.",
        }

    monkeypatch.setattr(
        "app.services.grading.run_code",
        fake_run_code,
    )

    monkeypatch.setattr(
        "app.services.grading.call_llm",
        fake_llm,
    )

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": "partial",
        },
    )

    assert 2 <= result["score"] <= 4
    assert "Failed test cases" in result["rationale"]


# -------------------------------------------------------
# Syntax error
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_syntax_error(monkeypatch):

    async def fake_run_code(**kwargs):
        return {
            "provider_failed": False,
            "timed_out": False,
            "pass_rate": 0.0,
            "stderr": "SyntaxError",
            "results": [
                {"passed": False},
                {"passed": False},
            ],
        }

    async def fake_llm(*args, **kwargs):
        return {
            "success": True,
            "text": "SCORE: 1\nRATIONALE: Syntax error.",
        }

    monkeypatch.setattr(
        "app.services.grading.run_code",
        fake_run_code,
    )

    monkeypatch.setattr(
        "app.services.grading.call_llm",
        fake_llm,
    )

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": "def add(",
        },
    )

    assert result["score"] <= 1
    assert "SyntaxError" in result["rationale"]


# -------------------------------------------------------
# Provider unavailable
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_down(monkeypatch):

    async def fake_run_code(**kwargs):
        return {
            "provider_failed": True,
        }

    monkeypatch.setattr(
        "app.services.grading.run_code",
        fake_run_code,
    )

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": "anything",
        },
    )

    assert result["flagged"] is True
    assert result["score"] is None


# -------------------------------------------------------
# LLM unavailable
# -------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_failure(monkeypatch):

    async def fake_run_code(**kwargs):
        return {
            "provider_failed": False,
            "timed_out": False,
            "pass_rate": 0.8,
            "stderr": "",
            "results": [
                {"passed": True},
                {"passed": True},
            ],
        }

    async def fake_llm(*args, **kwargs):
        return {
            "success": False,
            "text": None,
        }

    monkeypatch.setattr(
        "app.services.grading.run_code",
        fake_run_code,
    )

    monkeypatch.setattr(
        "app.services.grading.call_llm",
        fake_llm,
    )

    result = await grade_answer(
        "coding",
        QUESTION,
        {
            "code": "good solution",
        },
    )

    assert result["flagged"] is True

    # pass_rate = 0.8
    # tests_score = 4
    # judge fallback = 4
    # final = 4

    assert result["score"] == 4