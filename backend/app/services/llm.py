"""
llm.py — the single gateway for all LLM calls in this codebase.

No other module may call the LLM client directly. Every call goes through retries with
exponential backoff, a capped max_tokens, and is logged to ai_logs.
"""
from __future__ import annotations

import base64
import os
import asyncio
import logging
from typing import Iterable

from openai import AsyncOpenAI, APIError, APITimeoutError

from app.db import get_db

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

MODEL = os.environ.get("LLM_MODEL", "kimi-k2.5")
# Separate model for vision — set to whatever multimodal endpoint your provider offers.
# Falls back to MODEL so single-model deployments still work.
VISION_MODEL = os.environ.get("LLM_VISION_MODEL", MODEL)

MAX_TOKENS = 2000
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0

# Must match the `kind` values allowed by the ai_logs table.
# 'vision' was added for the AI-Proctoring worker (see app/workers/proctoring_worker.py).
VALID_KINDS = {"personalize", "grade", "cv_estimate", "stt", "generate", "vision"}


async def call_llm(prompt: str, *, kind: str, session_id: str | None = None) -> dict:
    """
    Call the LLM with retries + exponential backoff. Logs the final outcome to ai_logs.

    `kind` must be one of VALID_KINDS (matches the ai_logs.kind column's expected values).
    `session_id` is optional — pass it when the call happens within a candidate session,
    so the log row can be traced back to that session.

    Returns: {"success": bool, "text": str | None, "error": str | None}
    Never raises — callers (like grade_answer) must be able to degrade gracefully.
    A failure to WRITE the log (separate from a failure to call the LLM) is also
    swallowed, so telemetry can never take down grading.
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

    # All retries exhausted — log the failure too (response left null), then return gracefully.
    await _safe_log(session_id=session_id, kind=kind, prompt=prompt, response=None)
    return {"success": False, "text": None, "error": last_error}


# =============================================================================
# Vision variant — added for AI Proctoring (Week 3).
# Same contract as call_llm: never raises, always returns the {success, text, error} dict,
# always logs to ai_logs. Callers batch several frames + one reference photo into a single
# call to keep cost bounded (see app/workers/proctoring_worker.py).
# =============================================================================

async def call_llm_vision(
    prompt: str,
    images: Iterable[bytes],
    *,
    session_id: str | None = None,
) -> dict:
    """
    Multimodal call: text prompt + one or more JPEG images.

    Images are passed as base64 data URLs. The provider is expected to be
    OpenAI-compatible (the same base_url the rest of the codebase uses).

    Returns: {"success": bool, "text": str | None, "error": str | None}
    """
    content: list[dict] = [{"type": "text", "text": prompt}]
    for img in images:
        b64 = base64.b64encode(img).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await _client.chat.completions.create(
                model=VISION_MODEL,
                messages=[{"role": "user", "content": content}],
                max_completion_tokens=MAX_TOKENS,
            )
            response_text = response.choices[0].message.content
            # Only the text prompt is logged (base64 images would blow up ai_logs).
            await _safe_log(session_id=session_id, kind="vision", prompt=prompt, response=response_text)
            return {"success": True, "text": response_text, "error": None}

        except (APIError, APITimeoutError) as e:
            last_error = str(e)
            logger.warning(f"Vision call failed (attempt {attempt}/{MAX_RETRIES}): {last_error}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    await _safe_log(session_id=session_id, kind="vision", prompt=prompt, response=None)
    return {"success": False, "text": None, "error": last_error}


async def _safe_log(*, session_id: str | None, kind: str, prompt: str, response: str | None) -> None:
    """Wraps _log_to_ai_logs so a logging/DB failure can never crash call_llm's caller."""
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
