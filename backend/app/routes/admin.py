"""Admin API: import a bank (→ set), create a set-driven assessment, list/review.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID

from app.db import get_db
from supabase import AsyncClient

router = APIRouter(prefix="/admin", tags=["admin"])

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
async def set_competencies(set_id: str, db: AsyncClient = Depends(get_db)):
    """The distinct TRACK competencies covered by a set's questions."""
    items_response = await db.table("question_set_items").select("question_id").eq("set_id", set_id).execute()
    if not items_response.data:
        raise HTTPException(status_code=404, detail="Question set not found")

    # Extract IDs and fetch the corresponding competencies from the bank
    question_ids = [item["question_id"] for item in items_response.data]
    bank_response = await db.table("question_bank").select("competency_id").in_("id", question_ids).execute()
    
    sub_ids = [q["competency_id"] for q in bank_response.data if q.get("competency_id")]
    
    # Map the sub-competencies up to their parent tracks
    competencies_response = await db.table("competencies").select("parent_id").in_("id", sub_ids).execute()
    track_ids = list(set(c["parent_id"] for c in competencies_response.data if c.get("parent_id")))
    
    return track_ids

@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(payload: AssessmentCreate, db: AsyncClient = Depends(get_db)):
    """Create a set-driven assessment, automatically deriving competencies."""
    # Automatically derive the competencies from the provided question set ID
    competencies_response = await set_competencies(str(payload.question_set_id), db)

    new_assessment_data = {
        "title": payload.title,
        "question_set_id": str(payload.question_set_id),
        "competency_ids": competencies_response,
        "time_limit_min": payload.time_limit_min,
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