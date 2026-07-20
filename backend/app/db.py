"""Supabase (Postgres) async client. Import get_db() where you need the DB."""
from __future__ import annotations
import os
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

load_dotenv()

_client: AsyncClient | None = None


async def init_db() -> None:
    global _client
    if _client is None:
        _client = await acreate_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


async def get_db() -> AsyncClient:
    if _client is None:
        await init_db()
    assert _client is not None
    return _client

# Usage:  db = await get_db();  await db.table("question_bank").select("*").execute()
