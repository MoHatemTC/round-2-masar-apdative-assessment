"""Pydantic models for the AI-Proctoring endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- Consent ---------------------------------------------------------------

class ConsentIn(BaseModel):
    session_id: str
    accepted: bool
    timestamp: datetime


class ConsentOut(BaseModel):
    session_id: str
    proctoring_status: Literal["active", "proctoring_unavailable"]


# ---- Frame metadata (sent alongside multipart uploads) ---------------------

class FrameMeta(BaseModel):
    timestamp: int = Field(..., description="ms since epoch on the client")
    question_number: Optional[int] = None


# ---- Analysis verdict (persisted in proctoring_captures.analysis) ----------

class FrameVerdict(BaseModel):
    person_present: bool
    same_person_as_reference: Optional[bool] = None   # None on the reference itself
    multiple_people: bool
    phone_visible: bool
    looking_away: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
