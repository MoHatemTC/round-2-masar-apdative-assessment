
from __future__ import annotations

import os
import asyncio
import logging
from openai import AsyncOpenAI, APIError, APITimeoutError
from app.db import get_db

logger = logging.getLogger(__name__)

# --- Grading client (Gemini) ---
# Timeout raised from 30s -> 90s: grading prompts can legitimately take longer
# than 30s to generate on a slower/reasoning-heavy model, and killing the
# request mid-generation just guarantees a retry (or, after 3, a None score)
# instead of the answer we were already about to get.
_client = AsyncOpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    timeout=120.0,
)
MODEL = os.environ["LLM_MODEL"]

# --- STT client (Groq) — separate from grading, per the env split ---
_stt_client = AsyncOpenAI(
    base_url=os.environ["STT_BASE_URL"],
    api_key=os.environ["STT_API_KEY"],
    timeout=60.0,
)
STT_MODEL = os.environ["STT_MODEL"]

MAX_TOKENS = 2000
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0

VALID_KINDS = {"personalize", "grade", "cv_estimate", "stt", "generate"}


async def call_llm(prompt: str, *, kind: str, session_id: str | None = None, max_tokens: int | None = None) -> dict:
    """`max_tokens` lets a caller cap the reply size for kinds that don't need
    the full MAX_TOKENS budget (e.g. grading's short SCORE/RATIONALE format) —
    a tighter cap means the model finishes generating sooner, which reduces
    both wall-clock time and the odds of hitting the client timeout at all."""
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind {kind!r}. Must be one of {VALID_KINDS}")

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await _client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens or MAX_TOKENS,
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


async def call_stt(audio_bytes: bytes, filename: str, *, session_id: str | None = None) -> dict:
    """Transcribe audio via the STT client (Groq), same retry/backoff/logging contract as call_llm."""
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await _stt_client.audio.transcriptions.create(
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