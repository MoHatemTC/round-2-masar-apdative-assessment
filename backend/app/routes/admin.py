"""Admin API: import a bank (→ set), create a set-driven assessment, list/review.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from app.db import get_db
from app.schemas.question_types import validate_question_payload

router = APIRouter(prefix="/admin", tags=["admin"])

# --- SCHEMAS FOR YOUR TASK (Data Validation) ---
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
    raise NotImplementedError

@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(payload: AssessmentCreate):
    """Create a set-driven assessment.
    TODO: if body has question_set_id and no competency_ids → derive them from the set
    (set_competencies). Insert into `assessments`. Return the row."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
    
@router.get("/assessments", response_model=List[AssessmentResponse])
async def list_assessments():
    """
    Queries the database for all created assessments
    and returns them to the admin dashboard.
    """
    db = await get_db()
    
    # Grab every row from the assessments table
    response = await db.table("assessments").select("*").execute()
    
    # Return the real list of assessments instead of an empty list []
    return response.data


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Return the final_reports row + per-competency results for the admin review page. TODO."""
    raise NotImplementedError
