"""
Database model definitions.

These are shared table/column definitions used by the
Supabase data-access layer.

No SQLAlchemy ORM.
No database connection.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


# ==========================================================
# Table names
# ==========================================================

COMPETENCIES = "competencies"
QUESTIONS = "questions"
QUESTION_SETS = "question_sets"
QUESTION_SET_ITEMS = "question_set_items"
LEVEL_HISTORY = "level_history"


# ==========================================================
# Competency
# ==========================================================

@dataclass(slots=True)
class Competency:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    parent_id: Optional[int] = None
    created_at: Optional[datetime] = None


# ==========================================================
# Question
# ==========================================================

@dataclass(slots=True)
class Question:
    id: Optional[int] = None
    source_ref: str = ""
    competency_id: int = 0
    text: str = ""
    difficulty: int = 3
    tool_type: str = ""
    expected_answer: Optional[str] = None
    metadata: Dict[str, Any] | None = None
    created_at: Optional[datetime] = None


# ==========================================================
# Question Set
# ==========================================================

@dataclass(slots=True)
class QuestionSet:
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None


# ==========================================================
# Question Set Item
# ==========================================================

@dataclass(slots=True)
class QuestionSetItem:
    id: Optional[int] = None
    question_set_id: int = 0
    question_id: int = 0
    position: int = 1


# ==========================================================
# Level History
# ==========================================================

@dataclass(slots=True)
class LevelHistory:
    id: Optional[int] = None
    assessment_session_id: str = ""
    question_number: int = 0
    estimated_level: int = 1
    confidence: float = 0.0
    posterior: Dict[int, float] | None = None
    created_at: Optional[datetime] = None