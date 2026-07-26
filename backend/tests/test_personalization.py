"""Tests for question_bank.cv_estimate_levels and question_bank.personalize_question.

call_llm is mocked throughout — these tests are about OUR handling of whatever the model
returns: does a good reply get used, does a malicious or malformed reply get safely discarded,
does the answer key ever leak.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agent.adaptive_loop import _ANSWER_KEYS, _public_payload
from app.services.question_bank import cv_estimate_levels, personalize_question

COMPETENCY_A = "11111111-1111-1111-1111-111111111111"
COMPETENCY_B = "22222222-2222-2222-2222-222222222222"


def _mock_call_llm(monkeypatch, module, text: str, success: bool = True):
    """Patch call_llm as imported into `module`, returning the same
    {"success", "text", "error"} shape the real function returns."""
    mock = AsyncMock(return_value={"success": success, "text": text, "error": None if success else "boom"})
    monkeypatch.setattr(module, "call_llm", mock)
    return mock


MCQ_QUESTION = {
    "id": "q-1",
    "competency_id": COMPETENCY_A,
    "tool_type": "mcq",
    "body": "Which HTTP status code means a resource was created?",
    "payload": {
        "options": [
            {"id": "a", "text": "200 OK"},
            {"id": "b", "text": "201 Created"},
            {"id": "c", "text": "404 Not Found"},
        ],
        "answer_key": {"correct_id": "b"},
        "explanation": "201 Created is returned when a request creates a new resource.",
    },
}


# ── personalize_question: happy paths ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_personalize_returns_unchanged_when_no_cv_context(monkeypatch):
    import app.services.question_bank as qb
    mock = AsyncMock()
    monkeypatch.setattr(qb, "call_llm", mock)

    result = await personalize_question(MCQ_QUESTION, cv_context="")

    assert result == MCQ_QUESTION
    mock.assert_not_called()  # must not spend an LLM call with nothing to personalize against


@pytest.mark.asyncio
async def test_personalize_rewrites_body_and_option_text(monkeypatch):
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({
        "body": "As a backend engineer working with REST APIs, which status code means a resource was created?",
        "options": [
            {"id": "a", "text": "200 OK"},
            {"id": "b", "text": "201 Created — the one you'd expect from a successful POST"},
            {"id": "c", "text": "404 Not Found"},
        ],
    }))

    result = await personalize_question(MCQ_QUESTION, cv_context="5 years as a backend engineer")

    assert "backend engineer" in result["body"]
    assert result["payload"]["options"][1]["text"] == "201 Created — the one you'd expect from a successful POST"
    assert [o["id"] for o in result["payload"]["options"]] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_personalize_strips_markdown_fence_from_reply(monkeypatch):
    import app.services.question_bank as qb
    _mock_call_llm(monkeypatch, qb, '```json\n{"body": "fenced rewrite"}\n```')

    result = await personalize_question(MCQ_QUESTION, cv_context="anything")

    assert result["body"] == "fenced rewrite"


# ── personalize_question: the security guarantee ──────────────────────────────

@pytest.mark.asyncio
async def test_personalize_never_leaks_answer_even_if_llm_tries_to_change_it(monkeypatch):
    """The core security test: even if the LLM reply actively tries to alter which option is
    correct (or inject new answer-bearing fields), the real answer must survive unchanged and
    _public_payload (what the browser actually receives) must never contain answer-bearing keys."""
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({
        "body": "rewritten stem",
        "options": [
            {"id": "a", "text": "This is now secretly the correct one"},
            {"id": "b", "text": "201 Created"},
            {"id": "c", "text": "404 Not Found"},
        ],
        # An adversarial/broken LLM reply trying to smuggle answer-bearing content back in:
        "answer_key": {"correct_id": "a"},
        "explanation": "a is correct (fabricated)",
    }))

    result = await personalize_question(MCQ_QUESTION, cv_context="anything")

    assert result["payload"]["answer_key"] == {"correct_id": "b"}
    assert result["payload"]["explanation"] == MCQ_QUESTION["payload"]["explanation"]

    public = _public_payload(result["payload"])
    for key in _ANSWER_KEYS:
        assert key not in public


@pytest.mark.asyncio
async def test_personalize_discards_option_rewrite_if_ids_dont_match(monkeypatch):
    """If the model drops/adds/renames an option id, the whole options rewrite must be discarded
    (not merged) — a partial match could scramble which id maps to which correct answer."""
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({
        "body": "rewritten stem",
        "options": [
            {"id": "a", "text": "still A"},
            {"id": "b", "text": "still B"},
            {"id": "d", "text": "an extra option that shouldn't exist"},
        ],
    }))

    result = await personalize_question(MCQ_QUESTION, cv_context="anything")

    assert result["payload"]["options"] == MCQ_QUESTION["payload"]["options"]


@pytest.mark.asyncio
async def test_personalize_falls_back_to_original_body_when_llm_call_fails(monkeypatch):
    import app.services.question_bank as qb
    _mock_call_llm(monkeypatch, qb, text=None, success=False)  # simulates exhausted retries

    result = await personalize_question(MCQ_QUESTION, cv_context="anything")

    assert result["body"] == MCQ_QUESTION["body"]
    assert result["payload"]["answer_key"] == MCQ_QUESTION["payload"]["answer_key"]


@pytest.mark.asyncio
async def test_personalize_falls_back_when_reply_is_unparseable_text(monkeypatch):
    import app.services.question_bank as qb
    _mock_call_llm(monkeypatch, qb, "sorry, I can't help with that")

    result = await personalize_question(MCQ_QUESTION, cv_context="anything")

    assert result["body"] == MCQ_QUESTION["body"]
    assert result["payload"]["options"] == MCQ_QUESTION["payload"]["options"]


@pytest.mark.asyncio
async def test_personalize_passes_session_id_through_to_call_llm(monkeypatch):
    """call_llm handles ai_logs itself now — confirm we actually pass session_id through so the
    log row can be traced back to the right session."""
    import app.services.question_bank as qb
    mock = _mock_call_llm(monkeypatch, qb, '{"body": "x"}')

    await personalize_question(MCQ_QUESTION, cv_context="anything", session_id="s-1")

    _, kwargs = mock.call_args
    assert kwargs["kind"] == "personalize"
    assert kwargs["session_id"] == "s-1"


# ── cv_estimate_levels ─────────────────────────────────────────────────────────

QUEUE = [{"id": COMPETENCY_A, "name": "Python"}, {"id": COMPETENCY_B, "name": "SQL"}]


@pytest.mark.asyncio
async def test_cv_estimate_returns_empty_when_no_cv(monkeypatch):
    import app.services.question_bank as qb
    mock = AsyncMock()
    monkeypatch.setattr(qb, "call_llm", mock)

    assert await cv_estimate_levels(None, QUEUE) == {}
    assert await cv_estimate_levels({}, QUEUE) == {}
    mock.assert_not_called()


@pytest.mark.asyncio
async def test_cv_estimate_parses_valid_estimates(monkeypatch):
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({COMPETENCY_A: 4, COMPETENCY_B: 2}))

    result = await cv_estimate_levels({"raw_text": "5 years Python, some SQL"}, QUEUE)

    assert result == {COMPETENCY_A: 4, COMPETENCY_B: 2}


@pytest.mark.asyncio
async def test_cv_estimate_ignores_unknown_competency_ids(monkeypatch):
    """The LLM must not be able to inject an estimate for a competency that wasn't in the queue."""
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({COMPETENCY_A: 4, "some-made-up-id": 5}))

    result = await cv_estimate_levels({"raw_text": "..."}, QUEUE)

    assert result == {COMPETENCY_A: 4}


@pytest.mark.asyncio
async def test_cv_estimate_clamps_out_of_range_values(monkeypatch):
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({COMPETENCY_A: 9, COMPETENCY_B: -3}))

    result = await cv_estimate_levels({"raw_text": "..."}, QUEUE)

    assert result == {COMPETENCY_A: 5, COMPETENCY_B: 1}


@pytest.mark.asyncio
async def test_cv_estimate_skips_non_numeric_values(monkeypatch):
    import app.services.question_bank as qb
    import json
    _mock_call_llm(monkeypatch, qb, json.dumps({COMPETENCY_A: "very good", COMPETENCY_B: 3}))

    result = await cv_estimate_levels({"raw_text": "..."}, QUEUE)

    assert result == {COMPETENCY_B: 3}


@pytest.mark.asyncio
async def test_cv_estimate_returns_empty_for_blank_cv_text(monkeypatch):
    import app.services.question_bank as qb
    mock = AsyncMock()
    monkeypatch.setattr(qb, "call_llm", mock)

    assert await cv_estimate_levels({"raw_text": "   "}, QUEUE) == {}
    mock.assert_not_called()


@pytest.mark.asyncio
async def test_cv_estimate_returns_empty_when_call_llm_fails(monkeypatch):
    import app.services.question_bank as qb
    _mock_call_llm(monkeypatch, qb, text=None, success=False)

    result = await cv_estimate_levels({"raw_text": "5 years Python"}, QUEUE)

    assert result == {}