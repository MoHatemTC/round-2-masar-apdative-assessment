"""
Database package.

Exports the shared Supabase session dependency.
"""

from .session import (
    get_db,
    get_supabase,
    initialize_supabase,
    close_supabase,
)

__all__ = [
    "get_db",
    "get_supabase",
    "initialize_supabase",
    "close_supabase",
]