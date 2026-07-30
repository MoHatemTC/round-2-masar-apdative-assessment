# demo/new_demo_session.py
"""Run this before each demo run to get a fresh, valid session_id.
Usage: python demo/new_demo_session.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.db import get_db

async def main():
    db = await get_db()
    existing_assessment = await db.table("assessments").select("id").limit(1).execute()
    if not existing_assessment.data:
        print("No assessments exist — create one first.")
        return
    assessment_id = existing_assessment.data[0]["id"]

    row = {
        "assessment_id": assessment_id,
        "candidate_name": "Demo Candidate",
        "intake_answers": {},
        "status": "in_progress",
    }
    result = await db.table("sessions").insert(row).execute()
    new_id = result.data[0]["id"]
    print(f"\nNew demo session created.")
    print(f"Update DEMO_SESSION_ID in page.tsx to:\n\n  {new_id}\n")

asyncio.run(main())