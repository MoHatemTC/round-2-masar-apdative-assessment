"""
test_bank_validation.py

Covers:
  - _validate_item (row-level validation helper in app/routes/admin_bank.py)
  - POST /admin/question-bank/import (success + 422 with row-level errors)

Run with:
    cd backend
    python -m pytest tests/test_bank_validation.py -v
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.admin_bank import router, _validate_item

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures — one clean item per tool_type, taken from QUESTION_TYPES examples
# so they stay in sync with the single source of truth instead of drifting.
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_mcq_item():
    return {
        "source_ref": "mcq-001",
        "tool_type": "mcq",
        "body": "Which HTTP status code means a resource was created?",
        "payload": {
            "options": [
                {"id": "a", "text": "200 OK"},
                {"id": "b", "text": "201 Created"},
            ],
            "answer_key": {"correct_id": "b"},
        },
    }


@pytest.fixture
def valid_coding_item():
    return {
        "source_ref": "coding-001",
        "tool_type": "coding",
        "body": "Return the sum of even numbers in a list.",
        "payload": {
            "language": "python",
            "test_cases": [{"input": "[1,2,3,4]", "expected_output": "6"}],
        },
    }


@pytest.fixture
def valid_voice_item():
    return {
        "source_ref": "voice-001",
        "tool_type": "voice",
        "body": "Describe a time you resolved a conflict on a team.",
        "payload": {"evaluation_criteria": ["Names the situation", "Reflects on the outcome"]},
    }


# ---------------------------------------------------------------------------
# Unit tests: _validate_item
# ---------------------------------------------------------------------------

def test_valid_mcq_item_has_no_errors(valid_mcq_item):
    assert _validate_item(0, valid_mcq_item) is None


def test_valid_coding_item_has_no_errors(valid_coding_item):
    assert _validate_item(0, valid_coding_item) is None


def test_valid_voice_item_has_no_errors(valid_voice_item):
    assert _validate_item(0, valid_voice_item) is None


def test_mcq_missing_correct_id_is_flagged(valid_mcq_item):
    valid_mcq_item["payload"]["answer_key"] = {}
    result = _validate_item(2, valid_mcq_item)
    assert result is not None
    assert result["index"] == 2
    assert result["source_ref"] == "mcq-001"
    assert any("correct_id" in e for e in result["errors"])


def test_mcq_correct_id_matching_no_option_is_flagged(valid_mcq_item):
    valid_mcq_item["payload"]["answer_key"] = {"correct_id": "z"}
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("matches no option" in e for e in result["errors"])


def test_coding_with_no_test_cases_is_flagged(valid_coding_item):
    valid_coding_item["payload"]["test_cases"] = []
    result = _validate_item(0, valid_coding_item)
    assert result is not None
    assert any("test case" in e for e in result["errors"])


def test_voice_missing_rubric_signal_is_flagged(valid_voice_item):
    valid_voice_item["payload"] = {}
    result = _validate_item(0, valid_voice_item)
    assert result is not None
    assert any("evaluation_criteria" in e for e in result["errors"])


def test_missing_body_is_flagged(valid_mcq_item):
    valid_mcq_item["body"] = ""
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("body is required" in e.lower() for e in result["errors"])


def test_missing_tool_type_is_flagged(valid_mcq_item):
    del valid_mcq_item["tool_type"]
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("tool_type is required" in e for e in result["errors"])


def test_unrecognized_tool_type_is_flagged(valid_mcq_item):
    valid_mcq_item["tool_type"] = "not_a_real_type"
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("Unrecognized tool_type" in e for e in result["errors"])


def test_non_object_payload_is_flagged_not_crashed(valid_mcq_item):
    """Regression test: payload as a string used to raise an unhandled AttributeError
    (validate_question_payload calls payload.get(...)) instead of a row-level error."""
    valid_mcq_item["payload"] = "not an object"
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("payload must be an object" in e for e in result["errors"])


def test_non_string_body_is_flagged_not_crashed(valid_mcq_item):
    """Regression test: body as a non-string used to raise an unhandled AttributeError
    (validate_question_payload calls body.strip()) instead of a row-level error."""
    valid_mcq_item["body"] = 12345
    result = _validate_item(0, valid_mcq_item)
    assert result is not None
    assert any("body must be a string" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# Endpoint tests: POST /admin/question-bank/import
# ---------------------------------------------------------------------------

def test_import_all_valid_items_returns_200(valid_mcq_item, valid_coding_item, valid_voice_item):
    response = client.post(
        "/admin/question-bank/import",
        json=[valid_mcq_item, valid_coding_item, valid_voice_item],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["item_count"] == 3


def test_import_with_one_bad_row_returns_422_with_row_errors(valid_mcq_item, valid_coding_item):
    valid_coding_item["payload"]["test_cases"] = []  # break this one

    response = client.post(
        "/admin/question-bank/import",
        json=[valid_mcq_item, valid_coding_item],
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert len(detail["row_errors"]) == 1
    assert detail["row_errors"][0]["index"] == 1
    assert detail["row_errors"][0]["source_ref"] == "coding-001"


def test_import_valid_rows_are_not_reported_as_errors_alongside_bad_ones(
    valid_mcq_item, valid_coding_item, valid_voice_item
):
    valid_voice_item["payload"] = {}  # break only this one; mcq and coding stay valid

    response = client.post(
        "/admin/question-bank/import",
        json=[valid_mcq_item, valid_coding_item, valid_voice_item],
    )

    assert response.status_code == 422
    row_errors = response.json()["detail"]["row_errors"]
    assert len(row_errors) == 1
    assert row_errors[0]["index"] == 2
    assert row_errors[0]["source_ref"] == "voice-001"


def test_import_multiple_bad_rows_reports_each_with_correct_index(valid_mcq_item, valid_coding_item):
    valid_mcq_item["payload"]["answer_key"] = {}
    valid_coding_item["payload"]["test_cases"] = []

    response = client.post(
        "/admin/question-bank/import",
        json=[valid_mcq_item, valid_coding_item],
    )

    assert response.status_code == 422
    row_errors = response.json()["detail"]["row_errors"]
    indices = {row["index"] for row in row_errors}
    assert indices == {0, 1}


def test_import_empty_batch_returns_422():
    response = client.post("/admin/question-bank/import", json=[])
    assert response.status_code == 422


def test_import_with_malformed_payload_type_returns_422_not_500(valid_mcq_item, valid_coding_item):
    """Regression test: a row with the wrong JSON type for payload must not crash the
    whole batch (500) — it must be reported as that row's error, with other rows intact."""
    valid_mcq_item["payload"] = "not an object"

    response = client.post(
        "/admin/question-bank/import",
        json=[valid_mcq_item, valid_coding_item],
    )

    assert response.status_code == 422
    row_errors = response.json()["detail"]["row_errors"]
    assert len(row_errors) == 1
    assert row_errors[0]["index"] == 0
    assert any("payload must be an object" in e for e in row_errors[0]["errors"])


def test_import_does_not_persist_anything_yet(valid_mcq_item):
    """Scaffold-stage contract: a valid batch is validated but not written anywhere."""
    response = client.post("/admin/question-bank/import", json=[valid_mcq_item])
    assert response.status_code == 200
    assert "not yet implemented" in response.json()["message"].lower()