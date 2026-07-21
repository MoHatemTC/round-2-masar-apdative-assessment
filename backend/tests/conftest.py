"""Shared fixtures for the intake tests.

`FakeDB` is a tiny stand-in for the real Supabase `AsyncClient` — it implements just the fluent
`.table(...).select/insert/update/upsert(...).eq(...).execute()` surface `candidate_intake.py`
actually calls, backed by plain in-memory dicts instead of Postgres. This lets the route/handler
logic (validation, status codes, what gets written where) be tested without a live database.
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeResult:
    """Mimics the `.data` attribute on a real supabase-py `APIResponse`."""

    def __init__(self, data: list[dict]):
        self.data = data


class FakeQuery:
    """One chainable `db.table(name)....execute()` call. Supports the handful of operations the
    intake routes use: select (with .eq filters), insert, update (with .eq filters), upsert."""

    def __init__(self, tables: dict[str, list[dict]], table_name: str):
        self._tables = tables
        self._table_name = table_name
        self._op: str | None = None
        self._payload: dict | None = None
        self._filters: list[tuple[str, Any]] = []

    def select(self, *_args, **_kwargs) -> "FakeQuery":
        self._op = self._op or "select"
        return self

    def insert(self, payload: dict) -> "FakeQuery":
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict) -> "FakeQuery":
        self._op = "update"
        self._payload = payload
        return self

    def upsert(self, payload: dict) -> "FakeQuery":
        self._op = "upsert"
        self._payload = payload
        return self

    def eq(self, field: str, value: Any) -> "FakeQuery":
        self._filters.append((field, value))
        return self

    def _rows(self) -> list[dict]:
        return self._tables.setdefault(self._table_name, [])

    def _matches(self, row: dict) -> bool:
        return all(row.get(field) == value for field, value in self._filters)

    async def execute(self) -> FakeResult:
        rows = self._rows()

        if self._op == "insert":
            row = dict(self._payload or {})
            row.setdefault("id", str(uuid.uuid4()))
            rows.append(row)
            return FakeResult([row])

        if self._op == "select":
            return FakeResult([r for r in rows if self._matches(r)])

        if self._op == "update":
            matched = [r for r in rows if self._matches(r)]
            for row in matched:
                row.update(self._payload or {})
            return FakeResult(matched)

        if self._op == "upsert":
            payload = self._payload or {}
            pk = ("session_id", "competency_id")
            if all(k in payload for k in pk):
                existing = next(
                    (r for r in rows if r.get("session_id") == payload["session_id"]
                     and r.get("competency_id") == payload["competency_id"]),
                    None,
                )
                if existing is not None:
                    existing.update(payload)
                    return FakeResult([existing])
            row = dict(payload)
            rows.append(row)
            return FakeResult([row])

        return FakeResult([])


class FakeDB:
    """In-memory stand-in for `AsyncClient`. `db.table("sessions")` etc. all share `self.tables`,
    so writes made in one call are visible to reads in the next, just like a real DB session."""

    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self.tables, name)

    def seed(self, table_name: str, row: dict) -> dict:
        """Test helper: insert a row directly, bypassing the fluent API."""
        row = dict(row)
        row.setdefault("id", str(uuid.uuid4()))
        self.tables.setdefault(table_name, []).append(row)
        return row


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def supabase_client(fake_db: FakeDB) -> FakeDB:
    """Alias of `fake_db` under the name `tests/ingestion/*` expects.

    `app/ingestion/upserts.py` is written against the real Supabase `AsyncClient`'s
    `.table(...).select/insert/update(...).eq(...).execute()` surface (see its own comment:
    "FakeDB does not support delete(), so we avoid it and update/insert only") — `FakeDB`
    already implements exactly that surface, so the ingestion tests reuse the same fake the
    intake tests use rather than needing a second one.
    """
    return fake_db


@pytest.fixture
def client(fake_db, monkeypatch):
    """A FastAPI TestClient mounting only the intake router, with `get_db` patched to return
    `fake_db`. Mounting just this router (rather than the full `app.main.app`) keeps the test
    isolated from the other lanes' still-`NotImplementedError` stubs."""
    from app.routes import candidate_intake

    async def _fake_get_db():
        return fake_db

    monkeypatch.setattr(candidate_intake, "get_db", _fake_get_db)

    app = FastAPI()
    app.include_router(candidate_intake.router)
    return TestClient(app)