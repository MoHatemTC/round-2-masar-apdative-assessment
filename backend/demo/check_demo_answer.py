"""Run this AFTER recording and submitting a real answer through the browser
demo page, to confirm it actually landed correctly in the real database.

    python scripts/check_demo_answer.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_db  # noqa: E402

DEMO_SESSION_ID = "8f14e390-9b1a-4c1f-9e6a-9d6f0b7a1a22"
DEMO_QUESTION_NUMBER = 1


def _print_row(label, row):
    print(f"\n{label}:")
    if not row:
        print("  <none found>")
        return
    for k, v in row.items():
        val = str(v)
        if len(val) > 200:
            val = val[:200] + "... (truncated)"
        print(f"  {k}: {val}")


async def main():
    db = await get_db()

    answer = await db.table("answers").select("*").eq(
        "session_id", DEMO_SESSION_ID
    ).eq("question_number", DEMO_QUESTION_NUMBER).maybe_single().execute()
    answer_row = answer.data if answer is not None else None
    _print_row("answers row", answer_row)

    logs = await db.table("ai_logs").select("*").eq("session_id", DEMO_SESSION_ID).execute()
    print(f"\nai_logs rows for this session: {len(logs.data or [])}")
    for row in (logs.data or []):
        _print_row(f"  ai_logs[{row.get('kind')}]", row)

    if not answer_row:
        print("\nNo answer row yet — did you submit through the demo page first?")
        return

    print("\n--- Summary ---")
    print(f"transcript present: {bool(answer_row.get('transcript'))}")
    print(f"score:              {answer_row.get('score')}")
    print(f"flagged:            {answer_row.get('flagged')}")
    print(f"audio_url:          {answer_row.get('audio_url')}")
    expected_kinds = {"stt", "grade"}
    seen_kinds = {row.get("kind") for row in (logs.data or [])}
    missing = expected_kinds - seen_kinds
    if missing:
        print(f"WARNING: no ai_logs row for kind(s) {missing} — check that call_llm/call_stt logging isn't silently failing.")
    else:
        print("Both stt and grade calls were logged to ai_logs. ✔")


if __name__ == "__main__":
    asyncio.run(main())