"""Single source of truth for question payload shapes, per tool_type.  [GIVEN — your reference]

Every required field here is one the grader (services/grading.py) actually reads — so a question
that validates here can be graded. Use `validate_question_payload` on import (return per-row errors)
and drive your admin "add question" form from `QUESTION_TYPES`.
"""
from __future__ import annotations

QUESTION_TYPES: dict[str, dict] = {
    "mcq": {
        "label": "Multiple Choice",
        "example": {
            "body": "Which HTTP status code means a resource was created?",
            "payload": {
                "options": [
                    {"id": "a", "text": "200 OK"},
                    {"id": "b", "text": "201 Created"},
                    {"id": "c", "text": "404 Not Found"},
                ],
                "answer_key": {"correct_id": "b"},
                "explanation": "201 Created is returned when a request creates a new resource.",
            },
        },
    },
    "voice": {
        "label": "Voice / Open-ended",
        "example": {
            "body": "Describe a time you resolved a conflict on a team.",
            "payload": {"evaluation_criteria": ["Names the situation", "Explains their actions", "Reflects on the outcome"]},
        },
    },
    "coding": {
        "label": "Coding",
        "example": {
            "body": "Return the sum of even numbers in a list.",
            "payload": {
                "language": "python",
                "starter_code": "def sum_even(nums):\n    pass",
                "test_cases": [{"input": "[1,2,3,4]", "expected_output": "6"}, {"input": "[]", "expected_output": "0"}],
            },
        },
    },
    "visualization": {
        "label": "Data Analysis",
        "example": {
            "body": "Sales dropped 30% while ad spend rose 20%. What would you investigate?",
            "payload": {"expected_insights": ["Notices the inverse relationship", "Proposes plausible causes", "Suggests a next step"]},
        },
    },
}

_OPEN_ENDED = {"voice", "visualization"}
_RUBRIC_KEYS = ("evaluation_criteria", "expected_insights", "rubric")

# Canonical difficulty ↔ 1–5 level mapping. The bank stores difficulty as easy/medium/hard (human-
# friendly); the adaptive loop selects and estimates on the 1–5 level scale, so map through this.
DIFFICULTY_TO_LEVEL = {"easy": 2, "medium": 3, "hard": 4}
LEVEL_TO_DIFFICULTY = {1: "easy", 2: "easy", 3: "medium", 4: "hard", 5: "hard"}


def level_of(difficulty) -> int:
    """easy/medium/hard (or an int) → a 1–5 level; defaults to 3 (medium) when unknown/missing."""
    if isinstance(difficulty, int):
        return max(1, min(5, difficulty))
    return DIFFICULTY_TO_LEVEL.get(str(difficulty or "").strip().lower(), 3)


def validate_question_payload(tool_type: str, body: str, payload: dict | None) -> list[str]:
    """Return human-readable errors (empty = gradable). Kept grader-accurate on purpose."""
    errors: list[str] = []
    if not (body or "").strip():
        errors.append("Question body is required.")
    payload = payload or {}

    if tool_type == "mcq":
        opts = [o for o in (payload.get("options") or []) if isinstance(o, dict) and o.get("id") and str(o.get("text") or "").strip()]
        if len(opts) < 2:
            errors.append("MCQ needs at least 2 options (id + text).")
        correct = (payload.get("answer_key") or {}).get("correct_id")
        if not correct:
            errors.append("MCQ needs answer_key.correct_id.")
        elif opts and not any(str(o["id"]) == str(correct) for o in opts):
            errors.append(f"correct_id '{correct}' matches no option.")

    elif tool_type == "coding":
        tcs = payload.get("test_cases") or []
        if not tcs:
            errors.append("Coding needs at least one test case.")
        elif not all(isinstance(c, dict) and "input" in c and "expected_output" in c for c in tcs):
            errors.append("Each test case needs input + expected_output.")

    elif tool_type in _OPEN_ENDED:
        has_signal = any(isinstance(payload.get(k), list) and any(str(x).strip() for x in payload[k]) for k in _RUBRIC_KEYS)
        if not has_signal:
            errors.append("Add evaluation_criteria / expected_insights so it can be graded.")

    return errors
