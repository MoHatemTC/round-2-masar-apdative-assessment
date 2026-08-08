"""
AI-Proctoring HTTP surface.

    POST /proctoring/consent    — record accept/decline on the session.
    POST /proctoring/reference  — upload the single reference photo (multipart).
    POST /proctoring/frames     — upload a batch of Q&A frames  (multipart).

Design contract (from the Week-3 task):
  * The turn path (`/chat/turn`) must never be blocked or slowed by proctoring.
    -> This module only writes to the DB + storage; the vision worker runs
       out-of-band (`app/workers/proctoring_worker.py`).
  * Any failure inside proctoring (bad file, dead worker, LLM error) must not
    interrupt or fail the candidate's assessment.
    -> The frame endpoint returns 202 on partial failures with a `skipped`
       breakdown, and the frontend swallows errors on this endpoint anyway.
  * Captured media is PII.
    -> Bucket is private, RLS is on for both tables (see 006_proctoring.sql).

Hardening applied:
  * Per-file size cap + MIME allowlist (image/jpeg only) + magic-byte check.
  * Per-batch file-count cap.
  * Per-session sliding-window rate limit (in-memory; swap for Redis in prod).
  * Session existence + status checks (422 on unknown / completed / bad kinds).
  * batch_id idempotency ledger — retries of the same upload are safe.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque

logger = logging.getLogger(__name__)
from typing import Deque, Dict, List, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from supabase import AsyncClient

from app.db import get_db
from app.schemas.proctoring import ConsentIn, ConsentOut, FrameMeta

router = APIRouter(prefix="/proctoring", tags=["proctoring"])

# ---- Configuration ---------------------------------------------------------

MAX_FILE_BYTES = 400_000            # 400 KB per JPEG (640px @ q=0.85 is well under)
MAX_REFERENCE_BYTES = 800_000       # slightly larger for the reference photo
MAX_BATCH_FILES = 20                # hard cap per batch upload
ALLOWED_MIME = {"image/jpeg", "image/jpg"}
STORAGE_BUCKET = "proctoring"       # private bucket — created via Supabase dashboard

# ---- In-memory rate limiter (per session, sliding window) -----------------
_RATE_WINDOW_S = 60
_RATE_MAX_CALLS = 6                 # 6 batches per minute per session
_recent: Dict[str, Deque[float]] = defaultdict(deque)


def _rate_limited(session_id: str) -> bool:
    now = time.time()
    q = _recent[session_id]
    while q and now - q[0] > _RATE_WINDOW_S:
        q.popleft()
    if len(q) >= _RATE_MAX_CALLS:
        return True
    q.append(now)
    return False


# ---- Helpers ---------------------------------------------------------------

async def _load_session(db: AsyncClient, session_id: str) -> dict:
    """Fetch the session or raise 422 (unknown / completed)."""
    res = await db.table("sessions").select("*").eq("id", session_id).maybe_single().execute()
    if not res or not res.data:
        raise HTTPException(status_code=422, detail="unknown_session")
    sess = res.data
    if sess.get("status") == "completed":
        raise HTTPException(status_code=422, detail="session_not_active")
    return sess


def _validate_jpeg(upload: UploadFile, data: bytes, max_bytes: int) -> None:
    """MIME + size + magic-byte guardrails; raises 422/413 on any violation."""
    if (upload.content_type or "").lower() not in ALLOWED_MIME:
        raise HTTPException(status_code=422, detail="unsupported_media_type")
    if len(data) == 0:
        raise HTTPException(status_code=422, detail="empty_file")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="file_too_large")
    if len(data) < 3 or not (data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF):
        raise HTTPException(status_code=422, detail="not_a_jpeg")


async def _upload_to_storage(
    db: AsyncClient, path: str, data: bytes, *, upsert: bool = False,
) -> str:
    """Upload JPEG bytes to the private 'proctoring' bucket.

    Args:
        upsert: If True, overwrite an existing object at the same path.
                Use True for frames (uniquely named, retries are harmless).
                Use False for the reference photo (must not be silently replaced).
    """
    await db.storage.from_(STORAGE_BUCKET).upload(
        path,
        data,
        file_options={"content-type": "image/jpeg", "upsert": str(upsert).lower()},
    )
    return path


# ============================================================================
# 1. Consent
# ============================================================================

@router.post("/consent", response_model=ConsentOut)
async def record_consent(
    payload: ConsentIn,
    db: AsyncClient = Depends(get_db),
) -> ConsentOut:
    """Persist the candidate's accept/decline decision and the exact timestamp."""
    sess = await _load_session(db, payload.session_id)
    status = "active" if payload.accepted else "proctoring_unavailable"
    await db.table("sessions").update(
        {
            "proctoring_consent": payload.accepted,
            "proctoring_consent_at": payload.timestamp.isoformat(),
            "proctoring_status": status,
        }
    ).eq("id", sess["id"]).execute()
    return ConsentOut(session_id=sess["id"], proctoring_status=status)


# ============================================================================
# 2. Reference photo (blocking pre-assessment step)
# ============================================================================

@router.post("/reference")
async def upload_reference(
    session_id: str = Form(...),
    kind: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncClient = Depends(get_db),
) -> dict:
    """Store the single reference photo.  This is the ONE upload that gates
    assessment start; the frontend must not enable "Begin" until it succeeds.

    Security notes (addressing PR review feedback):
      * The DB row is claimed BEFORE the storage upload so the unique index
        is the guard — if it 409s, no image is written.
      * A retake is allowed only while no frames have been captured yet
        (window-bounding).  Once the Q&A phase starts the reference is locked,
        preventing silent replacement of the face that frames are compared
        against — even without a full auth layer.
      * Storage upsert is False for references (must not silently overwrite).
    """
    if kind != "reference":
        raise HTTPException(status_code=422, detail="bad_kind")

    sess = await _load_session(db, session_id)
    if sess.get("proctoring_consent") is not True:
        raise HTTPException(status_code=422, detail="consent_missing")

    data = await file.read()
    _validate_jpeg(file, data, MAX_REFERENCE_BYTES)

    path = f"{session_id}/reference-{uuid.uuid4()}.jpg"

    # --- Window-bounding: allow retake only before any frames exist ----------
    existing = (
        await db.table("proctoring_captures")
        .select("id")
        .eq("session_id", session_id)
        .eq("kind", "reference")
        .maybe_single()
        .execute()
    )

    if existing and existing.data:
        # A reference already exists.  Only allow replacement while the
        # assessment hasn't started — i.e. before any frames have been captured.
        frames = (
            await db.table("proctoring_captures")
            .select("id", count="exact")
            .eq("session_id", session_id)
            .eq("kind", "frame")
            .execute()
        )
        if frames.count:
            raise HTTPException(
                status_code=409,
                detail="Reference photo is locked once the assessment has started.",
            )
        # Pre-assessment retake: delete the old row so the insert below succeeds.
        await (
            db.table("proctoring_captures")
            .delete()
            .eq("id", existing.data["id"])
            .execute()
        )

    # --- Claim the DB slot FIRST, then write storage -------------------------
    await db.table("proctoring_captures").insert(
        {
            "session_id": session_id,
            "question_number": None,
            "kind": "reference",
            "storage_path": path,
            "analysis_status": "pending",
        }
    ).execute()

    # Only reached if we own the slot — storage upsert is False so a
    # concurrent write would fail rather than silently overwrite.
    await _upload_to_storage(db, path, data, upsert=False)

    return {"ok": True, "storage_path": path}


# ============================================================================
# 3. Frame batch upload
# ============================================================================

@router.post("/frames")
async def upload_frame_batch(
    request: Request,
    db: AsyncClient = Depends(get_db),
) -> JSONResponse:
    """Ingest a batch of Q&A frames without ever blocking the candidate.

    Multipart body:
        session_id : str
        batch_id   : str  (client-generated; idempotency key)
        file_0..file_{n-1}, meta_0..meta_{n-1}
    where meta_i is a JSON-encoded FrameMeta {timestamp, question_number}.

    On partial failure returns 202 with `{accepted, skipped}` so the client can
    move on. On complete success returns 200. On idempotent replay returns 200.
    """
    form = await request.form()
    session_id = form.get("session_id")
    batch_id = form.get("batch_id")

    if not isinstance(session_id, str) or not isinstance(batch_id, str):
        raise HTTPException(status_code=422, detail="missing_ids")

    if _rate_limited(session_id):
        return JSONResponse(status_code=429, content={"error": "rate_limited"})

    sess = await _load_session(db, session_id)
    if sess.get("proctoring_status") != "active":
        raise HTTPException(status_code=422, detail="proctoring_not_active")

    # Idempotency: replayed batch_id -> ack success and stop.
    existing = (
        await db.table("proctoring_batches")
        .select("batch_id")
        .eq("batch_id", batch_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return JSONResponse(status_code=200, content={"ok": True, "idempotent": True})

    accepted: List[Tuple[str, FrameMeta]] = []
    skipped: List[str] = []

    for i in range(MAX_BATCH_FILES):
        f = form.get(f"file_{i}")
        m = form.get(f"meta_{i}")
        if f is None or m is None:
            break
        if not hasattr(f, "read") or not isinstance(m, (str, bytes)):
            skipped.append(f"file_{i}:bad_form_shape")
            continue
        if isinstance(m, bytes):
            m = m.decode()
        try:
            data = await f.read()
            _validate_jpeg(f, data, MAX_FILE_BYTES)
            meta = FrameMeta.model_validate_json(m)
            path = f"{session_id}/frames/{meta.timestamp}.jpg"
            await _upload_to_storage(db, path, data, upsert=True)
            accepted.append((path, meta))
        except HTTPException as e:
            skipped.append(f"file_{i}:{e.detail}")
        except Exception as e:  # noqa: BLE001 — resilience: never crash the endpoint
            skipped.append(f"file_{i}:unexpected:{type(e).__name__}")

    if accepted:
        await db.table("proctoring_captures").insert(
            [
                {
                    "session_id": session_id,
                    "question_number": meta.question_number,
                    "kind": "frame",
                    "storage_path": path,
                    "analysis_status": "pending",
                }
                for (path, meta) in accepted
            ]
        ).execute()

    # Ledger entry guards this batch_id from replay even if 0 frames were accepted.
    await db.table("proctoring_batches").insert(
        {"batch_id": batch_id, "session_id": session_id, "frame_count": len(accepted)}
    ).execute()

    if skipped:
        logger.warning("Frames skipped for session %s: %s", session_id, skipped)

    status_code = 200 if not skipped else 202
    return JSONResponse(
        status_code=status_code,
        content={"ok": True, "accepted": len(accepted), "skipped": skipped},
    )


# ============================================================================
# 4. Storage cleanup  (call when a session is deleted)
# ============================================================================

async def purge_proctoring_storage(db: AsyncClient, session_id: str) -> int:
    """Delete all proctoring images for a session from the storage bucket.

    DB rows are handled by ``ON DELETE CASCADE`` on the FK to sessions, but
    Storage objects have no such mechanism — this function closes that gap.

    Call this **before** deleting the session row so the cascade hasn't yet
    removed the capture rows we need to enumerate paths.

    Returns the number of objects removed.
    """
    import logging as _log

    rows = (
        await db.table("proctoring_captures")
        .select("storage_path")
        .eq("session_id", session_id)
        .execute()
    )
    paths = [r["storage_path"] for r in (rows.data or []) if r.get("storage_path")]
    if not paths:
        return 0

    try:
        await db.storage.from_(STORAGE_BUCKET).remove(paths)
    except Exception as exc:  # noqa: BLE001
        _log.getLogger(__name__).warning(
            "Failed to purge %d storage objects for session %s: %s",
            len(paths), session_id, exc,
        )
        return 0
    return len(paths)
