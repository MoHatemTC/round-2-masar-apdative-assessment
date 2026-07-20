
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from openai import APIError

from app.services import llm


def test_retry_then_success(monkeypatch):
    first_error = APIError(
        message="temporary failure",
        request=Mock(),
        body=None,
    )

    create = Mock(
        side_effect=[
            first_error,
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="success response")
                    )
                ]
            ),
        ]
    )

    monkeypatch.setattr(
        llm,
        "_client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        ),
    )
    monkeypatch.setattr(llm, "_log_to_ai_logs", AsyncMock())
    monkeypatch.setattr(llm.asyncio, "sleep", AsyncMock())

    result = asyncio.run(
        llm.call_llm("test prompt", kind="grade")
    )

    assert result == {
        "success": True,
        "text": "success response",
        "error": None,
    }
    assert create.call_count == 2


def test_all_retries_fail_returns_failure(monkeypatch):
    error = APIError(
        message="LLM unavailable",
        request=Mock(),
        body=None,
    )

    create = Mock(side_effect=error)

    monkeypatch.setattr(
        llm,
        "_client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        ),
    )
    monkeypatch.setattr(llm, "_log_to_ai_logs", AsyncMock())
    monkeypatch.setattr(llm.asyncio, "sleep", AsyncMock())

    result = asyncio.run(
        llm.call_llm("test prompt", kind="grade")
    )

    assert result["success"] is False
    assert result["text"] is None
    assert result["error"] == "LLM unavailable"
    assert create.call_count == llm.MAX_RETRIES


def test_invalid_kind_raises():
    try:
        asyncio.run(
            llm.call_llm(
                "test prompt",
                kind="invalid_kind",
            )
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Invalid kind" in str(exc)