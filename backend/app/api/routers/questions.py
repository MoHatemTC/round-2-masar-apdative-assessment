"""
Question Bank browse endpoints.

Provides read-only browsing with filters:

- tool_type
- competency
- difficulty

Pure API layer.

FastAPI -> Supabase
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from supabase import AsyncClient
from app.db.session import get_supabase
from uuid import UUID


router = APIRouter(
    prefix="/questions",
    tags=["Question Bank"],
)


@router.get("/")
async def browse_questions(
    tool_type: Optional[str] = Query(None),
    competency: Optional[str] = Query(None),
    difficulty: Optional[int] = Query(None),
    db: AsyncClient = Depends(get_supabase),
):
    """
    Browse Question Bank.

    Supports optional filters.

    Examples

    /questions

    /questions?tool_type=coding

    /questions?competency=<uuid>

    /questions?difficulty=3
    """

    query = (
        db.table("question_bank")
        .select(
            """
            id,
            body,
            tool_type,
            difficulty,
            competency:competencies(
                id,
                code,
                name
            )
            """
        )
        .eq("is_active", True)
    )

    if tool_type:
        query = query.eq(
            "tool_type",
            tool_type,
        )

    if difficulty is not None:
        query = query.eq("difficulty", difficulty)

    if competency:
        query = query.eq(
            "competency_id",
            competency,
        )

    result = await query.execute()

    items = []

    for row in result.data or []:
        comp = row.get("competency") or {}

        items.append(
            {
                "id": row["id"],
                "text": row["body"],
                "tool_type": row["tool_type"],
                "difficulty": row["difficulty"],
                "competency": {
                    "id": comp.get("id"),
                    "name": comp.get("name") or comp.get("code") or "",
                },
            }
        )
    
    return items

@router.get("/competencies")
async def list_competencies(
    db: AsyncClient = Depends(get_supabase),
):
    result = (
        await db.table("competencies")
        .select("id, name, code")
        .order("name")
        .execute()
    )

    return result.data

@router.get("/{question_id}")
async def get_question(
    question_id: UUID,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Get one question.
    """

    result = (
        await db.table("question_bank")
        .select(
            """
            id,
            body,
            tool_type,
            difficulty,
            competency:competencies(
                id,
                code,
                name
            )
            """
        )
        .eq("id", question_id)
        .single()
        .execute()
    )

    row = result.data or {}
    comp = row.get("competency") or {}

    return {
        "id": row["id"],
        "text": row["body"],
        "tool_type": row["tool_type"],
        "difficulty": row["difficulty"],
        "competency": {
            "id": comp.get("id"),
            "name": comp.get("name") or comp.get("code") or "",
        },
    }