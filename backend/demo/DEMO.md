# Week 3 voice E2E — wired demo

## Running it

`live_demo.py` boots a **real FastAPI app** with the **real**
`app.routes.transcribe.router` mounted, and drives it with real HTTP
requests (multipart form data, real file bytes, `httpx` + ASGI transport) —
the same request shape `VoiceRecorder.tsx` sends. Nothing in the request
path is reimplemented.

The only things swapped out are the two things this sandbox literally
cannot reach: Supabase and the OpenAI-compatible STT/LLM gateway. Everything
from the route handler down through `grading.py` and `llm.py` (retries,
backoff, `ai_logs` write attempt, parsing) is the real production code,
unmodified.

Drop `fake_db.py` and `live_demo.py` next to your real `app/` package and run:

```
python demo/live_demo.py
```

It runs six scenarios end-to-end and asserts on the actual responses:

1. Normal recording → STT → rubric grading
2. Mic denied → typed fallback, flagged, session continues
3. Mic denied AND nothing typed → still completes the turn (no 400 block)
4. STT gateway down → flagged for manual review, audio preserved
5. Oversized upload → clean 413, slot not burned, retry succeeds
6. **Reload mid-grade** → two real concurrent requests for the same
   `(session_id, question_number)`, STT artificially slowed to widen the
   race window. Asserts exactly one STT call and one DB row.

## Wiring it to your real app instead

To point this at your actual FastAPI app rather than a throwaway one built
here, skip `build_app()` and instead:

```python
from app.main import app  # your real app
transport = httpx.ASGITransport(app=app)
```

and drop the two `get_db` monkeypatches — against real infra you'd instead
point `LLM_BASE_URL`/`STT_BASE_URL`/etc at a staging gateway and use your
real Supabase project (ideally a disposable test session/question row, not
production data).

## For the actual "one live demo session" deliverable

This script proves the *code paths* work end-to-end and is a good thing to
attach as evidence, but it isn't itself the deliverable — that's a real
recorded human voice, transcribed and graded, in a real running session.
For that:

1. Confirm the unique constraint exists —
   `UNIQUE (session_id, question_number)` on `answers` — required by the
   claim/finalize logic in `transcribe.py`. This demo's `fake_db.py`
   enforces it in-memory to prove the code handles it; your real Postgres
   table needs the actual constraint for the same guarantee to hold.
2. Open a real assessment session in Chrome, reach a `tool_type: voice`
   question, record ~20s of real audio, submit.
3. Capture: the `/voice-answer` response, the resulting `answers` row
   (transcript, score, rationale, flagged), and the `ai_logs` rows for
   both the `stt` and `grade` calls.
4. Repeat the mic-denied path once for real (deny permission in the
   browser, type an answer instead) and screenshot the flagged result.
5. Run the golden suite against the live model and attach the output:
   `pytest -m eval tests/test_golden_eval.py -v`
