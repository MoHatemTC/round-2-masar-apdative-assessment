"""Normalize the PRD's flat question-bank format into the structured import payload.

The PRD (and data/sample_question_bank.json) define an upload as ONE flat JSON array
where every item embeds its own track + sub_competency:

    [{"source_ref", "track": {code, name, ...}, "sub_competency": {code, name},
      "tool_type", "difficulty", "rubric", "body", "payload"}, ...]

The import pipeline (schemas.QuestionBankImport -> validators -> upserts) works on the
pre-normalized {competencies, questions, question_set} shape instead. This module bridges
the two so admins can upload either format. Field mapping mirrors upserts.py:
body -> text, rubric -> expected_answer, payload -> metadata.
"""
from __future__ import annotations


def is_flat_bank(raw: object) -> bool:
    """True when the body is the PRD flat format: a bare array of items, or
    {"items": [...], "set_name": ...} as sent by the admin UI."""
    if isinstance(raw, list):
        return True
    return isinstance(raw, dict) and "items" in raw


def normalize_flat_bank(raw: list | dict) -> dict:
    """Convert the flat format into the QuestionBankImport dict shape.

    Purely structural: dedupes tracks/sub-competencies by code (first occurrence wins),
    preserves question order for question_set.items, and leaves per-question payload
    validation to the existing validators. Missing fields pass through as-is so the
    Pydantic model reports them with a per-field location.
    """
    if isinstance(raw, dict):
        items = raw.get("items") or []
        set_name = raw.get("set_name")
    else:
        items = raw
        set_name = None

    competencies: list[dict] = []
    seen_codes: set[str] = set()
    questions: list[dict] = []
    set_items: list[dict] = []
    first_track_name: str | None = None

    for order, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            # Let the model reject it with a location instead of crashing here.
            questions.append({"_row": order, "invalid": item})
            continue

        track = item.get("track") or {}
        sub = item.get("sub_competency") or {}
        track_code = track.get("code")
        sub_code = sub.get("code")

        if track_code and track_code not in seen_codes:
            seen_codes.add(track_code)
            competencies.append({"code": track_code, "name": track.get("name") or track_code})
            first_track_name = first_track_name or track.get("name")

        if sub_code and sub_code not in seen_codes:
            seen_codes.add(sub_code)
            competencies.append({
                "code": sub_code,
                "name": sub.get("name") or sub_code,
                "parent_code": track_code,
            })

        questions.append({
            "source_ref": item.get("source_ref"),
            "competency": sub_code or track_code,
            "text": item.get("body"),
            "difficulty": item.get("difficulty"),
            "tool_type": item.get("tool_type"),
            "expected_answer": item.get("rubric"),
            "metadata": item.get("payload") or {},
        })
        if item.get("source_ref"):
            set_items.append({"source_ref": item["source_ref"], "order": order})

    return {
        "competencies": competencies,
        "questions": questions,
        "question_set": {
            "name": set_name or (f"{first_track_name} Bank" if first_track_name else "Imported Question Set"),
            "items": set_items,
        },
    }
