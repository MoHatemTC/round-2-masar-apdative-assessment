"""Admin API — Bank Ingestion & Validation lane.

Scaffolds POST /admin/question-bank/import: validates every item's payload against its
tool_type and returns 422 with row-level errors on any failure. Persistence (upserting
competencies/questions/sets) is explicitly out of scope here and lands next week — see
the TODO in `import_bank` below.

`QUESTION_TYPES` and `validate_question_payload` (app/schemas/question_types.py) are the
single source of truth for what a valid payload looks like per tool_type. This module does
not re-implement or fork that logic — it only adds the one check that file doesn't cover
(rejecting an unrecognized tool_type outright) and assembles per-row results.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

# TODO(auth): this endpoint should require an admin-authenticated caller. Wire in the
# real dependency once located, e.g.:
#     from app.auth import require_admin
#     router = APIRouter(prefix="/admin", tags=["admin-bank"], dependencies=[Depends(require_admin)])
# Left open (not stubbed with a fake check) so it isn't mistaken for a real access control.

# from app.db import get_db  # not needed yet — this scaffold does not touch the database

from app.schemas.question_types import QUESTION_TYPES, validate_question_payload

router = APIRouter(prefix="/admin", tags=["admin-bank"])


def _validate_item(index: int, item: dict) -> dict | None:
    """Validate a single import row. Returns an error entry, or None if the row is clean.

    Two layers of validation, in order:
      1. tool_type must be a key in QUESTION_TYPES at all. validate_question_payload does
         not check this itself (an unrecognized tool_type silently produces zero errors),
         so this endpoint owns that one gap rather than editing the given reference file.
      2. If the tool_type is recognized, delegate the actual shape/content check to
         validate_question_payload — the single source of truth for what "valid" means
         for that type.
    """
    source_ref = item.get("source_ref")
    tool_type = item.get("tool_type")
    body = item.get("body", "")
    payload = item.get("payload")

    errors: list[str] = []

    if not tool_type:
        errors.append("tool_type is required.")
    elif tool_type not in QUESTION_TYPES:
        known = ", ".join(sorted(QUESTION_TYPES.keys()))
        errors.append(f"Unrecognized tool_type '{tool_type}'. Known types: {known}.")
    else:
        errors.extend(validate_question_payload(tool_type, body, payload))

    if not errors:
        return None

    return {
        "index": index,
        "source_ref": source_ref,
        "tool_type": tool_type,
        "errors": errors,
    }


@router.post("/question-bank/import")
async def import_bank(items: list[dict] = Body(...), set_name: str | None = None):
    """Validate a batch of question-bank import rows; return 422 with row-level errors.

    Each item is expected to carry at least: tool_type, body, payload (plus source_ref,
    for traceability — recommended but not enforced at this stage). Full field/shape
    requirements per tool_type live in QUESTION_TYPES.

    TODO (next week — not implemented here):
      1. Upsert competencies: tracks (by code), then subs (by code, parent = track).
      2. Upsert questions on source_ref (preserve difficulty!). Link competency_id = sub.
      3. Create/find a question_set named `set_name` (default: the track name(s)); add items.
      4. Return {tracks, sub_competencies, questions, set: {id, name, item_count}}.
    Once that lands, a clean batch (no row_errors) should proceed to persistence instead
    of stopping at the "validated" response below.
    """
    if not items:
        raise HTTPException(status_code=422, detail={"message": "No items provided."})

    row_errors = [
        entry for entry in (_validate_item(i, item) for i, item in enumerate(items))
        if entry is not None
    ]

    if row_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"{len(row_errors)} of {len(items)} item(s) failed validation.",
                "row_errors": row_errors,
            },
        )

    return {
        "valid": True,
        "item_count": len(items),
        "message": "All items passed validation. Upsert is not yet implemented — no rows were written.",
    }
