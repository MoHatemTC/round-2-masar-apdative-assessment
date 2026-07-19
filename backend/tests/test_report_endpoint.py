"""Mocked integration tests for `GET /admin/sessions/{session_id}/report`.

No real database or network — `app.db.get_db` is monkeypatched to return a tiny
in-memory fake seeded with rows, so we can assert the endpoint's actual behavior:
correct report + competency-results shape, low-confidence data surfacing correctly,
per-session scoping, and 404 when no report exists yet.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.routes import admin as admin_module
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

    async def execute(self):
        rows = self._store.get(self._table, [])
        filtered = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
        return _FakeResponse(filtered)


class _FakeDB:
    def __init__(self, store: dict):
        self._store = store

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self._store, name)


def _patch_db(monkeypatch, store: dict) -> None:
    async def _fake_get_db():
        return _FakeDB(store)

    monkeypatch.setattr(admin_module, "get_db", _fake_get_db)


class TestGetReportEndpoint:
    async def test_returns_report_and_competency_results(self, monkeypatch):
        store = {
            "final_reports": [{
                "session_id": "sess-1",
                "overall_pct": 70,
                "overall_level": 4,
                "level_label": "Advanced",
                "has_low_confidence": True,
                "skill_scores": {"comp-sql": {"low_confidence": True, "pct": 40}},
            }],
            "session_competency_results": [
                {"session_id": "sess-1", "competency_id": "comp-python", "low_confidence": False},
                {"session_id": "sess-1", "competency_id": "comp-sql", "low_confidence": True},
            ],
        }
        _patch_db(monkeypatch, store)

        result = await get_report("sess-1")

        assert result["report"]["session_id"] == "sess-1"
        assert result["report"]["overall_pct"] == 70
        assert len(result["competency_results"]) == 2

    async def test_low_confidence_data_present_in_returned_report(self, monkeypatch):
        store = {
            "final_reports": [{
                "session_id": "sess-1",
                "overall_pct": 70,
                "has_low_confidence": True,
                "skill_scores": {
                    "comp-sql": {"low_confidence": True, "band_label": "Developing"},
                    "comp-python": {"low_confidence": False, "band_label": "Expert"},
                },
            }],
            "session_competency_results": [
                {
                    "session_id": "sess-1",
                    "competency_id": "comp-sql",
                    "low_confidence": True,
                    "converged_reason": "max_questions",
                },
            ],
        }
        _patch_db(monkeypatch, store)

        result = await get_report("sess-1")

        assert result["report"]["has_low_confidence"] is True
        assert result["report"]["skill_scores"]["comp-sql"]["low_confidence"] is True
        assert result["report"]["skill_scores"]["comp-python"]["low_confidence"] is False
        assert result["competency_results"][0]["low_confidence"] is True
        assert result["competency_results"][0]["converged_reason"] == "max_questions"

    async def test_returns_404_when_report_missing(self, monkeypatch):
        _patch_db(monkeypatch, {"final_reports": [], "session_competency_results": []})

        with pytest.raises(HTTPException) as exc_info:
            await get_report("nonexistent-session")

        assert exc_info.value.status_code == 404

    async def test_scopes_competency_results_to_requested_session_only(self, monkeypatch):
        store = {
            "final_reports": [
                {"session_id": "sess-1", "overall_pct": 80, "has_low_confidence": False, "skill_scores": {}},
            ],
            "session_competency_results": [
                {"session_id": "sess-1", "competency_id": "a"},
                {"session_id": "sess-2", "competency_id": "b"},  # different session — must not leak
            ],
        }
        _patch_db(monkeypatch, store)

        result = await get_report("sess-1")

        assert len(result["competency_results"]) == 1
        assert result["competency_results"][0]["competency_id"] == "a"

    async def test_no_low_confidence_case_reports_false(self, monkeypatch):
        store = {
            "final_reports": [{
                "session_id": "sess-2",
                "overall_pct": 90,
                "has_low_confidence": False,
                "skill_scores": {"a": {"low_confidence": False}},
            }],
            "session_competency_results": [
                {"session_id": "sess-2", "competency_id": "a", "low_confidence": False},
            ],
        }
        _patch_db(monkeypatch, store)

        result = await get_report("sess-2")

        assert result["report"]["has_low_confidence"] is False
        assert all(r["low_confidence"] is False for r in result["competency_results"])