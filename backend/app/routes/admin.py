"""
Admin API:
- Import question bank
- Create question-set driven assessments
- List assessments
- Review reports
"""

from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID


from app.db import get_db
from supabase import AsyncClient

from app.ingestion.schemas import (
    QuestionBankImport,
)

from app.ingestion.validators import (
    validate_import,
)

from app.ingestion.upserts import (
    import_question_bank,
)


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


# =========================================================
# Assessment Schemas
# =========================================================


class AssessmentCreate(BaseModel):

    title: str

    question_set_id: UUID

    time_limit_min: int | None = 30



class AssessmentResponse(BaseModel):

    id: UUID

    title: str

    question_set_id: UUID

    competency_ids: list[UUID]

    time_limit_min: int | None = 30



# =========================================================
# Question Types
# =========================================================


@router.get("/question-bank/types")
async def question_bank_types():

    from app.schemas.question_types import QUESTION_TYPES

    return [
        {
            "tool_type": key,
            **value,
        }
        for key, value in QUESTION_TYPES.items()
    ]



# =========================================================
# Question Bank Import
# =========================================================


@router.post("/question-bank/import")
async def import_bank(
    payload: QuestionBankImport,
):

    """
    Import Question Bank.

    Flow:

    JSON
      |
      v
    Pydantic validation
      |
      v
    Business validation
      |
      v
    import_question_bank()
      |
      v
    Supabase upserts
    """


    errors = validate_import(
        payload
    )


    if errors:

        return {

            "success": False,

            "competencies_imported": 0,

            "questions_imported": 0,

            "question_set_items_imported": 0,

            "errors": errors,

        }



    db = await get_db()



    try:

        await import_question_bank(
            db,
            payload,
        )


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {exc}",
        )



    return {

        "success": True,

        "competencies_imported":
            len(payload.competencies),

        "questions_imported":
            len(payload.questions),

        "question_set_items_imported":
            len(payload.question_set.items),

        "errors": [],

    }



# =========================================================
# Question Set Competencies
# =========================================================


@router.get("/question-sets/{set_id}/competencies")
async def set_competencies(
    set_id: str,
):
    """
    Return UUIDs of the parent competencies
    covered by a question set.
    """

    db = await get_db()

    items_response = (
        await db.table("question_set_items")
        .select("question_id")
        .eq("set_id", set_id)
        .execute()
    )

    if not items_response.data:
        raise HTTPException(
            status_code=404,
            detail="Question set not found",
        )

    question_ids = [
        item["question_id"]
        for item in items_response.data
    ]

    questions_response = (
        await db.table("question_bank")
        .select("competency_id")
        .in_("id", question_ids)
        .execute()
    )

    sub_ids = list(
        {
            q["competency_id"]
            for q in questions_response.data
            if q.get("competency_id")
        }
    )

    if not sub_ids:
        return []

    competencies_response = (
        await db.table("competencies")
        .select("parent_id")
        .in_("id", sub_ids)
        .execute()
    )

    track_ids = list(
        {
            row["parent_id"]
            for row in competencies_response.data
            if row.get("parent_id")
        }
    )

    return track_ids

# =========================================================
# Create Assessment
# =========================================================


@router.post(
    "/assessments",
    response_model=AssessmentResponse,
)
async def create_assessment(
    payload: AssessmentCreate,
):


    db = await get_db()



    competency_ids = await set_competencies(
        str(payload.question_set_id)
    )



    new_assessment = {

        "title":
            payload.title,

        "question_set_id":
            str(payload.question_set_id),

        "competency_ids":
            competency_ids,

        "time_limit_min":
            payload.time_limit_min,

    }

    # Insert the derived assessment into the database
    insert_response = await db.table("assessments").insert(new_assessment_data).execute()
    
    if not insert_response.data:
        raise HTTPException(status_code=500, detail="Failed to create assessment")

    return insert_response.data[0]
    
@router.get("/assessments", response_model=list[AssessmentResponse])
async def list_assessments(db: AsyncClient = Depends(get_db)):
    """
    Queries the database for all created assessments
    and returns them to the admin dashboard.
    """
    response = await db.table("assessments").select("*").execute()
    return response.data


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Return the final_reports row + per-competency results for the admin review page. TODO."""
    raise NotImplementedError

@router.get("/assessments/{assessment_id}/invitations")
async def list_invitations(assessment_id: UUID, db: AsyncClient = Depends(get_db)):
    """Lists invitations and cross-references session status for each candidate."""
    # Fetch all invitations for the given assessment
    invitations_response = await db.table("invitations").select("*").eq("assessment_id", str(assessment_id)).execute()
    invitations = invitations_response.data or []

    # Fetch all session statuses for the given assessment
    sessions_response = await db.table("sessions").select("candidate_email, status").eq("assessment_id", str(assessment_id)).execute()
    sessions_map = {s["candidate_email"]: s["status"] for s in sessions_response.data} if sessions_response.data else {}

    results = []
    # Cross-reference the candidate emails to determine the actual status
    for inv in invitations:
        email = inv.get("candidate_email")
        session_status = sessions_map.get(email)
        
        if session_status == "completed":
            status_label = "taken"
        elif session_status:
            status_label = "in_progress"
        else:
            status_label = "not_taken"
            
        results.append({
            "id": inv.get("id"),
            "candidate_email": email,
            "status": status_label,
            "invited_at": inv.get("created_at")
        })

    return results
