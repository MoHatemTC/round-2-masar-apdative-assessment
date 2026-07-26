"""
Integration tests for idempotent Question Bank imports.

Requires:
- Supabase test database
- Unique constraints:
    competencies(code)
    questions(source_ref)
    question_sets(name)
"""

import pytest

from app.ingestion.schemas import (
    CompetencyImport,
    QuestionBankImport,
    QuestionImport,
    QuestionSetImport,
    QuestionSetItemImport,
)
from app.ingestion.upserts import import_question_bank


def sample_bank() -> QuestionBankImport:
    """
    Small valid bank used by all tests.
    """

    return QuestionBankImport(
        competencies=[
            CompetencyImport(
                code="PYTHON",
                name="Python",
            ),
            CompetencyImport(
                code="FASTAPI",
                name="FastAPI",
                parent_code="PYTHON",
            ),
        ],
        questions=[
            QuestionImport(
                source_ref="Q001",
                competency="PYTHON",
                text="Explain decorators.",
                difficulty="medium",
                tool_type="text",
            ),
            QuestionImport(
                source_ref="Q002",
                competency="FASTAPI",
                text="Explain dependency injection.",
                difficulty="hard",
                tool_type="coding",
            ),
        ],
        question_set=QuestionSetImport(
            name="Backend Assessment",
            description="Sample bank",
            items=[
                QuestionSetItemImport(
                    source_ref="Q001",
                    order=1,
                ),
                QuestionSetItemImport(
                    source_ref="Q002",
                    order=2,
                ),
            ],
        ),
    )


@pytest.mark.asyncio
async def test_import_twice_creates_no_duplicates(
    supabase_client,
):
    """
    Importing the exact same payload twice
    should never create duplicate rows.
    """

    payload = sample_bank()

    await import_question_bank(
        supabase_client,
        payload,
    )

    await import_question_bank(
        supabase_client,
        payload,
    )

    competencies = (
        await supabase_client
        .table("competencies")
        .select("*")
        .execute()
    ).data

    questions = (
        await supabase_client
        .table("question_bank")
        .select("*")
        .execute()
    ).data

    question_sets = (
        await supabase_client
        .table("question_sets")
        .select("*")
        .execute()
    ).data

    question_set_items = (
        await supabase_client
        .table("question_set_items")
        .select("*")
        .execute()
    ).data

    assert len(competencies) == 2
    assert len(questions) == 2
    assert len(question_sets) == 1
    assert len(question_set_items) == 2


@pytest.mark.asyncio
async def test_import_updates_existing_question(
    supabase_client,
):
    """
    Re-import should update an existing question
    instead of inserting another one.
    """

    payload = sample_bank()

    await import_question_bank(
        supabase_client,
        payload,
    )

    payload.questions[0].text = "Updated question text"

    await import_question_bank(
        supabase_client,
        payload,
    )

    rows = (
        await supabase_client
        .table("question_bank")
        .select("*")
        .eq("source_ref", "Q001")
        .execute()
    ).data

    assert len(rows) == 1
    assert rows[0]["body"] == "Updated question text"


@pytest.mark.asyncio
async def test_question_set_is_updated_not_duplicated(
    supabase_client,
):
    """
    Question Set should be updated by name.
    """

    payload = sample_bank()

    await import_question_bank(
        supabase_client,
        payload,
    )

    payload.question_set.description = "Updated description"

    await import_question_bank(
        supabase_client,
        payload,
    )

    rows = (
        await supabase_client
        .table("question_sets")
        .select("*")
        .eq("name", "Backend Assessment")
        .execute()
    ).data

    assert len(rows) == 1
    assert rows[0]["description"] == "Updated description"