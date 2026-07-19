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
    time_limit_min: Optional[int] | None = 30

class AssessmentResponse(BaseModel):
    id: UUID
    question_set_id: UUID
    competency_ids: List[UUID]
    time_limit_min: Optional[int]
    

@router.get("/question-bank/types")
async def question_bank_types():
    """Serve the per-type payload spec to drive the admin 'add question' form + templates."""
    from app.schemas.question_types import QUESTION_TYPES
    return [{"tool_type": k, **v} for k, v in QUESTION_TYPES.items()]

@router.post("/question-bank/import")
async def import_bank(items: list[dict] = Body(...), set_name: str | None = None):
    """Import a fully-defined bank JSON and group it into a Question Set."""
    raise NotImplementedError

@router.get("/question-sets/{set_id}/competencies")
async def set_competencies(set_id: str):
    """The distinct TRACK competencies covered by a set's questions."""
    raise NotImplementedError

@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(payload: AssessmentCreate):
    """
    Takes a question_set_id, derives the unique competencies from its questions,
    and creates a new assessment row in the database.
    """
    db = await get_db()
    
    # 1. THE LOOKUP: Find all questions linked to this question_set_id
    items_response = await db.table("question_set_items").select("question_id").eq("set_id", str(payload.question_set_id)).execute()
    
    # If the set doesn't exist or is empty, trigger the 404 error
    if not items_response.data:
        raise HTTPException(status_code=404, detail="Question set not found")
        
    # Extract the question IDs into a list
    question_ids = [item["question_id"] for item in items_response.data]

    # 2. THE DERIVATION: Look up those specific questions in the bank to get their competencies
    bank_response = await db.table("question_bank").select("competency_id").in_("id", question_ids).execute()
    
    # Use a Python 'set' to instantly remove any duplicate competencies, then convert back to a list
    derived_competencies = list(set([str(q["competency_id"]) for q in bank_response.data if q.get("competency_id")]))

 
    # 3. THE INSERT: Create the assessment with the derived competencies
    new_assessment_data = {
        "title": payload.title, # <-- Add this line!
        "question_set_id": str(payload.question_set_id),
        "competency_ids": derived_competencies,
        "time_limit_min": payload.time_limit_min
    }
    
    insert_response = await db.table("assessments").insert(new_assessment_data).execute()
    
    if not insert_response.data:
        raise HTTPException(status_code=500, detail="Failed to create assessment")

    return insert_response.data[0]

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
