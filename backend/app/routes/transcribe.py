# app/routes/transcribe.py
from __future__ import annotations
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.db import get_db
from app.services.llm import call_stt
from app.services.grading import grade_answer
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

MAX_BYTES = 25 * 1024 * 1024
MAX_DURATION_MS = 10 * 60 * 1000

# NOTE: this endpoint relies on a UNIQUE constraint on
# answers(session_id, question_number) to make the "claim" insert below
# race-safe. 
# Without it, two concurrent submits (e.g. a page reload firing a second
# request while the first is still mid-grade) can both pass the "existing"
# check below and both run STT + grading.


# NOTE: on this project's installed postgrest-py version, `.maybe_single().execute()`
# returns None for the WHOLE result (not an object with `.data = None`) when zero rows
# match. `_row()` normalizes that so every call site below can just check the return
# value directly, whichever behavior the client actually has.
def _row(result):
    return result.data if result is not None else None


@router.get("/api/sessions/{session_id}/questions/{question_number}/answer")
async def get_existing_answer(session_id: str, question_number: int):
    db = await get_db()
    existing = await db.table("answers").select("*").eq(
        "session_id", session_id
    ).eq("question_number", question_number).maybe_single().execute()
    existing_row = _row(existing)

    if existing_row:
        return {"exists": True, "answer": existing_row}
    return {"exists": False, "answer": None}


@router.post("/api/sessions/{session_id}/questions/{question_number}/voice-answer")
async def submit_voice_answer(
    session_id: str,
    question_number: int,
    duration_ms: int = Form(...),
    question_id: str = Form(...),
    audio: UploadFile | None = File(None),
    typed_answer: str | None = Form(None),
    skipped: bool = Form(False),
):
    db = await get_db()

    # --- fast-path idempotency check ---
    existing = await db.table("answers").select("*").eq(
        "session_id", session_id
    ).eq("question_number", question_number).maybe_single().execute()
    existing_row = _row(existing)
    if existing_row:
        return {"status": "already_submitted", "answer": existing_row}

    if skipped:
        question_resp = await db.table("question_bank").select("body,competency_id").eq(
            "id", question_id
        ).maybe_single().execute()
        question = _row(question_resp) or {}
        try:
            claimed = await db.table("answers").insert({
                "session_id": session_id,
                "question_number": question_number,
                "question_id": question_id,
                "question_body": question.get("body"),
                "competency_id": question.get("competency_id"),
                "tool_type": "voice",
                "skipped": True,
                "answer_text": None,
                "audio_url": None,
                "transcript": None,
                "score": 0.0,
                "rationale": "Skipped by the candidate.",
                "flagged": False,
            }).execute()
            return {"status": "submitted", "answer": claimed.data[0]}
        
        except Exception as e:
            logger.warning(f"skip claim_row insert failed: {type(e).__name__}: {e}")
            existing = await db.table("answers").select("*").eq(
                "session_id", session_id
            ).eq("question_number", question_number).maybe_single().execute()
            return {"status": "already_submitted", "answer": _row(existing)}

    question_resp = await db.table("question_bank").select("*").eq(
        "id", question_id
    ).maybe_single().execute()
    question = _row(question_resp) or {}
    logger.info(f"Received question_id: {question_id}")
    logger.info(f"Question lookup result: {question}")
    
    base_row = {
        "session_id": session_id,
        "question_number": question_number,
        "question_id": question.get("id"),
        "question_body": question.get("body"),
        "competency_id": question.get("competency_id"),
        "tool_type": "voice",
        "skipped": False,
    }

    async def claim_row(extra: dict) -> dict | None:
        try:
            claimed = await db.table("answers").insert({**base_row, **extra}).execute()
            return claimed.data[0]
        except Exception as e:
            msg = str(e).lower()
            if "duplicate key" in msg or "answers_session_question" in msg or "unique constraint" in msg:
              return None  # genuinely lost the race — expected, not an error
            logger.error(f"claim_row insert failed: {type(e).__name__}: {e}")
            raise

    async def finalize(row_id: str, update: dict) -> dict:
        updated = await db.table("answers").update(update).eq("id", row_id).execute()
        return updated.data[0] if updated.data else update

    # --- mic denied / no audio → typed fallback, flagged, or graceful skip ---
    if audio is None:
        if not typed_answer or not typed_answer.strip():
            # Nothing usable was submitted (e.g. no mic AND nothing typed).
            # This must still complete the turn rather than block the session.
            claimed = await claim_row({
                "answer_text": None,
                "audio_url": None,
                "transcript": None,
                "score": 0.0,
                "rationale": "No audio and no typed answer provided — treated as skipped.",
                "flagged": False,
                "skipped": True,
            })
            if claimed is None:
                existing = await db.table("answers").select("*").eq(
                    "session_id", session_id
                ).eq("question_number", question_number).maybe_single().execute()
                return {"status": "already_submitted", "answer": _row(existing)}
            return {"status": "submitted", "answer": claimed}

        claimed = await claim_row({
            "answer_text": typed_answer,
            "audio_url": None,
            "transcript": None,
            "score": None,
            "rationale": None,
            "flagged": True,
        })
        if claimed is None:
            existing = await db.table("answers").select("*").eq(
                "session_id", session_id
            ).eq("question_number", question_number).maybe_single().execute()
            return {"status": "already_submitted", "answer": _row(existing)}

        grade = await grade_answer(
            tool_type="voice",
            question=question,
            tool_result={"answer_text": typed_answer},
            session_id=session_id,
        )
        answer = await finalize(claimed["id"], {
            "score": grade["score"],
            "rationale": f"[No audio — typed fallback used] {grade['rationale']}",
            "flagged": True,
        })
        return {"status": "submitted", "answer": answer}

    # --- validate BEFORE claiming, so a rejected upload can be retried
    #     (e.g. re-record after an oversized file) without burning the slot ---
    if duration_ms > MAX_DURATION_MS:
        raise HTTPException(status_code=413, detail="Recording exceeds max allowed duration.")

    size = 0
    chunks = []
    while chunk := await audio.read(1024 * 1024):
     size += len(chunk)
     if size > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Recording exceeds max allowed size.")
     chunks.append(chunk)
    raw = b"".join(chunks)
    if len(raw) == 0:
     raise HTTPException(status_code=400, detail="Empty audio file.")

    # --- claim the slot now, right before the expensive/racy STT call ---
    claimed = await claim_row({
        "answer_text": None,
        "audio_url": None,
        "transcript": None,
        "score": None,
        "rationale": None,
        "flagged": False,
    })
    if claimed is None:
        existing = await db.table("answers").select("*").eq(
            "session_id", session_id
        ).eq("question_number", question_number).maybe_single().execute()
        return {"status": "already_submitted", "answer": _row(existing)}

    filename = f"{session_id}/{question_number}-{uuid.uuid4()}.webm"
    try:
        bucket = db.storage.from_("candidate-audio")
        await bucket.upload(filename, raw, {"content-type": "audio/webm"})
        stt_result = await call_stt(raw, filename, session_id=session_id)
    except Exception as e:
        logger.error(f"upload/STT failed: {type(e).__name__}: {e}")
        answer = await finalize(claimed["id"], {
            "audio_url": filename,
            "transcript": None,
            "score": None,
            "rationale": "Upload or transcription failed — flagged for manual review.",
            "flagged": True,
        })
        return {"status": "submitted", "answer": answer}

    if not stt_result["success"]:
        answer = await finalize(claimed["id"], {
            "audio_url": filename,
            "transcript": None,
            "score": None,
            "rationale": "Speech-to-text failed — flagged for manual review.",
            "flagged": True,
        })
        return {"status": "submitted", "answer": answer}

    transcript = stt_result["text"]
    grade = await grade_answer(
        tool_type="voice",
        question=question,
        tool_result={"transcript": transcript},
        session_id=session_id,
    )
    answer = await finalize(claimed["id"], {
        "audio_url": filename,
        "transcript": transcript,
        "score": grade["score"],
        "rationale": grade["rationale"],
        "flagged": grade["flagged"],
    })
    return {"status": "submitted", "answer": answer}
