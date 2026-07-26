"""
Question Bank Import API.

Workflow

POST /admin/import

        JSON
          │
          ▼
Pydantic validation (schemas.py)
          │
          ▼
Business validation (validators.py)
          │
          ├── errors -> return to frontend
          │
          ▼
Idempotent upserts
          │
          ▼
Import summary

This router performs orchestration only.

No business logic should live here.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from supabase import AsyncClient

from app.db.session import get_supabase

from app.ingestion.schemas import (
    QuestionBankImport,
    ImportSummary,
)

from app.ingestion.validators import (
    validate_import,
)

from app.ingestion.upserts import (
    import_question_bank,
)


router = APIRouter(
    prefix="/admin/import",
    # tags=["Question Bank Import"],
)


# ---------------------------------------------------------
# Validate only
# ---------------------------------------------------------


@router.post(
    "/validate",
    response_model=ImportSummary,
)
async def validate_question_bank(
    payload: QuestionBankImport,
):
    """
    Validate an import payload.

    No database writes occur.
    """

    errors = validate_import(
        payload,
    )

    return ImportSummary(
        success=len(errors) == 0,
        competencies_imported=0,
        questions_imported=0,
        question_set_items_imported=0,
        errors=errors,
    )


# ---------------------------------------------------------
# Import
# ---------------------------------------------------------


@router.post(
    "",
    response_model=ImportSummary,
)
async def import_bank(
    payload: QuestionBankImport,
    db: AsyncClient = Depends(get_supabase),
):
    print("========== IMPORT ROUTE HIT ==========")

    errors = validate_import(payload)

    if errors:
        return ImportSummary(
            success=False,
            competencies_imported=0,
            questions_imported=0,
            question_set_items_imported=0,
            errors=errors,
        )

    try:
        await import_question_bank(db, payload)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {exc}",
        )

    return ImportSummary(
        success=True,
        competencies_imported=len(payload.competencies),
        questions_imported=len(payload.questions),
        question_set_items_imported=len(payload.question_set.items),
        errors=[],
    )
# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------


@router.get("/health")
async def import_health():
    """
    Simple endpoint used by the frontend
    to verify the import service is alive.
    """

    return {
        "status": "ok",
        "service": "question-bank-import",
    }