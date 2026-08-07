"""
Admin API:
- Import question bank
- Create question-set driven assessments
- List assessments
- Review reports
"""

from __future__ import annotations
import math
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from pydantic import BaseModel
from uuid import UUID
import os
import uuid
from fastapi import BackgroundTasks
from pydantic import EmailStr
from app.services.email import send_invitation_background

from app.db import get_db
from supabase import AsyncClient

from app.ingestion.schemas import (
    QuestionBankImport,
)

from app.ingestion.normalize import (
    is_flat_bank,
    normalize_flat_bank,
)

from pydantic import ValidationError

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
# Invitation Schemas
# =========================================================

class InvitationCreate(BaseModel):
    assessment_id: UUID
    candidate_email: EmailStr  # Automatically validates email format (returns 422 if invalid)

class InvitationResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    candidate_email: str
    token: str
    status: str


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
    raw: list | dict = Body(...),
):

    """
    Import Question Bank.

    Accepts BOTH upload formats:
      * the PRD flat format — a bare JSON array of items (data/sample_question_bank.json),
        or {"items": [...], "set_name": "..."} as the admin UI sends it — which is
        normalized server-side, and
      * the structured {competencies, questions, question_set} payload.

    Flow:

    JSON
      |
      v
    normalize (flat -> structured, when needed)
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

    if is_flat_bank(raw):
        raw = normalize_flat_bank(raw)

    try:
        payload = QuestionBankImport.model_validate(raw)
    except ValidationError as exc:
        return {
            "success": False,
            "competencies_imported": 0,
            "questions_imported": 0,
            "question_set_items_imported": 0,
            "errors": [
                {
                    # loc like ('questions', 3, 'text') -> row 3; -1 when not per-row
                    "row": e["loc"][1] if len(e["loc"]) > 1 and isinstance(e["loc"][1], int) else -1,
                    "field": ".".join(str(p) for p in e["loc"]),
                    "message": e["msg"],
                }
                for e in exc.errors()
            ],
        }


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



@router.get("/competency-tracks")
async def list_competency_tracks(db: AsyncClient = Depends(get_db)):
    result = await db.table("competencies").select("id, name, code").order("name").execute()
    return result.data or []

# =========================================================
# Question Set Competencies
# =========================================================


@router.get("/question-sets/{set_id}/competencies")
async def set_competencies(
    set_id: str,
    db: AsyncClient = Depends(get_db),
):
    """
    Return the UUIDs of the competencies MEASURED by a question set — that is, the
    competencies its questions are actually filed under (the sub-competencies).

    These ids drive three things downstream, all of which must agree: the self-ratings
    collected at intake, the per-competency loop in the adaptive engine, and the rows in
    session_competency_results. The engine selects questions with
    `question_bank.competency_id == <one of these ids>`, so returning the PARENT track ids
    here made every lookup miss (questions hang off the subs), the bank look exhausted on
    question 1, and every candidate got LLM-generated fallback questions instead of the bank.
    """

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

    measured_ids = list(
        {
            q["competency_id"]
            for q in questions_response.data
            if q.get("competency_id")
        }
    )

    return measured_ids

# =========================================================
# Create Assessment
# =========================================================


@router.post(
    "/assessments",
    response_model=AssessmentResponse,
)
async def create_assessment(
    payload: AssessmentCreate,
    db: AsyncClient = Depends(get_db),
):



    competency_ids = await set_competencies(
        str(payload.question_set_id),
        db,
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

        # Defaults to false at the DB level; without this every new
        # assessment's candidate link 404s at candidate_intake.py's
        # is_published check until someone flips it manually.
        "is_published":
            True,

    }

    # Insert the derived assessment into the database
    insert_response = await db.table("assessments").insert(new_assessment).execute()

    if not insert_response.data:
        raise HTTPException(status_code=500, detail="Failed to create assessment")

    return insert_response.data[0]

@router.get("/assessments")
async def list_assessments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncClient = Depends(get_db),
):
    """
    Queries the database for all created assessments
    and returns them to the admin dashboard.
    """
    count_response = await db.table("assessments").select("*", count="exact").execute()
    total_items = count_response.count or 0
    total_pages = max(1, math.ceil(total_items / limit))

    offset = (page - 1) * limit
    response = await db.table("assessments").select("*").range(offset, offset + limit - 1).execute()

    return {
        "data": response.data,
        "meta": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalItems": total_items,
        },
    }


@router.get("/sessions")
async def list_sessions(
    assessment_id: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncClient = Depends(get_db),
):
    """Every candidate session, newest first, for the admin sessions dashboard.

    Each row carries the score/band from `final_reports` when the session finished, so the
    list can show results without the client fetching a report per row. Sessions that are
    still running simply have those fields null. Optional `assessment_id` narrows the list
    to one assessment.
    """
    count_query = db.table("sessions").select("*", count="exact")
    if assessment_id:
        count_query = count_query.eq("assessment_id", assessment_id)
    count_response = await count_query.execute()
    total_items = count_response.count or 0
    total_pages = max(1, math.ceil(total_items / limit))

    offset = (page - 1) * limit
    query = db.table("sessions").select(
        "id, assessment_id, candidate_name, candidate_email, status, created_at, completed_at"
    )
    if assessment_id:
        query = query.eq("assessment_id", assessment_id)

    sessions_response = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    sessions = sessions_response.data or []

    if not sessions:
        return {
            "data": [],
            "meta": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalItems": total_items,
            },
        }

    # One extra round trip for all reports beats one per session row.
    reports_response = (
        await db.table("final_reports")
        .select("session_id, overall_pct, level_label, has_low_confidence")
        .in_("session_id", [s["id"] for s in sessions])
        .execute()
    )
    reports = {r["session_id"]: r for r in (reports_response.data or [])}

    data = [
        {
            **session,
            # The list links to /admin/sessions/{id}; session_id mirrors id so the page can
            # use either without a special case.
            "session_id": session["id"],
            "overall_pct": reports.get(session["id"], {}).get("overall_pct"),
            "level_label": reports.get(session["id"], {}).get("level_label"),
            "has_low_confidence": reports.get(session["id"], {}).get("has_low_confidence"),
        }
        for session in sessions
    ]

    return {
        "data": data,
        "meta": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalItems": total_items,
        },
    }


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str, db: AsyncClient = Depends(get_db)):
    session_response = await db.table("sessions").select("status").eq("id", session_id).execute()

    if not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session_response.data[0]["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="Session is in progress or not taken. Report is not available yet."
        )

    report_response = await db.table("final_reports").select("*").eq("session_id", session_id).execute()

    if not report_response.data:
        raise HTTPException(status_code=404, detail="Final report missing for completed session.")

    report = report_response.data[0]

    competency_results_response = (
        await db.table("session_competency_results")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )

    answers_response = (
        await db.table("answers")
        .select("question_number, question_body, tool_type, score, rationale, answer_text, flagged")
        .eq("session_id", session_id)
        .order("question_number")
        .execute()
    )

    return {
        "session_id": report.get("session_id"),
        "overall_pct": report.get("overall_pct"),
        "level_label": report.get("level_label"),
        "has_low_confidence": report.get("has_low_confidence", False),
        "competency_results": competency_results_response.data or [],
        "answers": answers_response.data or [],
    }

@router.get("/assessments/{assessment_id}/invitations")
async def list_invitations(
    assessment_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncClient = Depends(get_db),
):
    """Lists invitations and cross-references session status for each candidate."""
    count_response = await db.table("invitations").select("*", count="exact").eq("assessment_id", str(assessment_id)).execute()
    total_items = count_response.count or 0
    total_pages = max(1, math.ceil(total_items / limit))

    offset = (page - 1) * limit
    invitations_response = await db.table("invitations").select("*").eq("assessment_id", str(assessment_id)).range(offset, offset + limit - 1).execute()
    invitations = invitations_response.data or []

    # Fetch status AND id to pass to the frontend
    sessions_response = await db.table("sessions").select("id, candidate_email, status").eq("assessment_id", str(assessment_id)).execute()

    # Map by email to quickly grab status and session_id
    sessions_map = {s["candidate_email"]: {"status": s["status"], "session_id": s["id"]} for s in sessions_response.data} if sessions_response.data else {}

    results = []
    for inv in invitations:
        email = inv.get("candidate_email")
        session_data = sessions_map.get(email, {})
        session_status = session_data.get("status")
        session_id = session_data.get("session_id") # Grab the ID!

        if session_status == "completed":
            status_label = "taken"
        elif session_status:
            status_label = "in_progress"
        else:
            status_label = "not_taken"

        results.append({
            "id": inv.get("id"),
            "session_id": session_id, # Frontend uses this for the drill-down link
            "candidate_email": email,
            "status": status_label,
            "invited_at": inv.get("created_at")
        })

    return {
        "data": results,
        "meta": {
            "currentPage": page,
            "totalPages": total_pages,
            "totalItems": total_items,
        },
    }

# =========================================================
# Invitations
# =========================================================

@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    payload: InvitationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncClient = Depends(get_db)
):
    """
    Creates an invitation for a candidate to take an assessment.
    Enforces deduplication: if an invite already exists, the same token is reused.
    Dispatches the email asynchronously via BackgroundTasks.
    """
    assessment_id_str = str(payload.assessment_id)
    email = payload.candidate_email

    # 1. Deduplication: Check if invitation already exists
    existing_response = (
        await db.table("invitations")
        .select("*")
        .eq("assessment_id", assessment_id_str)
        .eq("candidate_email", email)
        .execute()
    )

    if existing_response.data:
        # Reuse existing token to avoid duplicate rows
        invitation_data = existing_response.data[0]
        token = invitation_data["token"]
        status = "re-invited"
    else:
        # Generate new token and insert into database
        token = str(uuid.uuid4())
        new_invitation = {
            "assessment_id": assessment_id_str,
            "candidate_email": email,
            "token": token
        }

        insert_response = await db.table("invitations").insert(new_invitation).execute()
        if not insert_response.data:
            raise HTTPException(status_code=500, detail="Failed to create invitation in database.")

        invitation_data = insert_response.data[0]
        status = "invited"

    # 2. Queue email dispatch in the background (Non-blocking)
    # Falls back to localhost if FRONTEND_URL is not set in .env
    base_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    background_tasks.add_task(
        send_invitation_background,
        db,
        email,
        token,
        base_url
    )

    return {
        "id": invitation_data["id"],
        "assessment_id": invitation_data["assessment_id"],
        "candidate_email": email,
        "token": token,
        "status": status
    }