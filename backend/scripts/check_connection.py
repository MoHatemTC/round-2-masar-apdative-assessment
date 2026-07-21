import asyncio
from app.db import get_db

async def main():
    db = await get_db()
    result = await db.table("ai_logs").select("*").limit(1).execute()
    print("Connected. Sample ai_logs row(s):", result.data)

if __name__ == "__main__":
    asyncio.run(main()) 
