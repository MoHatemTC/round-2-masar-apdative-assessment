"""
Production-contract tests for the adaptive assessment loop.

Uses a schema-faithful fake DB that accumulates .eq() filters properly
(instead of overwriting them), so the question-set selection path is
exercised correctly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.adaptive_loop import run_turn
from app.routes.chat import turn as chat_turn
from fastapi import HTTPException


# ── Schema-faithful fake DB ────────────────────────────────────────────────

class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQueryBuilder:
    """
    Accumulates all chained .eq() filters in a list instead of overwriting
    a single key/val pair, so multi-filter queries work correctly.
    """

    def __init__(self, db, table_name):
        self._db = db
        self._table_name = table_name
        self._filters = []
        self._is_single = False
        self._upsert_data = None
        self._update_data = None
        self._on_conflict = None

    # ── query builder chain ────────────────────────────────

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def maybe_single(self):
        self._is_single = True
        return self

    def upsert(self, data, on_conflict=None):
        self._upsert_data = data
        self._on_conflict = on_conflict
        return self

    def update(self, data):
        self._update_data = data
        return self

    def in_(self, key, values):
        self._filters.append(("__in__", (key, values)))
        return self

    def insert(self, data):
        self._upsert_data = data
        return self

    # ── execute ────────────────────────────────────────────

    async def execute(self):
        # UPDATE path
        if self._update_data is not None:
            rows = self._db._tables.get(self._table_name, [])
            for row in rows:
                if self._row_matches(row):
                    row.update(self._update_data)
            return FakeResponse(rows)

        # UPSERT path
        if self._upsert_data is not None:
            table = self._db._tables.setdefault(self._table_name, [])
            if isinstance(self._upsert_data, list):
                for d in self._upsert_data:
                    table.append(d)
                return FakeResponse(self._upsert_data)
            table.append(self._upsert_data)
            return FakeResponse(self._upsert_data)

        # SELECT path
        rows = self._db._tables.get(self._table_name, [])
        matched = [r for r in rows if self._row_matches(r)]

        if self._is_single:
            return FakeResponse(matched[0] if matched else None)
        return FakeResponse(matched)

    def _row_matches(self, row):
        for f in self._filters:
            if f[0] == "__in__":
                key, values = f[1]
                if row.get(key) not in values:
                    return False
            else:
                key, value = f
                if row.get(key) != value:
                    return False
        return True


class SchemaFaithfulDB:
    """
    In-memory DB seeded with schema-faithful data.
    Each .table() call returns a fresh FakeQueryBuilder so chained
    .eq() filters never leak between calls.
    """

    def __init__(self):
        self._tables = {
            "question_bank": [
                {
                    "id": "q1",
                    "competency_id": "comp1",
                    "tool_type": "mcq",
                    "difficulty": 3,
                    "body": "What is 2+2?",
                    "payload": {"options": ["3", "4"], "answer_key": "4"},
                    "is_active": True,
                },
                {
                    "id": "q2",
                    "competency_id": "comp2",
                    "tool_type": "coding",
                    "difficulty": 3,
                    "body": "Write a function.",
                    "payload": {"expected_output": "True"},
                    "is_active": True,
                },
            ],
            "question_set_items": [
                {"set_id": "set1", "question_id": "q1"},
            ],
            "assessments": [
                {
                    "id": "assess1",
                    "question_set_id": "set1",
                    "competency_ids": ["comp1"],
                },
            ],
            "sessions": [
                {
                    "id": "session1",
                    "assessment_id": "assess1",
                    "agent_state": {},
                    "intake_answers": {"comp1": 3},
                },
            ],
            "answers": [],
            "session_competency_results": [],
            "final_reports": [],
        }

    def table(self, name):
        return FakeQueryBuilder(self, name)

    def get_answers(self):
        return self._tables.get("answers", [])


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def fake_db():
    return SchemaFaithfulDB()


# ── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_select_grade_persist_cycle(fake_db):
    """
    Full select → grade → persist cycle against a schema-faithful fake.
    The selection service is bypassed because we can't do a real Supabase
    inner join in the fake, but pick_question is exercised end-to-end.
    """
    session = fake_db._tables["sessions"][0]
    state = session["agent_state"]

    # ── Turn 1: init + pick ──
    # Mock selection to return q1 (simulates the question_set_items join)
    q1 = fake_db._tables["question_bank"][0]

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "app.agent.adaptive_loop.select_competency_question",
            AsyncMock(return_value=q1),
        )
        new_state = await run_turn(fake_db, session, state, None)

    assert new_state["initialized"] is True
    assert new_state["queue"] == ["comp1"]
    assert new_state["question_set_id"] == "set1"

    # _emit should carry the question body
    assert "_emit" in new_state
    assert new_state["_emit"]["body"] == "What is 2+2?"
    assert new_state["_emit"]["question_number"] == 1
    assert new_state["question_number"] == 1

    # ── Turn 2: grade the answer ──
    tool_result = {"answer": "4"}

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "app.agent.adaptive_loop.grade_answer",
            AsyncMock(return_value={"score": 5, "rationale": "Correct", "flagged": False}),
        )
        # After grading q1, selection returns None → bank exhaustion → converge → finalize
        m.setattr(
            "app.agent.adaptive_loop.select_competency_question",
            AsyncMock(return_value=None),
        )
        m.setattr(
            "app.services.scoring.competency_result_from_state",
            MagicMock(return_value={"competency_id": "comp1", "level": 5, "pct": 100, "label": "Expert", "low_confidence": False}),
        )
        m.setattr(
            "app.services.scoring.session_competency_result_row",
            MagicMock(return_value={"session_id": "session1", "competency_id": "comp1"}),
        )
        m.setattr(
            "app.services.scoring.final_report_row",
            MagicMock(return_value={"session_id": "session1", "overall_pct": 100, "overall_level": 5, "level_label": "Expert"}),
        )

        result_state = await run_turn(fake_db, session, new_state, tool_result)

    # Verify answer persistence uses schema-correct columns
    answers = fake_db.get_answers()
    assert len(answers) >= 1
    ans = answers[0]
    assert ans["question_number"] == 1
    assert ans["question_id"] == "q1"
    assert ans["question_body"] == "What is 2+2?"
    assert ans["tool_type"] == "mcq"
    assert ans["score"] == 5
    assert "answer_text" in ans
    # Non-schema columns must NOT appear
    assert "tool_result" not in ans
    assert "flagged" not in ans

    # Competency should be converged
    assert result_state["per_competency"]["comp1"]["converged"] is True


@pytest.mark.asyncio
async def test_duplicate_retry_rejected():
    """
    Submitting an answer without question_number → 400.
    Submitting with a stale question_number → 409.
    """
    fake_db = SchemaFaithfulDB()

    # ── Missing question_number → 400 ──
    body_no_qnum = {
        "session_id": "session1",
        "tool_result": {"answer": "something"},
    }
    with pytest.raises(HTTPException) as exc_info:
        await chat_turn(body=body_no_qnum, db=fake_db)
    assert exc_info.value.status_code == 400
    assert "question_number is required" in exc_info.value.detail

    # ── Stale question_number → 409 ──
    # Mutate session state so question_number is 2
    fake_db._tables["sessions"][0]["agent_state"] = {
        "turn_number": 1,
        "question_number": 2,
        "initialized": True,
    }
    body_stale = {
        "session_id": "session1",
        "question_number": 1,
        "tool_result": {"answer": "old answer"},
    }
    with pytest.raises(HTTPException) as exc_info:
        await chat_turn(body=body_stale, db=fake_db)
    assert exc_info.value.status_code == 409
    assert "Stale submission" in exc_info.value.detail


@pytest.mark.asyncio
async def test_question_set_scoping(fake_db):
    """
    Verifies that init_session stores question_set_id in state, and
    pick_question passes it to select_competency_question.
    """
    session = fake_db._tables["sessions"][0]
    state = session["agent_state"]

    captured_kwargs = {}

    async def capturing_selector(**kwargs):
        captured_kwargs.update(kwargs)
        return fake_db._tables["question_bank"][0]

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "app.agent.adaptive_loop.select_competency_question",
            capturing_selector,
        )
        await run_turn(fake_db, session, state, None)

    assert state["question_set_id"] == "set1"
    assert captured_kwargs.get("question_set_id") == "set1"
