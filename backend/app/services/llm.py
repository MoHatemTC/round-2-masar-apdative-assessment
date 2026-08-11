"""
llm.py — the single gateway for all LLM calls in this codebase.

No other module may call the LLM client directly. Every call goes through retries with
exponential backoff, a capped max_tokens, and is logged to ai_logs.

'vision' was added for the AI-Proctoring worker (see app/workers/proctoring_worker.py).
"""
from __future__ import annotations

import base64
import os
import asyncio
import logging
from typing import Iterable

from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI, APIError, APITimeoutError
from app.db import get_db

logger = logging.getLogger(__name__)

MAX_TOKENS = 2000
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0
VALID_KINDS = {"personalize", "grade", "cv_estimate", "stt", "generate", "vision"}

_client: AsyncOpenAI | None = None
_stt_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI | None:
    """Lazily build the grading client. Returns None if credentials
    aren't configured, so callers degrade gracefully instead of crashing the
    whole module at import time.
    """
    global _client
    if _client is None:
        base_url = os.environ.get("LLM_BASE_URL")
        api_key = os.environ.get("LLM_API_KEY")
        if not base_url or not api_key:
            return None
        _client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=120.0)
    return _client


def _get_stt_client() -> AsyncOpenAI | None:
    """Lazily build the STT client, separate from grading per the env split.
    Returns None if credentials aren't configured."""
    global _stt_client
    if _stt_client is None:
        base_url = os.environ.get("STT_BASE_URL")
        api_key = os.environ.get("STT_API_KEY")
        if not base_url or not api_key:
            return None
        _stt_client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=60.0)
    return _stt_client


MODEL = os.environ.get("LLM_MODEL", "")
VISION_MODEL = os.environ.get("LLM_VISION_MODEL", MODEL)
STT_MODEL = os.environ.get("STT_MODEL", "")


async def call_llm(prompt: str, *, kind: str, session_id: str | None = None, max_tokens: int | None = None) -> dict:
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind {kind!r}. Must be one of {VALID_KINDS}")

    client = _get_client()
    if client is None:
        logger.warning("LLM call skipped — LLM_BASE_URL/LLM_API_KEY not configured.")
        return {"success": False, "text": None, "error": "LLM is not configured."}

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens if max_tokens is not None else MAX_TOKENS,
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


# =============================================================================
# Vision variant — added for AI Proctoring (Week 3).
# =============================================================================

async def call_llm_vision(
    prompt: str,
    images: Iterable[bytes],
    *,
    session_id: str | None = None,
) -> dict:
    """
    Multimodal call: text prompt + one or more JPEG images.
    Returns: {"success": bool, "text": str | None, "error": str | None}
    """
    client = _get_client()
    if client is None:
        logger.warning("Vision call skipped — LLM not configured.")
        return {"success": False, "text": None, "error": "LLM is not configured."}

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
            response = await client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {"role": "system", "content": "You are a JSON-only API. Never use <think> tags or any reasoning blocks. Output ONLY the requested JSON array, nothing else."},
                    {"role": "user", "content": content},
                ],
                max_completion_tokens=MAX_TOKENS * 2,
            )
            # Some models (Qwen3) put the answer in .content and reasoning
            # in .reasoning_content. Fall back to reasoning if content is empty.
            msg = response.choices[0].message
            response_text = msg.content or getattr(msg, "reasoning_content", None) or ""
            await _safe_log(session_id=session_id, kind="vision", prompt=prompt, response=response_text)
            return {"success": True, "text": response_text, "error": None}
        except (APIError, APITimeoutError) as e:
            last_error = str(e)
            logger.warning(f"Vision call failed (attempt {attempt}/{MAX_RETRIES}): {last_error}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    await _safe_log(session_id=session_id, kind="vision", prompt=prompt, response=None)
    return {"success": False, "text": None, "error": last_error}


# =============================================================================
# STT (Speech-to-Text)
# =============================================================================

async def call_stt(audio_bytes: bytes, filename: str, *, session_id: str | None = None) -> dict:
    client = _get_stt_client()
    if client is None:
        logger.warning("STT call skipped — STT_BASE_URL/STT_API_KEY not configured.")
        return {"success": False, "text": None, "error": "STT is not configured."}

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.audio.transcriptions.create(
                model=STT_MODEL,
                file=(filename, audio_bytes),
            )
            response_text = response.text
            await _safe_log(session_id=session_id, kind="stt", prompt="[audio]", response=response_text)
            return {"success": True, "text": response_text, "error": None}
        except (APIError, APITimeoutError) as e:
            last_error = str(e)
            logger.warning(f"STT call failed (attempt {attempt}/{MAX_RETRIES}): {last_error}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    await _safe_log(session_id=session_id, kind="stt", prompt="[audio]", response=None)
    return {"success": False, "text": None, "error": last_error}


async def _safe_log(*, session_id: str | None, kind: str, prompt: str, response: str | None) -> None:
    try:
        await _log_to_ai_logs(session_id=session_id, kind=kind, prompt=prompt, response=response)
    except Exception as e:
        logger.warning(f"Failed to write ai_logs row (kind={kind}): {e}")


async def _log_to_ai_logs(*, session_id: str | None, kind: str, prompt: str, response: str | None) -> None:
    db = await get_db()
    await db.table("ai_logs").insert({
        "session_id": session_id,
        "kind": kind,
        "prompt": prompt,
        "response": response,
    }).execute()
