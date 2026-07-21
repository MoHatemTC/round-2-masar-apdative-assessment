"""
llm.py — the single gateway for all LLM calls in this codebase.

No other module may call the LLM client directly. Every call goes through retries with
exponential backoff, a capped max_tokens, and is logged to ai_logs.
"""
from __future__ import annotations

import os
import asyncio
import logging
from openai import AsyncOpenAI, APIError, APITimeoutError
from app.db import get_db  # adjust import path to match your actual db.py location

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
MODEL = os.environ.get("LLM_MODEL", "kimi-k2.5")
MAX_TOKENS = 2000
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0

# Must match the `kind` values allowed by the ai_logs table.
VALID_KINDS = {"personalize", "grade", "cv_estimate", "stt", "generate"}


async def call_llm(prompt: str, *, kind: str, session_id: str | None = None) -> dict:
    """
    Call the LLM with retries + exponential backoff. Logs the final outcome to ai_logs.
    ...
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind {kind!r}. Must be one of {VALID_KINDS}")

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await _client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=MAX_TOKENS,
            )
            response_text = response.choices[0].message.content
            await _safe_log(session_id=session_id, kind=kind, prompt=prompt, response=response_text)
            return {"success": True, "text": response_text, "error": None}

        except (APIError, APITimeoutError) as e:
            last_error = str(e)
            logger.warning(f"LLM call failed (attempt {attempt}/{MAX_RETRIES}): {last_error}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    await _safe_log(session_id=session_id, kind=kind, prompt=prompt, response=None)
    return {"success": False, "text": None, "error": last_error}


async def _safe_log(*, session_id: str | None, kind: str, prompt: str, response: str | None) -> None:
    """Wraps _log_to_ai_logs so a logging failure can never crash grading."""
    try:
        await _log_to_ai_logs(session_id=session_id, kind=kind, prompt=prompt, response=response)
    except Exception as e:
        logger.warning(f"Failed to write ai_logs row (kind={kind}): {e}")


async def _log_to_ai_logs(*, session_id: str | None, kind: str, prompt: str, response: str | None) -> None:
    """Insert one row into ai_logs, matching its real schema exactly."""
    db = await get_db()
    await db.table("ai_logs").insert({
        "session_id": session_id,
        "kind": kind,
        "prompt": prompt,
        "response": response,
    }).execute()
