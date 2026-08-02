import asyncio
from app.db import get_db

VOICE_QUESTION = {
    "id": "b2c3d4e5-0000-4000-8000-000000000001",
    "competency_id": "6cdfd60e-cdf1-41bc-a4f7-b1d7c3f0189f",
    "tool_type": "voice",
    "difficulty": "medium",
    "body": "You need to build a prompt that summarizes incoming customer support tickets into structured fields. How would you design and validate it before shipping?",
    "is_active": True,
    "payload": {
        "time_limit_seconds": 120,
        "evaluation_criteria": [
            "Designs around a structured schema",
            "Includes few-shot edge cases",
            "Proposes a measurable eval bar",
            "Iterates on failure cases",
        ],
    },
}

async def main():
    db = await get_db()
    inserted = await db.table("question_bank").insert(VOICE_QUESTION).execute()
    print(f"Inserted: {inserted.data}")

asyncio.run(main())