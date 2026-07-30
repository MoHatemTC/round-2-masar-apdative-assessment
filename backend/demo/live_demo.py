"""Live, wired demo of the voice pipeline — exactly as it runs in main.

This does NOT reimplement any business logic. It boots a real FastAPI app
with the real app.routes.transcribe.router mounted, and drives it with real
HTTP requests (multipart form data, real file bytes) via an in-process ASGI
transport — the same request shape VoiceRecorder.tsx sends.

The only things swapped out are the true external services this environment
can't reach: Supabase (app.db.get_db) and the OpenAI-compatible STT/LLM
gateway clients (app.services.llm._client / _stt_client). Everything from
the FastAPI route handler down through app/services/grading.py is the real,
unmodified production code.

Run: python demo/live_demo.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock

# --- env vars llm.py needs at import time (dummy — network is mocked) ---
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid")
os.environ.setdefault("LLM_API_KEY", "demo-key")
os.environ.setdefault("LLM_MODEL", "demo-model")
os.environ.setdefault("STT_BASE_URL", "https://example.invalid")
os.environ.setdefault("STT_API_KEY", "demo-key")
os.environ.setdefault("STT_MODEL", "demo-stt-model")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from openai import APITimeoutError  # noqa: E402

import demo.fake_db as fake_db  # noqa: E402
import app.services.llm as llm_module  # noqa: E402
import app.routes.transcribe as transcribe_module  # noqa: E402

# --- wire the fake DB into the real modules that call get_db() ---
transcribe_module.get_db = fake_db.get_db
llm_module.get_db = fake_db.get_db

# Demo-speed only: real backoff is 1/2/4s, which is correct for prod but slow
# to sit through here. This is a timing knob, not a logic change.
llm_module.BASE_BACKOFF_SECONDS = 0.01

QUESTION_ID = "q-aie1-02"
QUESTION_ROW = {
    "id": QUESTION_ID,
    "body": "You need to build a prompt that summarizes support tickets into structured fields...",
    "competency_id": "prompt-design",
    "payload": {
        "evaluation_criteria": [
            "Designs around a structured schema",
            "Includes few-shot edge cases",
            "Proposes a measurable eval bar",
            "Iterates on failure cases",
        ]
    },
}


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(transcribe_module.router)
    return app


def mock_llm_grade(score="4.5", rationale="Meets the criteria: structured schema, edge cases, measurable bar."):
    llm_module._client.chat.completions.create = AsyncMock(
        return_value=type("R", (), {
            "choices": [type("C", (), {"message": type("M", (), {"content": f"SCORE: {score}\nRATIONALE: {rationale}"})()})]
        })()
    )


def mock_stt_success(transcript="I'd design around a structured schema, add few-shot edge cases, set a measurable eval bar, and iterate on failures.", delay=0.0):
    async def _create(*args, **kwargs):
        if delay:
            await asyncio.sleep(delay)
        return type("R", (), {"text": transcript})()
    llm_module._stt_client.audio.transcriptions.create = AsyncMock(side_effect=_create)


def mock_stt_failure():
    llm_module._stt_client.audio.transcriptions.create = AsyncMock(
        side_effect=APITimeoutError(request=httpx.Request("POST", "https://example.invalid"))
    )


async def submit(client: httpx.AsyncClient, session_id: str, qn: int, *, audio_bytes: bytes | None, duration_ms: int = 15000, typed_answer: str | None = None):
    data = {"duration_ms": str(duration_ms), "question_id": QUESTION_ID}
    files = None
    if audio_bytes is not None:
        files = {"audio": ("answer.webm", audio_bytes, "audio/webm")}
    if typed_answer is not None:
        data["typed_answer"] = typed_answer
    resp = await client.post(f"/api/sessions/{session_id}/questions/{qn}/voice-answer", data=data, files=files)
    return resp


async def scenario_happy_path(client):
    print("\n=== Scenario 1: normal recording -> STT -> rubric grading ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])
    mock_stt_success()
    mock_llm_grade()

    resp = await submit(client, "sess-1", 1, audio_bytes=b"\x00" * 4096)
    body = resp.json()
    print(f"HTTP {resp.status_code} -> status={body['status']}")
    answer = body["answer"]
    print(f"  transcript: {answer['transcript']!r}")
    print(f"  score={answer['score']}  flagged={answer['flagged']}")
    print(f"  rationale: {answer['rationale']}")
    assert body["status"] == "submitted"
    assert answer["score"] == 4.5
    assert answer["flagged"] is False
    assert len(fake_db._singleton.dump("answers")) == 1


async def scenario_mic_denied(client):
    print("\n=== Scenario 2: mic denied -> typed fallback, flagged, session continues ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])
    mock_llm_grade(score="3.0", rationale="Reasonable structure but thin on edge cases.")

    resp = await submit(client, "sess-2", 1, audio_bytes=None, typed_answer="I'd use structured output and test it on a few examples.")
    body = resp.json()
    print(f"HTTP {resp.status_code} -> status={body['status']}")
    answer = body["answer"]
    print(f"  answer_text: {answer['answer_text']!r}")
    print(f"  score={answer['score']}  flagged={answer['flagged']}")
    print(f"  rationale: {answer['rationale']}")
    assert answer["flagged"] is True
    assert answer["rationale"].startswith("[No audio — typed fallback used]")
    print("  -> turn completed, no exception raised, session can continue")


async def scenario_no_audio_no_typed(client):
    print("\n=== Scenario 2b: mic denied AND nothing typed -> still completes the turn ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])

    resp = await submit(client, "sess-2b", 1, audio_bytes=None, typed_answer=None)
    body = resp.json()
    print(f"HTTP {resp.status_code} -> status={body['status']}")
    answer = body["answer"]
    print(f"  skipped={answer['skipped']}  flagged={answer['flagged']}  score={answer['score']}")
    assert resp.status_code == 200
    assert answer["skipped"] is True
    assert answer["flagged"] is True
    print("  -> no 400 error, no blocked session")


async def scenario_stt_failure(client):
    print("\n=== Scenario 3: STT gateway down -> flagged for manual review, audio kept ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])
    mock_stt_failure()

    resp = await submit(client, "sess-3", 1, audio_bytes=b"\x00" * 4096)
    body = resp.json()
    print(f"HTTP {resp.status_code} -> status={body['status']}")
    answer = body["answer"]
    print(f"  audio_url={answer['audio_url']}  transcript={answer['transcript']}")
    print(f"  score={answer['score']}  flagged={answer['flagged']}")
    print(f"  rationale: {answer['rationale']}")
    assert answer["audio_url"] is not None, "audio must not be lost on STT failure"
    assert answer["transcript"] is None
    assert answer["flagged"] is True
    print("  -> turn completed, audio preserved for manual review")


async def scenario_oversized_audio(client):
    print("\n=== Scenario 4: oversized recording -> clean rejection, retryable ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])
    mock_stt_success()
    mock_llm_grade()

    # Shrink the cap for the demo instead of allocating a real 25MB payload.
    original_max_bytes = transcribe_module.MAX_BYTES
    transcribe_module.MAX_BYTES = 100
    try:
        resp = await submit(client, "sess-4", 1, audio_bytes=b"\x00" * 4096)
        print(f"HTTP {resp.status_code} -> {resp.json()}")
        assert resp.status_code == 413
        assert len(fake_db._singleton.dump("answers")) == 0, "rejected upload must not claim the slot"

        # retry with audio under the (demo-shrunk) cap succeeds normally
        resp2 = await submit(client, "sess-4", 1, audio_bytes=b"\x00" * 50)
        body2 = resp2.json()
        print(f"retry -> HTTP {resp2.status_code} -> status={body2['status']}")
        assert body2["status"] == "submitted"
        print("  -> rejection didn't burn the (session, question) slot; retry worked")
    finally:
        transcribe_module.MAX_BYTES = original_max_bytes


async def scenario_reload_race(client):
    print("\n=== Scenario 5: reload mid-grade -> no duplicate row, no double STT call ===")
    fake_db.reset()
    fake_db._singleton.seed("question_bank", [QUESTION_ROW])
    mock_llm_grade()

    call_count = {"n": 0}

    async def _create(*args, **kwargs):
        call_count["n"] += 1
        await asyncio.sleep(0.3)  # wide window so both requests are genuinely in flight
        return type("R", (), {"text": "same transcript both times"})()

    llm_module._stt_client.audio.transcriptions.create = AsyncMock(side_effect=_create)

    r1, r2 = await asyncio.gather(
        submit(client, "sess-5", 1, audio_bytes=b"\x00" * 4096),
        submit(client, "sess-5", 1, audio_bytes=b"\x00" * 4096),
    )
    statuses = sorted([r1.json()["status"], r2.json()["status"]])
    print(f"  request A -> {r1.json()['status']}")
    print(f"  request B -> {r2.json()['status']}")
    print(f"  STT calls made: {call_count['n']}")
    print(f"  answer rows for (sess-5, q1): {len(fake_db._singleton.dump('answers'))}")

    assert statuses == ["already_submitted", "submitted"]
    assert call_count["n"] == 1, "STT must only be called once even under a concurrent resubmit"
    assert len(fake_db._singleton.dump("answers")) == 1, "must not create a duplicate row"
    print("  -> exactly one row written, exactly one STT call, no duplicate submission")


async def main():
    app = build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await scenario_happy_path(client)
        await scenario_mic_denied(client)
        await scenario_no_audio_no_typed(client)
        await scenario_stt_failure(client)
        await scenario_oversized_audio(client)
        await scenario_reload_race(client)

    print("\nAll scenarios passed against the real transcribe.router + grading.py + llm.py.")


if __name__ == "__main__":
    asyncio.run(main())
