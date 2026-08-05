import asyncio
import uuid
from app.db import get_db

async def main():
    db = await get_db()
    row = {
        'assessment_id': '078d7ac5-e916-49cb-b1f7-88d3bdc80fc4',
        'candidate_email': 'test@example.com',
        'status': 'not-taken',
        'token': str(uuid.uuid4()),
    }
    result = await db.table('invitations').insert(row).execute()
    print(f"Token: {result.data[0]['token']}")

asyncio.run(main())