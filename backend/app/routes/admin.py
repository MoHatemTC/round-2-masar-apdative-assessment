"""Admin API: import a bank (→ set), create a set-driven assessment, list/review.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body, HTTPException

# from app.db import get_db
from app.schemas.question_types import validate_question_payload

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.post("/assessments")
async def create_assessment(body: dict = Body(...)):
    """Create a set-driven assessment.
    TODO: if body has question_set_id and no competency_ids → derive them from the set
    (set_competencies). Insert into `assessments`. Return the row."""
    raise NotImplementedError


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    """Return the final_reports row + per-competency results for the admin review page. TODO."""
    raise NotImplementedError
