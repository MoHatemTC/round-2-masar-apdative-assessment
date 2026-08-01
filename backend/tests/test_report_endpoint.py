"""Mocked integration tests for `GET /admin/sessions/{session_id}/report`.

No real database or network. We pass a tiny in-memory fake seeded with rows
directly into the route handler, so we can assert the endpoint's actual behavior:
correct report + competency-results shape, low-confidence data surfacing correctly,
per-session scoping, answers inclusion, and 404/409 error handling.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.routes.admin import get_report

pytestmark = pytest.mark.asyncio


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, store: dict, table_name: str):
        self._store = store
        self._table = table_name
        self._filters: dict = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    async def execute(self):
        rows = self._store.get(self._table, [])
        filtered = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
        return _FakeResponse(filtered)


class _FakeDB:
    def __init__(self, store: dict):
        self._store = store

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._store, name)


class TestGetReportEndpoint:
    async def test_returns_report_and_competency_results_and_answers(self):
        store = {
            "sessions": [{"id": "sess-1", "status": "completed"}],
            "final_reports": [{
                "session_id": "sess-1",
                "overall_pct": 75,
                "level_label": "Advanced",
                "has_low_confidence": False
            }],
            "session_competency_results": [
                {"session_id": "sess-1", "competency_id": "comp-python", "low_confidence": False},
                {"session_id": "sess-1", "competency_id": "comp-sql", "low_confidence": False},
            ],
            "answers": [
                {"session_id": "sess-1", "question_number": 1, "score": 4},
                {"session_id": "sess-1", "question_number": 2, "score": 5},
            ]
        }
        fake_db = _FakeDB(store)

        result = await get_report("sess-1", db=fake_db)

        assert result["session_id"] == "sess-1"
        assert result["overall_pct"] == 75
        assert result["level_label"] == "Advanced"
        assert len(result["competency_results"]) == 2
        assert len(result["answers"]) == 2

    async def test_low_confidence_data_present_in_returned_report(self):
        store = {
            "sessions": [{"id": "sess-1", "status": "completed"}],
            "final_reports": [{
                "session_id": "sess-1",
                "overall_pct": 40,
                "level_label": "Developing",
                "has_low_confidence": True
            }],
            "session_competency_results": [
                {
                    "session_id": "sess-1",
                    "competency_id": "comp-sql",
                    "low_confidence": True,
                    "converged_reason": "max_questions",
                },
            ],
            "answers": []
        }
        fake_db = _FakeDB(store)

        result = await get_report("sess-1", db=fake_db)

        assert result["has_low_confidence"] is True
        assert result["competency_results"][0]["low_confidence"] is True
        assert result["competency_results"][0]["converged_reason"] == "max_questions"

    async def test_returns_404_when_session_missing(self):
        store = {"sessions": [], "final_reports": [], "session_competency_results": [], "answers": []}
        fake_db = _FakeDB(store)

        with pytest.raises(HTTPException) as exc_info:
            await get_report("nonexistent-session", db=fake_db)

        assert exc_info.value.status_code == 404
        assert "Session not found" in str(exc_info.value.detail)

    async def test_returns_409_when_session_incomplete(self):
        store = {
            "sessions": [{"id": "sess-1", "status": "in_progress"}],
            "final_reports": [],
            "session_competency_results": [],
            "answers": []
        }
        fake_db = _FakeDB(store)

        with pytest.raises(HTTPException) as exc_info:
            await get_report("sess-1", db=fake_db)

        assert exc_info.value.status_code == 409
        assert "not available yet" in str(exc_info.value.detail)

    async def test_returns_404_when_report_missing_but_session_completed(self):
        store = {
            "sessions": [{"id": "sess-1", "status": "completed"}],
            "final_reports": [],
            "session_competency_results": [],
            "answers": []
        }
        fake_db = _FakeDB(store)

        with pytest.raises(HTTPException) as exc_info:
            await get_report("sess-1", db=fake_db)

        assert exc_info.value.status_code == 404
        assert "Final report missing" in str(exc_info.value.detail)

    async def test_scopes_data_to_requested_session_only(self):
        store = {
            "sessions": [
                {"id": "sess-1", "status": "completed"},
                {"id": "sess-2", "status": "completed"}
            ],
            "final_reports": [
                {"session_id": "sess-1", "overall_pct": 80, "level_label": "Advanced", "has_low_confidence": False},
                {"session_id": "sess-2", "overall_pct": 90, "level_label": "Expert", "has_low_confidence": False},
            ],
            "session_competency_results": [
                {"session_id": "sess-1", "competency_id": "a"},
                {"session_id": "sess-2", "competency_id": "b"},  # different session
            ],
            "answers": [
                {"session_id": "sess-1", "question_number": 1},
                {"session_id": "sess-2", "question_number": 1},  # different session
            ]
        }
        fake_db = _FakeDB(store)

        result = await get_report("sess-1", db=fake_db)

        assert result["overall_pct"] == 80
        assert len(result["competency_results"]) == 1
        assert result["competency_results"][0]["competency_id"] == "a"
        assert len(result["answers"]) == 1