"""Seeds ONE real question_bank row (via the real app.db.get_db(), your real
Supabase project) so the frontend demo page has a genuine question to render
and submit against — no fakes, no mocks.

Run once before the browser demo:
    python scripts/seed_demo_question.py

NOTE: if your schema has answers.session_id / question_bank rows with foreign
keys to other tables (e.g. a `sessions` table, a `competencies` table), you
may need to adjust this to satisfy those constraints first — I don't have
your schema, only what transcribe.py/grading.py read from these rows.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import get_db  # noqa: E402

DEMO_QUESTION_ID = "8f14e390-9b1a-4c1f-9e6a-9d6f0b7a1a11"
DEMO_SESSION_ID = "8f14e390-9b1a-4c1f-9e6a-9d6f0b7a1a22"
DEMO_QUESTION_NUMBER = 1

QUESTION_ROW = {
    "id": DEMO_QUESTION_ID,
    "body": (
        "You need to build a prompt that summarizes incoming customer support "
        "tickets into structured fields (issue_category, severity, "
        "customer_sentiment, requested_action) for automated triage. How would "
        "you design and validate it before shipping?"
    ),
    "competency_id": None,  # unknown real type/FK — null avoids guessing wrong the same way id did
    "tool_type": "voice",
    "is_active": True,
    "payload": {
        "time_limit_seconds": 120,
        "evaluation_criteria": [
            "Designs the prompt/output around a concrete structured schema (fields, allowed values, structured output) rather than free-form text",
            "Includes few-shot examples that cover edge cases (empty, ambiguous, multi-issue tickets), not just clean happy-path examples",
            "Proposes a concrete, measurable evaluation bar (e.g. a labeled eval set with a target accuracy) rather than eyeballing whether outputs look good",
            "Describes iterating specifically on failure cases rather than one-shot prompt tweaking",
        ],
    },
}


async def main():
    db = await get_db()
    existing = await db.table("question_bank").select("*").eq("id", DEMO_QUESTION_ID).maybe_single().execute()
    existing_row = existing.data if existing is not None else None
    if existing_row:
        print(f"question_bank row {DEMO_QUESTION_ID!r} already exists — leaving it as-is.")
    else:
        inserted = await db.table("question_bank").insert(QUESTION_ROW).execute()
        print(f"Inserted question_bank row: {inserted.data}")

    print()
    print("Use these in the demo page / manual test:")
    print(f"  session_id      = {DEMO_SESSION_ID!r}")
    print(f"  question_number = {DEMO_QUESTION_NUMBER}")
    print(f"  question_id     = {DEMO_QUESTION_ID!r}")
    print()
    print("If a previous demo run already answered this (session_id, question_number),")
    print("either bump DEMO_QUESTION_NUMBER above or delete that row from `answers` first —")
    print("submit_voice_answer's idempotency check will otherwise just return already_submitted.")


if __name__ == "__main__":
    asyncio.run(main())