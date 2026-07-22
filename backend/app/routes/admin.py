"""
Admin API:
- Import question bank
- Create question-set driven assessments
- List assessments
- Review reports
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID


from app.db import get_db

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


@router.get(
    "/question-sets/{set_id}/competencies"
)
async def set_competencies(
    set_id: str,
):

    """
    Return TRACK competencies covered by a question set.

    Flow:

    Question Set
          |
          v
    Question Set Items
          |
          v
    Questions
          |
          v
    Sub Competencies
          |
          v
    Parent Competencies
    """


    db = await get_db()



    # -----------------------------------------------------
    # 1. Get questions from question set
    # -----------------------------------------------------


    items_response = (
        await db.table(
            "question_set_items"
        )
        .select(
            "question_id"
        )
        .eq(
            "question_set_id",
            set_id,
        )
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



    # -----------------------------------------------------
    # 2. Get sub competencies
    # -----------------------------------------------------


    questions_response = (

        await db.table(
            "questions"
        )
        .select(
            "competency_id"
        )
        .in_(
            "id",
            question_ids,
        )
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



    # -----------------------------------------------------
    # 3. Resolve parent tracks
    # -----------------------------------------------------


    sub_response = (

        await db.table(
            "competencies"
        )
        .select(
            "id,parent_id"
        )
        .in_(
            "id",
            sub_ids,
        )
        .execute()

    )



    track_ids = list(
        {
            row["parent_id"]

            for row in sub_response.data

            if row.get("parent_id")
        }
    )



    if not track_ids:

        return []



    # -----------------------------------------------------
    # 4. Return track details
    # -----------------------------------------------------


    tracks_response = (

        await db.table(
            "competencies"
        )
        .select(
            "id,code,name"
        )
        .in_(
            "id",
            track_ids,
        )
        .execute()

    )


    return tracks_response.data




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



    result = (

        await db.table(
            "assessments"
        )
        .insert(
            new_assessment
        )
        .execute()

    )



    if not result.data:

        raise HTTPException(
            status_code=500,
            detail="Failed to create assessment",
        )



    return result.data[0]



# =========================================================
# List Assessments
# =========================================================


@router.get(
    "/assessments",
    response_model=list[AssessmentResponse],
)
async def list_assessments():

    db = await get_db()


    response = (

        await db.table(
            "assessments"
        )
        .select("*")
        .execute()

    )


    return response.data




# =========================================================
# Reports
# =========================================================


@router.get(
    "/sessions/{session_id}/report"
)
async def get_report(
    session_id: str,
):

    """
    TODO:
    - fetch final_reports
    - fetch session_competency_results
    """

    raise NotImplementedError