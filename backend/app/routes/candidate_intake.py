"""Candidate intake API — start a session and capture self-ratings before the adaptive loop runs.

Owns: `POST /session/start`, `POST /session/{session_id}/intake`.
Does not touch the adaptive loop, question selection, personalization, or grading — those are
other lanes' seams (`app/agent/adaptive_loop.py`, `app/services/question_bank.py`,
`app/services/grading.py`). This module only ever writes to `sessions` and `session_self_ratings`.
"""
from __future__ import annotations

import io
import os
import uuid as uuid_lib
from datetime import datetime, timezone

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from pypdf import PdfReader

from app.db import get_db
from app.services.prior import compute_priors

router = APIRouter(tags=["candidate-intake"])

MAX_CV_BYTES = 5 * 1024 * 1024  # 5 MB — generous for a resume, small enough to reject junk fast
SUPPORTED_CV_EXTENSIONS = {".txt", ".pdf"}


def _is_valid_uuid(value) -> bool:
    """Whether `value` is *syntactically* a UUID — doesn't check it exists anywhere."""
    try:
        uuid_lib.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _require_str(value, field: str) -> str:
    """422 if `value` isn't a non-empty string, otherwise return it."""
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail=f"'{field}' is required.")
    return value


def _extract_cv_text(filename: str, content: bytes) -> str:
    """Best-effort text extraction from an uploaded CV file. Supports .txt and .pdf (checked
    against SUPPORTED_CV_EXTENSIONS at the call site). Raises a 422 for anything unreadable —
    never silently returns garbage for the LLM to reason about later."""
    ext = os.path.splitext(filename or "")[1].lower()

    if ext == ".txt":
        return content.decode("utf-8", errors="ignore").strip()

    if ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # noqa: BLE001 - any malformed/corrupt PDF must 422, not 500
            raise HTTPException(status_code=422, detail=f"Could not read PDF: {exc}") from exc
        return "\n".join(pages).strip()

    raise HTTPException(
        status_code=422,
        detail=f"Unsupported CV file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_CV_EXTENSIONS))}.",
    )


def _validate_self_ratings(raw) -> dict[str, int]:
    """Coerce + validate the incoming self_ratings payload.

    Expects `{competency_id: 1-5, ...}`. Returns a cleaned `{competency_id: int}` dict or raises a
    422 listing every row that failed, so the client can fix all of them at once.
    """
    if not isinstance(raw, dict) or not raw:
        raise HTTPException(
            status_code=422,
            detail="'self_ratings' must be a non-empty object keyed by competency_id.",
        )

    cleaned: dict[str, int] = {}
    errors: list[str] = []
    for competency_id, rating in raw.items():
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            errors.append(f"self_ratings['{competency_id}'] must be an integer 1-5, got {rating!r}.")
            continue
        if not (1 <= rating_int <= 5):
            errors.append(f"self_ratings['{competency_id}'] must be between 1 and 5, got {rating_int}.")
            continue
        cleaned[competency_id] = rating_int

    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return cleaned


@router.post("/session/start")
async def start_session(body: dict = Body(...)):
    """Create a session for a candidate taking an assessment.

    Body: `{assessment_id: str, candidate_name?: str, candidate_email?: str, cv_json?: dict}`.

    The session is created in status `identity` (pre-intake). Self-ratings aren't collected here —
    call `POST /session/{session_id}/intake` next. Returns `{"session_id": str}`.
    """
    assessment_id = _require_str(body.get("assessment_id"), "assessment_id")

    db = await get_db()

    # Fail fast on a bad assessment_id rather than creating a session that can never be completed.
    found = await db.table("assessments").select("id").eq("id", assessment_id).execute()
    if not found.data:
        raise HTTPException(status_code=404, detail=f"assessment '{assessment_id}' not found.")

    row = {
        "assessment_id": assessment_id,
        "candidate_name": body.get("candidate_name"),
        "candidate_email": body.get("candidate_email"),
        "cv_json": body.get("cv_json"),
        "intake_answers": {},
        "status": "identity",
    }
    result = await db.table("sessions").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not create session.")
    return {"session_id": result.data[0]["id"]}


@router.post("/session/{session_id}/intake")
async def submit_intake(session_id: str, body: dict = Body(...)):
    """Persist the candidate's 1-5 self-ratings (and CV, if not already sent at /start).

    Body: `{self_ratings: {competency_id: 1-5, ...}, cv_json?: dict}`.

    Self-ratings are validated, written to `sessions.intake_answers` (the field the adaptive
    loop's `init_session` reads at loop start) and mirrored one row per competency into
    `session_self_ratings` for admin review / auditing. The starting prior per competency is
    computed here for confirmation in the response; the adaptive loop independently computes the
    same value (via `app.services.prior.compute_priors`) when it actually seeds the Bayesian
    posterior, so the two never disagree.
    """
    db = await get_db()

    session_resp = await db.table("sessions").select("*").eq("id", session_id).execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found.")
    session = session_resp.data[0]

    self_ratings = _validate_self_ratings(body.get("self_ratings"))

    # Competency ids must (a) look like a UUID and (b) actually exist — checked here, before any
    # writes happen, so a bad id can never leave `sessions` and `session_self_ratings` half-written
    # relative to each other (session_self_ratings.competency_id is a foreign key: Postgres would
    # reject a nonexistent one, but only *after* we'd already updated `sessions`).
    malformed = [c for c in self_ratings if not _is_valid_uuid(c)]
    if malformed:
        raise HTTPException(
            status_code=422,
            detail=[f"'{c}' is not a valid competency id (must be a UUID)." for c in malformed],
        )

    found = await db.table("competencies").select("id").in_("id", list(self_ratings.keys())).execute()
    existing_ids = {row["id"] for row in found.data}
    unknown = [c for c in self_ratings if c not in existing_ids]
    if unknown:
        raise HTTPException(status_code=404, detail=f"unknown competency id(s): {unknown}")

    # cv_json may have been sent at /session/start already; let /intake override it if given again.
    cv_json = body.get("cv_json", session.get("cv_json"))

    # No CV-estimate service is available at intake time (that's an LLM call the adaptive loop
    # makes at init), so priors here only ever land on the self-rating / default-3 branches —
    # exactly this task's scope. The signature still accepts cv_estimates so this stays correct
    # once that service exists upstream.
    priors = compute_priors(self_ratings, cv_estimates=None)

    submitted_at = datetime.now(timezone.utc).isoformat()

    await db.table("sessions").update({
        "intake_answers": self_ratings,
        "cv_json": cv_json,
        "status": "in_progress",
        "intake_submitted_at": submitted_at,
    }).eq("id", session_id).execute()

    for competency_id, rating in self_ratings.items():
        await db.table("session_self_ratings").upsert({
            "session_id": session_id,
            "competency_id": competency_id,
            "self_rating": rating,
        }).execute()

    return {"session_id": session_id, "self_ratings": self_ratings, "priors": priors}


@router.get("/assessments/by-token/{share_token}")
async def get_assessment_by_token(share_token: str):
    """Candidate-facing, read-only: resolve a share link's token into what the entry flow needs —
    the assessment id/title and the competencies to self-rate. The token itself is the credential
    (same idea as any unauthenticated share link), so this deliberately requires no auth. This is
    separate from admin.py's `/assessments` CRUD routes, which are the admin-facing management
    surface for the same table.
    """
    db = await get_db()

    found = await db.table("assessments").select("*").eq("share_token", share_token).execute()
    if not found.data:
        raise HTTPException(status_code=404, detail="This assessment link is invalid or has expired.")
    assessment = found.data[0]

    if not assessment.get("is_published"):
        raise HTTPException(status_code=404, detail="This assessment is not currently open.")

    competency_ids = assessment.get("competency_ids") or []
    competencies = []
    if competency_ids:
        comp_resp = await db.table("competencies").select("id,name,code").in_("id", competency_ids).execute()
        competencies = [
            {"id": c["id"], "name": c.get("name") or c.get("code")} for c in comp_resp.data
        ]

    return {
        "assessment_id": assessment["id"],
        "title": assessment["title"],
        "competencies": competencies,
    }


@router.post("/session/{session_id}/cv")
async def upload_cv(session_id: str, file: UploadFile = File(...)):
    """Accept a candidate's CV file, extract its text, and store it in `sessions.cv_json`.

    Supported formats: .txt, .pdf (max 5MB). Deliberately does NOT run CV competency estimation
    here — that's a separate, LLM-backed step (`question_bank.cv_estimate_levels`) that the
    adaptive loop calls once, at `init_session`. Doing the estimate here too would mean paying
    for (and waiting on) an LLM call twice, or getting two different estimates if the candidate
    re-uploads. This endpoint's job is just: get the text safely into `sessions.cv_json` and give
    the frontend something to show as upload feedback.

    Returns `{session_id, filename, characters_extracted, message}` — enough for the intake
    screen to show "CV uploaded (1,842 characters read)" without waiting on an LLM round-trip.
    """
    db = await get_db()

    session_resp = await db.table("sessions").select("id").eq("id", session_id).execute()
    if not session_resp.data:
        raise HTTPException(status_code=404, detail=f"session '{session_id}' not found.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded CV file is empty.")
    if len(content) > MAX_CV_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"CV file too large ({len(content)} bytes; max {MAX_CV_BYTES} bytes).",
        )

    raw_text = _extract_cv_text(file.filename or "", content)
    if not raw_text:
        raise HTTPException(status_code=422, detail="Could not extract any text from the uploaded CV.")

    cv_json = {
        "filename": file.filename,
        "raw_text": raw_text,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.table("sessions").update({"cv_json": cv_json}).eq("id", session_id).execute()

    return {
        "session_id": session_id,
        "filename": file.filename,
        "characters_extracted": len(raw_text),
        "message": "CV received.",
    }