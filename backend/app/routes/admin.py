"""Admin API: import a bank (→ set), create a set-driven assessment, list/review.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

# from app.db import get_db
from app.schemas.question_types import validate_question_payload

router = APIRouter(prefix="/admin", tags=["admin"])

# --- SCHEMAS FOR YOUR TASK (Data Validation) ---
class AssessmentCreate(BaseModel):
    question_set_id: UUID
    time_limit_min: Optional[int] = 30

class AssessmentResponse(BaseModel):
    id: UUID
    question_set_id: UUID
    competency_ids: List[str]
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


# --- ROUTES FOR YOUR TASK (The "Doors") ---

@router.post("/assessments", response_model=AssessmentResponse)
async def create_assessment(payload: AssessmentCreate):
    """
    SCAFFOLD: This will eventually receive a question_set_id, 
    look up the competencies for that set in the database, 
    and create a new assessment.
    """
    # For now, we return "dummy" data to prove the door works
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "question_set_id": payload.question_set_id,
        "competency_ids": ["mock-competency-1", "mock-competency-2"],
        "time_limit_min": payload.time_limit_min
    }

@router.get("/assessments")
async def list_assessments():
    """
    SCAFFOLD: This will eventually ask the database for all assessments
    and return them to the admin dashboard.
    """
    # For now, return an empty list
    return []


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Return the final_reports row + per-competency results for the admin review page. TODO."""
    raise NotImplementedError