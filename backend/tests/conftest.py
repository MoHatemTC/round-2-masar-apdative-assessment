"""
Shared fixtures for tests.

FakeDB:
- Mimics Supabase AsyncClient
- Supports:
    table()
    select()
    insert()
    update()
    upsert()
    eq()
    execute()

Used for:
- candidate intake tests
- ingestion tests
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------
# Fake Supabase Response
# ---------------------------------------------------------

class FakeResult:
    """
    Mimics supabase-py APIResponse.
    """

    def __init__(
        self,
        data: list[dict],
    ):
        self.data = data



# ---------------------------------------------------------
# Fake Query Builder
# ---------------------------------------------------------

class FakeQuery:
    """
    Minimal Supabase query mock.

    Supports:

    .select()
    .insert()
    .update()
    .upsert()
    .eq()
    .execute()
    """

    def __init__(
        self,
        tables: dict[str, list[dict]],
        table_name: str,
    ):

        self._tables = tables
        self._table_name = table_name

        self._op: str | None = None

        self._payload: dict | None = None

        self._conflict: str | None = None

        self._filters: list[
            tuple[str, Any]
        ] = []



    # -----------------------------------------------------
    # Query operations
    # -----------------------------------------------------

    def select(
        self,
        *_args,
        **_kwargs,
    ) -> "FakeQuery":

        self._op = self._op or "select"

        return self



    def insert(
        self,
        payload: dict,
    ) -> "FakeQuery":

        self._op = "insert"

        self._payload = payload

        return self



    def update(
        self,
        payload: dict,
    ) -> "FakeQuery":

        self._op = "update"

        self._payload = payload

        return self



    def upsert(
        self,
        payload: dict,
        on_conflict: str | None = None,
    ) -> "FakeQuery":

        self._op = "upsert"

        self._payload = payload

        self._conflict = on_conflict

        return self



    def eq(
        self,
        field: str,
        value: Any,
    ) -> "FakeQuery":

        self._filters.append(
            (
                field,
                value,
            )
        )

        return self



    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def _rows(self) -> list[dict]:

        return self._tables.setdefault(
            self._table_name,
            [],
        )



    def _matches(
        self,
        row: dict,
    ) -> bool:

        return all(
            row.get(field) == value
            for field, value
            in self._filters
        )



    # -----------------------------------------------------
    # Execute
    # -----------------------------------------------------

    async def execute(self) -> FakeResult:

        rows = self._rows()



        # -----------------------------
        # INSERT
        # -----------------------------

        if self._op == "insert":

            row = dict(
                self._payload or {}
            )

            row.setdefault(
                "id",
                str(uuid.uuid4()),
            )

            rows.append(row)

            return FakeResult(
                [row]
            )



        # -----------------------------
        # SELECT
        # -----------------------------

        if self._op == "select":

            return FakeResult(
                [
                    row
                    for row in rows
                    if self._matches(row)
                ]
            )



        # -----------------------------
        # UPDATE
        # -----------------------------

        if self._op == "update":

            matched = [
                row
                for row in rows
                if self._matches(row)
            ]


            for row in matched:

                row.update(
                    self._payload or {}
                )


            return FakeResult(
                matched
            )



        # -----------------------------
        # UPSERT
        # -----------------------------

        if self._op == "upsert":

            payload = self._payload or {}


            conflict_keys: list[str] = []


            if self._conflict:

                conflict_keys = [
                    key.strip()
                    for key
                    in self._conflict.split(",")
                ]



            existing = None


            if conflict_keys:

                existing = next(
                    (
                        row
                        for row
                        in rows
                        if all(
                            row.get(key)
                            ==
                            payload.get(key)

                            for key
                            in conflict_keys
                        )
                    ),
                    None,
                )



            if existing:

                existing.update(
                    payload
                )

                return FakeResult(
                    [existing]
                )



            row = dict(
                payload
            )


            row.setdefault(
                "id",
                str(uuid.uuid4()),
            )


            rows.append(row)


            return FakeResult(
                [row]
            )



        return FakeResult([])




# ---------------------------------------------------------
# Fake Database
# ---------------------------------------------------------

class FakeDB:
    """
    In-memory Supabase replacement.
    """

    def __init__(self):

        self.tables: dict[
            str,
            list[dict]
        ] = {}



    def table(
        self,
        name: str,
    ) -> FakeQuery:

        return FakeQuery(
            self.tables,
            name,
        )



    def seed(
        self,
        table_name: str,
        row: dict,
    ) -> dict:

        row = dict(row)

        row.setdefault(
            "id",
            str(uuid.uuid4()),
        )

        self.tables.setdefault(
            table_name,
            [],
        ).append(row)

        return row



# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------

@pytest.fixture
def fake_db():

    return FakeDB()



@pytest.fixture
def supabase_client(
    fake_db: FakeDB,
):

    return fake_db



@pytest.fixture
def client(
    fake_db,
    monkeypatch,
):

    from app.routes import candidate_intake


    async def _fake_get_db():

        return fake_db



    monkeypatch.setattr(
        candidate_intake,
        "get_db",
        _fake_get_db,
    )



    app = FastAPI()


    app.include_router(
        candidate_intake.router
    )


    return TestClient(app)
