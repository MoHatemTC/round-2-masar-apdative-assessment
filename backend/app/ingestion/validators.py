"""
Pure validation for Question Bank imports.

This module performs validation only.

No DB.
No writes.
No FastAPI.
"""

from collections import Counter
from typing import List

from .schemas import (
    QuestionBankImport,
    ValidationErrorItem,
)


VALID_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


def validate_import(
    payload: QuestionBankImport,
) -> List[ValidationErrorItem]:
    """
    Validate the entire import payload.

    Returns a list of validation errors.

    Empty list == valid.
    """

    errors: List[ValidationErrorItem] = []

    competency_codes = set()

    source_refs = set()

    # ---------------------------------------------------------
    # Competencies
    # ---------------------------------------------------------

    duplicate_codes = Counter(
        c.code
        for c in payload.competencies
    )

    for index, competency in enumerate(
        payload.competencies,
        start=1,
    ):

        if duplicate_codes[competency.code] > 1:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="competencies.code",
                    message=f"Duplicate competency code '{competency.code}'.",
                )
            )

        competency_codes.add(
            competency.code
        )

    # ---------------------------------------------------------
    # Parent references
    # ---------------------------------------------------------

    for index, competency in enumerate(
        payload.competencies,
        start=1,
    ):

        if (
            competency.parent_code
            and competency.parent_code
            not in competency_codes
        ):

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="competencies.parent_code",
                    message=(
                        f"Unknown parent competency "
                        f"'{competency.parent_code}'."
                    ),
                )
            )

    # ---------------------------------------------------------
    # Questions
    # ---------------------------------------------------------

    duplicate_refs = Counter(
        q.source_ref
        for q in payload.questions
    )

    for index, question in enumerate(
        payload.questions,
        start=1,
    ):

        if duplicate_refs[question.source_ref] > 1:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="questions.source_ref",
                    message=(
                        f"Duplicate source_ref "
                        f"'{question.source_ref}'."
                    ),
                )
            )

        source_refs.add(
            question.source_ref
        )

        if question.competency not in competency_codes:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="questions.competency",
                    message=(
                        f"Unknown competency "
                        f"'{question.competency}'."
                    ),
                )
            )

        if question.difficulty not in VALID_DIFFICULTIES:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="questions.difficulty",
                    message=(
                        "Difficulty must be "
                        "'easy', 'medium', or 'hard'."
                    ),
                )
            )

        if not question.text.strip():

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="questions.text",
                    message="Question text is required.",
                )
            )

        if not question.tool_type.strip():

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="questions.tool_type",
                    message="Tool type is required.",
                )
            )

    # ---------------------------------------------------------
    # Question Set
    # ---------------------------------------------------------

    seen_orders = set()

    for index, item in enumerate(
        payload.question_set.items,
        start=1,
    ):

        if item.source_ref not in source_refs:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="question_set.items.source_ref",
                    message=(
                        f"Unknown question "
                        f"'{item.source_ref}'."
                    ),
                )
            )

        if item.order in seen_orders:

            errors.append(
                ValidationErrorItem(
                    row=index,
                    field="question_set.items.order",
                    message=(
                        f"Duplicate order "
                        f"{item.order}."
                    ),
                )
            )

        seen_orders.add(
            item.order
        )

    # ---------------------------------------------------------
    # Empty payload checks
    # ---------------------------------------------------------

    if not payload.competencies:

        errors.append(
            ValidationErrorItem(
                row=0,
                field="competencies",
                message="At least one competency is required.",
            )
        )

    if not payload.questions:

        errors.append(
            ValidationErrorItem(
                row=0,
                field="questions",
                message="At least one question is required.",
            )
        )

    if not payload.question_set.items:

        errors.append(
            ValidationErrorItem(
                row=0,
                field="question_set.items",
                message="Question set must contain at least one question.",
            )
        )

    return errors