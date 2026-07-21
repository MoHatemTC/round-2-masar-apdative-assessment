"""
Idempotent Question Bank upserts.

Responsibilities:
- Upsert competencies by code
- Resolve parent_id relationships
- Upsert questions by source_ref
- Create/update Question Set
- Create Question Set Items

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
) -> Dict[str, int]:

    code_to_id: Dict[str, int] = {}

    for competency in payload.competencies:

        existing = await (
            db.table("competencies")
            .select("*")
            .eq(
                "code",
                competency.code,
            )
            .execute()
        )

        row = {
            "code": competency.code,
            "name": competency.name,
            "parent_id": None,
        }

        if existing.data:

            await (
                db.table("competencies")
                .update(row)
                .eq(
                    "code",
                    competency.code,
                )
                .execute()
            )

            code_to_id[competency.code] = (
                existing.data[0]["id"]
            )

        else:

            result = await (
                db.table("competencies")
                .insert(row)
                .execute()
            )

            code_to_id[competency.code] = (
                result.data[0]["id"]
            )


    # update parents

    for competency in payload.competencies:

        if competency.parent_code is None:
            continue

        await (
            db.table("competencies")
            .update(
                {
                    "parent_id": code_to_id[
                        competency.parent_code
                    ]
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
# Questions
# ---------------------------------------------------------

async def upsert_questions(
    db: AsyncClient,
    payload: QuestionBankImport,
    competency_ids: Dict[str, int],
):

    for question in payload.questions:

        row = {
            "source_ref": question.source_ref,
            "text": question.text,
            "tool_type": question.tool_type,
            "difficulty": DIFFICULTY_MAP[
                question.difficulty
            ],
            "competency_id": competency_ids[
                question.competency
            ],
            "expected_answer": question.expected_answer,
            "metadata": question.metadata,
        }


        existing = await (
            db.table("questions")
            .select("*")
            .eq(
                "source_ref",
                question.source_ref,
            )
            .execute()
        )


        if existing.data:

            await (
                db.table("questions")
                .update(row)
                .eq(
                    "source_ref",
                    question.source_ref,
                )
                .execute()
            )

        else:

            await (
                db.table("questions")
                .insert(row)
                .execute()
            )



# ---------------------------------------------------------
# Question Set
# ---------------------------------------------------------

async def upsert_question_set(
    db: AsyncClient,
    payload: QuestionBankImport,
):

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
                "name",
                payload.question_set.name,
            )
            .execute()
        )

    else:

        result = await (
            db.table("question_sets")
            .insert(row)
            .execute()
        )

        question_set_id = result.data[0]["id"]



    # recreate mappings
    # FakeDB does not support delete(),
    # so we avoid it and update/insert only.

    # BUGFIX: this used to unconditionally .insert() every mapping on every import, so
    # re-importing the same set doubled (tripled, ...) the question_set_items rows instead
    # of being a no-op. Check for an existing (question_set_id, question_id) row first — same
    # update-or-insert pattern already used above for competencies/questions/question_sets —
    # and update its position instead of inserting a duplicate. FakeDB still doesn't need
    # delete() for this: existence-check + update/insert is enough to make re-import
    # idempotent.

    for item in payload.question_set.items:

        question = await (
            db.table("questions")
            .select("*")
            .eq(
                "source_ref",
                item.source_ref,
            )
            .execute()
        )


        if not question.data:
            continue


        question_id = question.data[0]["id"]

        existing_item = await (
            db.table("question_set_items")
            .select("*")
            .eq("question_set_id", question_set_id)
            .eq("question_id", question_id)
            .execute()
        )

        if existing_item.data:

            await (
                db.table("question_set_items")
                .update({"position": item.order})
                .eq("question_set_id", question_set_id)
                .eq("question_id", question_id)
                .execute()
            )

        else:

            mapping = {
                "question_set_id": question_set_id,
                "question_id": question_id,
                "position": item.order,
            }

            await (
                db.table("question_set_items")
                .insert(mapping)
                .execute()
            )



# ---------------------------------------------------------
# Import Orchestrator
# ---------------------------------------------------------

async def import_question_bank(
    db: AsyncClient,
    payload: QuestionBankImport,
):

    competency_ids = await upsert_competencies(
        db,
        payload,
    )


    await upsert_questions(
        db,
        payload,
        competency_ids,
    )


    await upsert_question_set(
        db,
        payload,
    )