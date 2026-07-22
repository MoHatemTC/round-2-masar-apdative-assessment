"""
Idempotent Question Bank upserts.

Responsibilities:
- Upsert competencies by code
- Resolve parent_id relationships
- Upsert Question Bank entries by source_ref
- Create/update Question Sets
- Upsert Question Set Items

Uses Supabase Python client.

No FastAPI.
"""

from typing import Dict

from supabase import AsyncClient

from .difficulty_map import DIFFICULTY_MAP
from .schemas import QuestionBankImport


# ---------------------------------------------------------
# Competencies
# ---------------------------------------------------------

async def upsert_competencies(
    db: AsyncClient,
    payload: QuestionBankImport,
) -> Dict[str, str]:
    """
    Upsert competencies using the unique `code` column.

    Root competencies become kind="track".
    Child competencies become kind="sub".

    Parent relationships are resolved afterwards once
    all IDs exist.
    """

    code_to_id: Dict[str, str] = {}

    # -----------------------------------------------------
    # Create / Update competencies
    # -----------------------------------------------------

    for competency in payload.competencies:

        row = {
            "kind": (
                "track"
                if competency.parent_code is None
                else "sub"
            ),
            "code": competency.code,
            "name": competency.name,
            "domain": None,
            "parent_id": None,
            "sort_order": 0,
            "is_active": True,
        }

        result = await (
            db.table("competencies")
            .upsert(
                row,
                on_conflict="code",
            )
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to upsert competency '{competency.code}'"
            )

        code_to_id[competency.code] = result.data[0]["id"]

    # -----------------------------------------------------
    # Resolve parent relationships
    # -----------------------------------------------------

    for competency in payload.competencies:

        if competency.parent_code is None:
            continue

        parent_id = code_to_id.get(
            competency.parent_code
        )

        if parent_id is None:
            raise Exception(
                f"Parent competency '{competency.parent_code}' not found."
            )

        await (
            db.table("competencies")
            .update(
                {
                    "parent_id": parent_id,
                }
            )
            .eq(
                "code",
                competency.code,
            )
            .execute()
        )

    return code_to_id


# ---------------------------------------------------------
# Question Bank
# ---------------------------------------------------------

async def upsert_questions(
    db: AsyncClient,
    payload: QuestionBankImport,
    competency_ids: Dict[str, str],
):
    """
    Upsert questions into question_bank using source_ref.

    Schema mapping:

    QuestionImport.text            -> body
    QuestionImport.expected_answer -> rubric
    QuestionImport.metadata        -> payload
    """

    for question in payload.questions:

        row = {
            "source_ref": question.source_ref,
            "competency_id": competency_ids[
                question.competency
            ],
            "tool_type": question.tool_type,
            "difficulty": DIFFICULTY_MAP[
                question.difficulty
            ],
            "body": question.text,
            "rubric": question.expected_answer,
            "payload": question.metadata,
            "tags": [],
            "is_active": True,
        }

        result = await (
            db.table("question_bank")
            .upsert(
                row,
                on_conflict="source_ref",
            )
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to upsert question '{question.source_ref}'"
            )

# ---------------------------------------------------------
# Question Set
# ---------------------------------------------------------

async def upsert_question_set(
    db: AsyncClient,
    payload: QuestionBankImport,
) -> str:
    """
    Create or update a question set.

    NOTE:
    question_sets.name is NOT unique in the current schema,
    so we cannot use native upsert(on_conflict="name").

    Instead:
        select -> update -> insert
    """

    existing = await (
        db.table("question_sets")
        .select("*")
        .eq(
            "name",
            payload.question_set.name,
        )
        .execute()
    )

    row = {
        "name": payload.question_set.name,
        "description": payload.question_set.description,
    }

    if existing.data:

        question_set_id = existing.data[0]["id"]

        await (
            db.table("question_sets")
            .update(row)
            .eq(
                "id",
                question_set_id,
            )
            .execute()
        )

    else:

        result = await (
            db.table("question_sets")
            .insert(row)
            .execute()
        )

        if not result.data:
            raise Exception(
                "Failed to create question set."
            )

        question_set_id = result.data[0]["id"]

    return question_set_id


# ---------------------------------------------------------
# Question Set Items
# ---------------------------------------------------------

async def upsert_question_set_items(
    db: AsyncClient,
    payload: QuestionBankImport,
    question_set_id: str,
):
    """
    Upsert mappings into question_set_items.

    Composite primary key:
        (set_id, question_id)
    """

    for item in payload.question_set.items:

        question = await (
            db.table("question_bank")
            .select("id")
            .eq(
                "source_ref",
                item.source_ref,
            )
            .execute()
        )

        if not question.data:
            continue

        question_id = question.data[0]["id"]

        row = {
            "set_id": question_set_id,
            "question_id": question_id,
            "sort_order": item.order,
        }

        result = await (
            db.table("question_set_items")
            .upsert(
                row,
                on_conflict="set_id,question_id",
            )
            .execute()
        )

        if not result.data:
            raise Exception(
                f"Failed to map question '{item.source_ref}' into question set."
            )

# ---------------------------------------------------------
# Import Orchestrator
# ---------------------------------------------------------

async def import_question_bank(
    db: AsyncClient,
    payload: QuestionBankImport,
):
    """
    Import a complete Question Bank.

    Order of operations:

        1. Upsert competencies
        2. Upsert question bank entries
        3. Create/update question set
        4. Upsert question set items

    The operation is idempotent:
    importing the same payload multiple times
    will update existing records rather than
    creating duplicates.
    """

    # -----------------------------------------------------
    # Competencies
    # -----------------------------------------------------

    competency_ids = await upsert_competencies(
        db,
        payload,
    )

    # -----------------------------------------------------
    # Question Bank
    # -----------------------------------------------------

    await upsert_questions(
        db,
        payload,
        competency_ids,
    )

    # -----------------------------------------------------
    # Question Set
    # -----------------------------------------------------

    question_set_id = await upsert_question_set(
        db,
        payload,
    )

    # -----------------------------------------------------
    # Question Set Items
    # -----------------------------------------------------

    await upsert_question_set_items(
        db,
        payload,
        question_set_id,
    )