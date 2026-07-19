"""Admin API: import a bank (→ set), create a set-driven assessment, list/review.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from app.db import get_db
from app.schemas.question_types import validate_question_payload

router = APIRouter(prefix="/admin", tags=["admin"])

class AssessmentCreate(BaseModel):
    title: str
    question_set_id: UUID
    time_limit_min: Optional[int] = 30


class AssessmentResponse(BaseModel):
    id: UUID
    title: str
    question_set_id: UUID
    competency_ids: List[UUID]
    time_limit_min: Optional[int] = 30
    

@router.get("/question-bank/types")
async def question_bank_types():
    """Serve the per-type payload spec to drive the admin 'add question' form + templates."""
    from app.schemas.question_types import QUESTION_TYPES
    return [{"tool_type": k, **v} for k, v in QUESTION_TYPES.items()]

@router.post("/question-bank/import")
async def import_bank(items: list[dict] = Body(...), set_name: str | None = None):
    """Import a fully-defined bank JSON and group it into a Question Set.
    TODO:
      1. Validate every item's payload (validate_question_payload) → 422 with per-row errors.
      2. Upsert competencies: tracks (by code), then subs (by code, parent = track).
      3. Upsert questions on source_ref (preserve difficulty!). Link competency_id = sub.
      4. Create/find a question_set named `set_name` (default: the track name(s)); add all items.
      5. Return {tracks, sub_competencies, questions, set: {id, name, item_count}}.
    """
    raise NotImplementedError

@router.get("/question-sets/{set_id}/competencies")
async def set_competencies(set_id: str):
    """The distinct TRACK competencies covered by a set's questions (subs roll up to parent).
    Used by the assessment form to auto-derive what an assessment measures. TODO."""
    db = await get_db()

    items_response = (
        await db.table("question_set_items")
        .select("question_id")
        .eq("set_id", set_id)
        .execute()
    )

    if not items_response.data:
        raise HTTPException(status_code=404, detail="Question set not found")

    question_ids = [item["question_id"] for item in items_response.data]

    bank_response = (
        await db.table("question_bank")
        .select("competency_id")
        .in_("id", question_ids)
        .execute()
    )

    sub_ids = [
        question["competency_id"]
        for question in bank_response.data
        if question.get("competency_id")
    ]

    competencies_response = (
        await db.table("competencies")
        .select("parent_id")
        .in_("id", sub_ids)
        .execute()
    )

    track_ids = list(
        set(
            competency["parent_id"]
            for competency in competencies_response.data
            if competency.get("parent_id")
        )
    )

    return track_ids

@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(payload: AssessmentCreate):
    """Create a set-driven assessment.
    TODO: if body has question_set_id and no competency_ids → derive them from the set
    (set_competencies). Insert into `assessments`. Return the row."""
    db = await get_db()

    competencies_response = await set_competencies(
        str(payload.question_set_id)
    )

    new_assessment_data = {
        "title": payload.title,
        "question_set_id": str(payload.question_set_id),
        "competency_ids": competencies_response,
        "time_limit_min": payload.time_limit_min,
    }

    insert_response = (
        await db.table("assessments")
        .insert(new_assessment_data)
        .execute()
    )

    if not insert_response.data:
        raise HTTPException(
            status_code=500,
            detail="Failed to create assessment",
        )

    return insert_response.data[0]
    
@router.get("/assessments", response_model=List[AssessmentResponse])
async def list_assessments():
    """
    Queries the database for all created assessments
    and returns them to the admin dashboard.
    """
    db = await get_db()
    response = await db.table("assessments").select("*").execute()
    return response.data


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Return the final_reports row + per-competency results for the admin review page. TODO."""
    raise NotImplementedError
