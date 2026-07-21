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

    /questions?competency=PYTHON

    /questions?difficulty=3
    """

    query = (
        db.table("questions")
        .select(
            """
            id,
            source_ref,
            text,
            tool_type,
            difficulty,
            competency:competencies(
                code,
                name
            )
            """
        )
    )

    if tool_type:
        query = query.eq(
            "tool_type",
            tool_type,
        )

    if difficulty:
        query = query.eq(
            "difficulty",
            difficulty,
        )

    if competency:
        query = query.eq(
            "competencies.code",
            competency,
        )

    result = await query.execute()

    return result.data


@router.get("/{question_id}")
async def get_question(
    question_id: int,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Get one question.
    """

    result = (
        await db.table("questions")
        .select(
            """
            *,
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

    return result.data


@router.get("/competency/{code}")
async def questions_by_competency(
    code: str,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Browse questions by competency code.
    """

    result = (
        await db.table("questions")
        .select(
            """
            *,
            competency:competencies(
                code,
                name
            )
            """
        )
        .eq(
            "competencies.code",
            code,
        )
        .execute()
    )

    return result.data


@router.get("/difficulty/{difficulty}")
async def questions_by_difficulty(
    difficulty: int,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Browse questions by difficulty.

    2 = easy

    3 = medium

    4 = hard
    """

    result = (
        await db.table("questions")
        .select("*")
        .eq(
            "difficulty",
            difficulty,
        )
        .execute()
    )

    return result.data


@router.get("/tool/{tool_type}")
async def questions_by_tool(
    tool_type: str,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Browse by tool type.
    """

    result = (
        await db.table("questions")
        .select("*")
        .eq(
            "tool_type",
            tool_type,
        )
        .execute()
    )

    return result.data