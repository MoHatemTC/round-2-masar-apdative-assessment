"""Candidate intake API — start a session and capture self-ratings before the adaptive loop runs.

Owns: `POST /session/start`, `POST /session/{session_id}/intake`.
Does not touch the adaptive loop, question selection, personalization, or grading — those are
other lanes' seams (`app/agent/adaptive_loop.py`, `app/services/question_bank.py`,
`app/services/grading.py`). This module only ever writes to `sessions` and `session_self_ratings`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException

from app.db import get_db
from app.services.prior import compute_priors

router = APIRouter(tags=["candidate-intake"])


def _require_str(value, field: str) -> str:
    """422 if `value` isn't a non-empty string, otherwise return it."""
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail=f"'{field}' is required.")
    return value


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
