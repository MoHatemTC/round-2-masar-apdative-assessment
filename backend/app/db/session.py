"""
Supabase session provider.

Creates a singleton AsyncClient that can be injected
into FastAPI endpoints.

Environment variables:

SUPABASE_URL
SUPABASE_KEY
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from supabase import AsyncClient, acreate_client

load_dotenv()

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    """
    Returns a singleton Async Supabase client.

    Configuration is validated only when the
    client is actually requested.
    """

    global _client

    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url:
            raise RuntimeError(
                "SUPABASE_URL is not configured."
            )

        if not key:
            raise RuntimeError(
                "SUPABASE_KEY is not configured."
            )

        _client = await acreate_client(
            url,
            key,
        )

    return _client


async def get_db() -> AsyncClient:
    """
    FastAPI dependency.
    """
    return await get_supabase()


async def initialize_supabase() -> None:
    """
    Initializes the singleton during startup.
    """
    await get_supabase()


async def close_supabase() -> None:
    """
    Clears the cached client.
    """
    global _client
    _client = None