"""
Question Set endpoints.

Provides:

- Create/Update Question Sets
- List Question Sets
- Get Question Set
- Delete Question Set
- GET /admin/question-sets/{id}/competencies

Uses Supabase AsyncClient.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import AsyncClient

from app.db.session import get_supabase

router = APIRouter(
    prefix="/admin/question-sets",
    tags=["Question Sets"],
)


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class QuestionSetCreate(BaseModel):
    name: str
    description: str | None = None


# ---------------------------------------------------------
# Create / Update
# ---------------------------------------------------------

@router.post("/")
async def create_or_update_question_set(
    payload: QuestionSetCreate,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Upsert Question Set by name.
    """

    result = (
        await db.table("question_sets")
        .upsert(
            {
                "name": payload.name,
                "description": payload.description,
            },
            on_conflict="name",
        )
        .execute()
    )

    return result.data


# ---------------------------------------------------------
# List
# ---------------------------------------------------------

@router.get("/")
async def list_question_sets(
    db: AsyncClient = Depends(get_supabase),
):
    """
    Return all question sets.
    """

    result = (
        await db.table("question_sets")
        .select("*")
        .order("name")
        .execute()
    )

    return result.data


# ---------------------------------------------------------
# Get One
# ---------------------------------------------------------

@router.get("/{question_set_id}")
async def get_question_set(
    question_set_id: int,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Get one question set with its questions.
    """

    result = (
        await db.table("question_sets")
        .select(
            """
            *,
            question_set_items(
                position,
                questions(
                    id,
                    source_ref,
                    text,
                    difficulty,
                    tool_type
                )
            )
            """
        )
        .eq("id", question_set_id)
        .single()
        .execute()
    )

    if result.data is None:
        raise HTTPException(
            status_code=404,
            detail="Question set not found.",
        )

    return result.data


# ---------------------------------------------------------
# Delete
# ---------------------------------------------------------

@router.delete("/{question_set_id}")
async def delete_question_set(
    question_set_id: int,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Delete a question set.

    Question records remain intact.
    """

    await (
        db.table("question_set_items")
        .delete()
        .eq("question_set_id", question_set_id)
        .execute()
    )

    await (
        db.table("question_sets")
        .delete()
        .eq("id", question_set_id)
        .execute()
    )

    return {
        "success": True
    }


# ---------------------------------------------------------
# Required Endpoint
# ---------------------------------------------------------

@router.get("/{question_set_id}/competencies")
async def question_set_competencies(
    question_set_id: int,
    db: AsyncClient = Depends(get_supabase),
):
    """
    Returns the distinct competencies
    represented in a Question Set.

    Required by the assignment.
    """

    result = (
        await db.table("question_set_items")
        .select(
            """
            questions(
                competency_id,
                competencies(
                    id,
                    code,
                    name
                )
            )
            """
        )
        .eq(
            "question_set_id",
            question_set_id,
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail="Question set not found.",
        )

    competencies = {}

    for item in result.data:

        question = item.get("questions")

        if not question:
            continue

        competency = question.get("competencies")

        if not competency:
            continue

        competencies[
            competency["id"]
        ] = competency

    return list(
        competencies.values()
    )