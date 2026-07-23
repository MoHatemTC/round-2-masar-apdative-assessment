"""
Pydantic schemas for Question Bank import.

Pure models only.

No database.
No FastAPI.
No ORM.
"""

from typing import List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------
# Competencies
# ---------------------------------------------------------

class CompetencyImport(BaseModel):
    """
    Competency definition.

    Parent is optional.
    Root competencies should omit parent_code.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)

    parent_code: Optional[str] = None


# ---------------------------------------------------------
# Questions
# ---------------------------------------------------------

class QuestionImport(BaseModel):
    """
    Single imported question.
    """

    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(..., min_length=1)

    competency: str = Field(
        ...,
        description="Competency code"
    )

    text: str = Field(..., min_length=1)

    difficulty: Literal[
        "easy",
        "medium",
        "hard",
    ]

    tool_type: str = Field(..., min_length=1)

    expected_answer: Optional[str] = None

    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------
# Question Set Items
# ---------------------------------------------------------

class QuestionSetItemImport(BaseModel):
    """
    One question inside a question set.
    """

    model_config = ConfigDict(extra="forbid")

    source_ref: str

    order: int = Field(..., ge=1)


# ---------------------------------------------------------
# Question Set
# ---------------------------------------------------------

class QuestionSetImport(BaseModel):
    """
    Named collection of questions.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)

    description: Optional[str] = None

    items: List[QuestionSetItemImport]


# ---------------------------------------------------------
# Root Import Payload
# ---------------------------------------------------------

class QuestionBankImport(BaseModel):
    """
    Root payload accepted by POST /admin/import
    """

    model_config = ConfigDict(extra="forbid")

    competencies: List[CompetencyImport]

    questions: List[QuestionImport]

    question_set: QuestionSetImport


# ---------------------------------------------------------
# Validation Error
# ---------------------------------------------------------

class ValidationErrorItem(BaseModel):
    """
    Structured validation error.

    Returned to the frontend without performing writes.
    """

    row: int

    field: str

    message: str


# ---------------------------------------------------------
# Import Result
# ---------------------------------------------------------

class ImportSummary(BaseModel):
    """
    Response returned after import.
    """

    success: bool

    competencies_imported: int = 0

    questions_imported: int = 0

    question_set_items_imported: int = 0

    errors: List[ValidationErrorItem] = Field(
        default_factory=list
    )