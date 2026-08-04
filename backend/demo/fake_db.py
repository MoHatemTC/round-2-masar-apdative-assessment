"""In-memory stand-in for the real Supabase-backed app.db module.

This exists ONLY so the real app/routes/transcribe.py, app/services/grading.py,
and app/services/llm.py can run completely unmodified against something that
behaves like a real Postgres/Supabase client — chainable filters, an insert
that enforces a unique constraint the same way Postgres would, and a storage
bucket. None of the actual voice-answer business logic lives here.
"""
from __future__ import annotations

import asyncio
import uuid


class UniqueViolation(Exception):
    pass


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, store: dict, name: str):
        self._store = store
        self._name = name
        self._filters: list[tuple[str, object]] = []
        self._mode: str | None = None
        self._insert_rows: list[dict] | None = None
        self._update_values: dict | None = None
        self._single = False

    def select(self, cols="*"):
        self._mode = "select"
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def insert(self, row):
        self._mode = "insert"
        self._insert_rows = [row] if isinstance(row, dict) else list(row)
        return self

    def update(self, values):
        self._mode = "update"
        self._update_values = values
        return self

    def maybe_single(self):
        self._single = True
        return self

    def _rows(self):
        return self._store.setdefault(self._name, [])

    def _matches(self, row):
        return all(row.get(col) == val for col, val in self._filters)

    async def execute(self):
        # Artificial network round-trip, same idea as a real DB call taking
        # non-zero time — this is what lets two concurrent requests actually
        # interleave in the demo instead of running back-to-back on a single
        # event loop with no yield points.
        await asyncio.sleep(0.02)

        # No further `await` before the constraint check below — this models
        # a real unique index, which enforces atomically once the DB actually
        # performs the write, regardless of how callers got interleaved
        # before that point.
        rows = self._rows()

        if self._mode == "insert":
            inserted = []
            for row in self._insert_rows:
                if self._name == "answers":
                    for existing in rows:
                        if (existing.get("session_id"), existing.get("question_number")) == (
                            row.get("session_id"),
                            row.get("question_number"),
                        ):
                            raise UniqueViolation(
                                "duplicate key value violates unique constraint "
                                "\"answers_session_question_uniq\""
                            )
                new_row = {"id": str(uuid.uuid4()), **row}
                rows.append(new_row)
                inserted.append(new_row)
            return FakeResult(inserted)

        if self._mode == "update":
            matched = [r for r in rows if self._matches(r)]
            for r in matched:
                r.update(self._update_values)
            return FakeResult(matched)

        # select
        matched = [r for r in rows if self._matches(r)]
        if self._single:
            return FakeResult(matched[0] if matched else None)
        return FakeResult(matched)


class FakeBucket:
    def __init__(self, files: dict, bucket: str):
        self._files = files
        self._bucket = bucket

    async def upload(self, path, raw_bytes, options=None):
        # Small artificial round-trip so concurrent requests genuinely overlap here.
        await asyncio.sleep(0.01)
        self._files[f"{self._bucket}/{path}"] = raw_bytes
        return {"path": path}


class FakeStorage:
    def __init__(self, files: dict):
        self._files = files

    def from_(self, bucket):
        return FakeBucket(self._files, bucket)


class FakeDB:
    def __init__(self):
        self._tables: dict[str, list[dict]] = {}
        self._files: dict[str, bytes] = {}
        self.storage = FakeStorage(self._files)

    def table(self, name):
        return FakeQuery(self._tables, name)

    def seed(self, name, rows):
        self._tables[name] = list(rows)

    def dump(self, name):
        return self._tables.get(name, [])


_singleton = FakeDB()


async def get_db():
    return _singleton


def reset():
    """Fresh DB between demo scenarios."""
    global _singleton
    _singleton = FakeDB()
    return _singleton
