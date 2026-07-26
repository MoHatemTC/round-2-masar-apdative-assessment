"""
Tests for Question Bank validation.

These tests verify that validators.py correctly detects
invalid import payloads without touching the database.
"""

from app.ingestion.schemas import (
    CompetencyImport,
    QuestionImport,
    QuestionSetImport,
    QuestionSetItemImport,
    QuestionBankImport,
)

from app.ingestion.validators import validate_import


def make_valid_payload():
    """
    Returns a completely valid import payload.
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
            description="Round 2",
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


def test_valid_payload_has_no_errors():
    payload = make_valid_payload()

    errors = validate_import(payload)

    assert errors == []


def test_duplicate_competency_code():
    payload = make_valid_payload()

    payload.competencies.append(
        CompetencyImport(
            code="PYTHON",
            name="Duplicate",
        )
    )

    errors = validate_import(payload)

    assert any(
        e.field == "competencies.code"
        for e in errors
    )


def test_unknown_parent_competency():
    payload = make_valid_payload()

    payload.competencies.append(
        CompetencyImport(
            code="AI",
            name="Artificial Intelligence",
            parent_code="UNKNOWN",
        )
    )

    errors = validate_import(payload)

    assert any(
        e.field == "competencies.parent_code"
        for e in errors
    )


def test_duplicate_question_source_ref():
    payload = make_valid_payload()

    payload.questions.append(
        QuestionImport(
            source_ref="Q001",
            competency="PYTHON",
            text="Duplicate",
            difficulty="easy",
            tool_type="text",
        )
    )

    errors = validate_import(payload)

    assert any(
        e.field == "questions.source_ref"
        for e in errors
    )


def test_unknown_question_competency():
    payload = make_valid_payload()

    payload.questions[0].competency = "UNKNOWN"

    errors = validate_import(payload)

    assert any(
        e.field == "questions.competency"
        for e in errors
    )


def test_invalid_difficulty():
    payload = make_valid_payload()

    payload.questions[0].difficulty = "very_hard"

    errors = validate_import(payload)

    assert any(
        e.field == "questions.difficulty"
        for e in errors
    )


def test_empty_question_text():
    payload = make_valid_payload()

    payload.questions[0].text = ""

    errors = validate_import(payload)

    assert any(
        e.field == "questions.text"
        for e in errors
    )


def test_empty_tool_type():
    payload = make_valid_payload()

    payload.questions[0].tool_type = ""

    errors = validate_import(payload)

    assert any(
        e.field == "questions.tool_type"
        for e in errors
    )


def test_unknown_question_set_reference():
    payload = make_valid_payload()

    payload.question_set.items.append(
        QuestionSetItemImport(
            source_ref="Q999",
            order=3,
        )
    )

    errors = validate_import(payload)

    assert any(
        e.field == "question_set.items.source_ref"
        for e in errors
    )


def test_duplicate_question_order():
    payload = make_valid_payload()

    payload.question_set.items.append(
        QuestionSetItemImport(
            source_ref="Q002",
            order=1,
        )
    )

    errors = validate_import(payload)

    assert any(
        e.field == "question_set.items.order"
        for e in errors
    )


def test_empty_competency_list():
    payload = make_valid_payload()

    payload.competencies.clear()

    errors = validate_import(payload)

    assert any(
        e.field == "competencies"
        for e in errors
    )


def test_empty_question_list():
    payload = make_valid_payload()

    payload.questions.clear()

    errors = validate_import(payload)

    assert any(
        e.field == "questions"
        for e in errors
    )


def test_empty_question_set():
    payload = make_valid_payload()

    payload.question_set.items.clear()

    errors = validate_import(payload)

    assert any(
        e.field == "question_set.items"
        for e in errors
    )