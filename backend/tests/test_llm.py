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

    create = AsyncMock(
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

    create = AsyncMock(side_effect=error)

    monkeypatch.setattr(
        llm,
        "_client",
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)
            )
        ),
    )
    log_mock = AsyncMock()
    monkeypatch.setattr(llm, "_log_to_ai_logs", log_mock)
    monkeypatch.setattr(llm.asyncio, "sleep", AsyncMock())

    result = asyncio.run(
        llm.call_llm("test prompt", kind="grade", session_id="fail-session")
    )

    # Must degrade gracefully -- return a failure dict, never raise.
    assert result["success"] is False
    assert result["text"] is None
    assert result["error"] == "LLM unavailable"
    assert create.call_count == llm.MAX_RETRIES

    # Failures must still be logged (response=None), same as successes.
    log_mock.assert_called_once_with(
        session_id="fail-session",
        kind="grade",
        prompt="test prompt",
        response=None,
    )


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


def test_logging_failure_does_not_crash(monkeypatch):
    """A Supabase/logging failure must never propagate out of call_llm."""
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="fine response"))]
        )
    )

    monkeypatch.setattr(
        llm,
        "_client",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
    )
    # Simulate the DB insert itself failing (e.g. network blip, schema drift) --
    # a completely different kind of error than APIError/APITimeoutError.
    monkeypatch.setattr(llm, "_log_to_ai_logs", AsyncMock(side_effect=RuntimeError("db unavailable")))

    # This must NOT raise -- call_llm's whole contract is "never raises".
    result = asyncio.run(llm.call_llm("test prompt", kind="grade"))

    assert result["success"] is True
    assert result["text"] == "fine response"


def test_logs_on_success(monkeypatch):
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="logged response"))]
        )
    )

    monkeypatch.setattr(
        llm,
        "_client",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
    )
    log_mock = AsyncMock()
    monkeypatch.setattr(llm, "_log_to_ai_logs", log_mock)

    result = asyncio.run(
        llm.call_llm("test prompt", kind="grade", session_id="abc-123")
    )

    assert result["success"] is True
    log_mock.assert_called_once_with(
        session_id="abc-123",
        kind="grade",
        prompt="test prompt",
        response="logged response",
    )