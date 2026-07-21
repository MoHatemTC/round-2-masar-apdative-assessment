"""
Supabase session provider.

Creates a singleton AsyncClient that can be injected
into FastAPI endpoints.

Environment variables:

SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
"""

import os

from dotenv import load_dotenv
from supabase import (
    AsyncClient,
    acreate_client,
)

load_dotenv()

# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY"
)

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL is not configured."
    )

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        "SUPABASE_SERVICE_ROLE_KEY is not configured."
    )

# ---------------------------------------------------------
# Singleton Client
# ---------------------------------------------------------

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    """
    Returns a singleton Async Supabase client.
    Used as a FastAPI dependency.
    """

    global _client

    if _client is None:
        _client = await acreate_client(
            SUPABASE_URL,
            SUPABASE_SERVICE_ROLE_KEY,
        )

    return _client


# ---------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------

async def get_db() -> AsyncClient:
    """
    Alias used by routes.

    Allows:
        Depends(get_db)
    """

    return await get_supabase()


# ---------------------------------------------------------
# Startup helper
# ---------------------------------------------------------

async def initialize_supabase() -> None:
    """
    Initializes the singleton client during
    FastAPI startup.
    """

    await get_supabase()


# ---------------------------------------------------------
# Shutdown helper
# ---------------------------------------------------------

async def close_supabase() -> None:
    """
    Clears the cached client reference.
    """

    global _client
    _client = None