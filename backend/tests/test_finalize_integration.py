"""Mocked integration tests for `adaptive_loop.finalize()`.

No real database or network — a small in-memory fake stands in for the Supabase
AsyncClient's fluent `.table(...).select/upsert/update(...).eq(...).execute()` API,
just enough surface to assert *behavior*: which tables get written, with what
payloads, whether repeated upserts are idempotent (same final row count/content
after being called twice), and that the session row is correctly marked completed.
"""
from __future__ import annotations

import pytest

from app.agent.adaptive_loop import finalize
from app.services.scoring import CAP_CONVERGED_REASON, MAX_QUESTIONS

pytestmark = pytest.mark.asyncio


# ── Fake Supabase-style fluent client ────────────────────────────────────────────
class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, db: "_FakeDB", table_name: str):
        self._db = db
        self._table = table_name
        self._op = None
        self._payload = None
        self._on_conflict = None
        self._filters: dict = {}

    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def upsert(self, rows, on_conflict=None):
        self._op = "upsert"
        self._payload = rows
        self._on_conflict = on_conflict
        return self

    def update(self, values):
        self._op = "update"
        self._payload = values
        return self

    def eq(self, column, value):
        self._filters[column] = value
        return self

    async def execute(self):
        self._db.calls.append({
            "table": self._table,
            "op": self._op,
            "payload": self._payload,
            "on_conflict": self._on_conflict,
            "filters": dict(self._filters),
        })
        table_store = self._db.store.setdefault(self._table, [])

        if self._op == "upsert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            key_cols = self._on_conflict.split(",") if self._on_conflict else None
            for row in rows:
                if key_cols:
                    key = tuple(row.get(k) for k in key_cols)
                    idx = next(
                        (i for i, r in enumerate(table_store)
                         if tuple(r.get(k) for k in key_cols) == key),
                        None,
                    )
                    if idx is not None:
                        table_store[idx] = dict(row)
                    else:
                        table_store.append(dict(row))
                else:
                    table_store.append(dict(row))
            return _FakeResponse(rows)

        if self._op == "update":
            matched = [r for r in table_store if all(r.get(k) == v for k, v in self._filters.items())]
            for row in matched:
                row.update(self._payload)
            return _FakeResponse(matched)

        if self._op == "select":
            filtered = [r for r in table_store if all(r.get(k) == v for k, v in self._filters.items())]
            return _FakeResponse(filtered)

        return _FakeResponse(None)


class _FakeDB:
    """Fakes just enough of the Supabase AsyncClient fluent API for these tests."""

    def __init__(self):
        self.calls: list[dict] = []
        self.store: dict[str, list[dict]] = {}

    def table(self, name: str) -> _FakeQuery:
        return _FakeQuery(self, name)

    def seed(self, table_name: str, rows: list[dict]) -> None:
        self.store[table_name] = [dict(r) for r in rows]


def _sample_state() -> dict:
    """One competency converges cleanly (confidence), one is cap-converged and
    below target — exercises both the normal path and the low-confidence path."""
    return {
        "per_competency": {
            "comp-python": {
                "self_rating": 4,
                "initial_estimate": 4,
                "level": 5,
                "confidence": 0.95,
                "converged_reason": "confidence",
                "questions_asked": 4,
            },
            "comp-sql": {
                "self_rating": 2,
                "initial_estimate": 2,
                "level": 2,
                "confidence": 0.4,
                "converged_reason": CAP_CONVERGED_REASON,
                "questions_asked": MAX_QUESTIONS,
            },
        }
    }


class TestFinalizePersistence:
    async def test_persists_session_competency_results(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        await finalize(db, {"id": "sess-1"}, _sample_state())

        rows = db.store["session_competency_results"]
        assert {r["competency_id"] for r in rows} == {"comp-python", "comp-sql"}
        by_id = {r["competency_id"]: r for r in rows}
        assert by_id["comp-python"]["final_level"] == 5
        assert by_id["comp-python"]["low_confidence"] is False
        assert by_id["comp-sql"]["final_level"] == 2
        assert by_id["comp-sql"]["low_confidence"] is True

    async def test_persists_final_report_with_low_confidence_rollup(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        await finalize(db, {"id": "sess-1"}, _sample_state())

        reports = db.store["final_reports"]
        assert len(reports) == 1
        report = reports[0]
        assert report["session_id"] == "sess-1"
        assert report["has_low_confidence"] is True
        assert set(report["skill_scores"].keys()) == {"comp-python", "comp-sql"}
        assert report["skill_scores"]["comp-sql"]["low_confidence"] is True
        assert report["skill_scores"]["comp-python"]["low_confidence"] is False
        assert report["overall_pct"] == 70  # mean(100, 40)

    async def test_marks_session_completed(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress", "completed_at": None}])

        await finalize(db, {"id": "sess-1"}, _sample_state())

        session_row = db.store["sessions"][0]
        assert session_row["status"] == "completed"
        assert session_row["completed_at"] is not None

    async def test_sets_complete_flag_and_closing_emit(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        result_state = await finalize(db, {"id": "sess-1"}, _sample_state())

        assert result_state["_complete"] is True
        assert result_state["_emit"]["overall_pct"] == 70
        assert result_state["_emit"]["level_label"] == "Advanced"

    async def test_raises_on_empty_per_competency(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        with pytest.raises(ValueError):
            await finalize(db, {"id": "sess-1"}, {"per_competency": {}})


class TestFinalizeIdempotency:
    async def test_repeated_calls_do_not_duplicate_rows(self):
        """Simulates a retried/duplicate turn calling finalize() twice — the upsert
        on_conflict keys must collapse to the same final state, not double the rows."""
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        await finalize(db, {"id": "sess-1"}, _sample_state())
        await finalize(db, {"id": "sess-1"}, _sample_state())  # second, identical call

        assert len(db.store["session_competency_results"]) == 2  # not 4
        assert len(db.store["final_reports"]) == 1               # not 2

    async def test_upserts_use_correct_conflict_keys(self):
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        await finalize(db, {"id": "sess-1"}, _sample_state())

        upserts = [c for c in db.calls if c["op"] == "upsert"]
        scr_upserts = [c for c in upserts if c["table"] == "session_competency_results"]
        report_upserts = [c for c in upserts if c["table"] == "final_reports"]
        assert scr_upserts and all(c["on_conflict"] == "session_id,competency_id" for c in scr_upserts)
        assert report_upserts and all(c["on_conflict"] == "session_id" for c in report_upserts)

    async def test_repeated_calls_produce_identical_payloads(self):
        """The upsert payload itself must be deterministic across calls with the same
        input state — no incidental drift (e.g. timestamps) in the scored rows."""
        db = _FakeDB()
        db.seed("sessions", [{"id": "sess-1", "status": "in_progress"}])

        await finalize(db, {"id": "sess-1"}, _sample_state())
        first_scr_payload = next(
            c["payload"] for c in db.calls
            if c["op"] == "upsert" and c["table"] == "session_competency_results"
        )
        first_report_payload = next(
            c["payload"] for c in db.calls
            if c["op"] == "upsert" and c["table"] == "final_reports"
        )

        await finalize(db, {"id": "sess-1"}, _sample_state())
        second_scr_payload = next(
            c["payload"] for c in reversed(db.calls)
            if c["op"] == "upsert" and c["table"] == "session_competency_results"
        )
        second_report_payload = next(
            c["payload"] for c in reversed(db.calls)
            if c["op"] == "upsert" and c["table"] == "final_reports"
        )

        assert first_scr_payload == second_scr_payload
        assert first_report_payload == second_report_payload