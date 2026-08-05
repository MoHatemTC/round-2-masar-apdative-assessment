"""
Standalone repro for the fallback-question path, without needing to actually
exhaust a competency's real bank through a full session.

Usage:
    cd backend
    python debug_fallback.py

Forces select_competency_question to return None (simulating bank exhaustion),
then runs pick_question exactly as adaptive_loop.py would, and prints:
  1. What pick_question emitted to the frontend (state["_emit"])
  2. Whether that question actually landed in question_bank afterward

If step 2 shows the row missing or with null body/competency_id, the insert
in pick_question's fallback branch is failing — check the printed exception
(if any) or add the RuntimeError-on-empty-data check suggested earlier.
"""
import asyncio

from app.db import get_db
from app.agent import adaptive_loop


async def main():
    db = await get_db()

    # Grab any real, existing competency to attach the fallback question to —
    # generate_fallback_question doesn't care which, and this avoids a
    # foreign-key failure on a made-up id.
    comp_resp = await db.table("competencies").select("id,name").limit(1).execute()
    if not comp_resp.data:
        print("No competencies found in this DB — can't run the repro.")
        return
    competency_id = comp_resp.data[0]["id"]
    print(f"Using real competency: {comp_resp.data[0]}")

    session = {"id": "debug-session", "cv_json": None}
    state = {
        "queue": [competency_id],
        "active_index": 0,
        "question_number": 0,
        "per_competency": {
            competency_id: {
                "level": 3,
                "used_ids": [],
                "converged": False,
                "generated_questions": [],
                "asked_types": {},
            }
        },
    }

    # Force the bank-exhaustion branch regardless of what's actually in the
    # bank for this competency. select_competency_question is awaited, so the
    # replacement needs to be an async function.
    async def fake_select(*args, **kwargs):
        return None
    original_select = adaptive_loop.select_competency_question
    adaptive_loop.select_competency_question = fake_select
    try:
        result_state = await adaptive_loop.pick_question(db, session, state)
    finally:
        adaptive_loop.select_competency_question = original_select

    emitted = result_state.get("_emit")
    print("\n--- pick_question emitted to frontend ---")
    print(emitted)

    if not emitted or not emitted.get("id"):
        print("\nNo question was emitted at all — fallback generation itself failed.")
        print("Check the 'Fallback generation failed: ...' warning this should have logged.")
        return

    qid = emitted["id"]
    print(f"\n--- checking question_bank for id={qid} ---")
    row_resp = await db.table("question_bank").select("*").eq("id", qid).maybe_single().execute()
    row = row_resp.data if row_resp is not None else None

    if row is None:
        print("MISSING: no row in question_bank for this id at all.")
        print("The insert in pick_question's fallback branch did not persist anything.")
    else:
        print("FOUND row in question_bank:")
        print(row)
        if row.get("body") is None or row.get("competency_id") is None:
            print("\nRow exists but body/competency_id are null — insert ran but with bad values.")
        else:
            print("\nLooks correct — body and competency_id are populated.")


if __name__ == "__main__":
    asyncio.run(main())