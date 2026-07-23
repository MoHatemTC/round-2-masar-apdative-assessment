import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.adaptive_loop import run_turn, init_session, pick_question, grade
from app.routes.chat import turn as chat_turn
from fastapi import HTTPException
from app.services.selection import select_competency_question

class SchemaFaithfulFakeDB:
    def __init__(self):
        self.question_bank = [
            {
                "id": "q1",
                "competency_id": "comp1",
                "tool_type": "mcq",
                "difficulty": 3,
                "body": "What is 2+2?",
                "payload": {"options": ["3", "4"], "answer_key": "4"}
            },
            {
                "id": "q2",
                "competency_id": "comp2",
                "tool_type": "coding",
                "difficulty": 3,
                "body": "Write a function.",
                "payload": {"expected_output": "True"}
            }
        ]
        self.question_set_items = [
            {"set_id": "set1", "question_id": "q1"}
        ]
        self.assessments = [
            {"id": "assess1", "question_set_id": "set1", "competency_ids": ["comp1"]}
        ]
        self.sessions = [
            {"id": "session1", "assessment_id": "assess1", "agent_state": {}, "intake_answers": {"comp1": 3}}
        ]
        self.answers = []
        
        self.current_table = None

    def table(self, name):
        self.current_table = name
        return self

    def select(self, *args):
        return self

    def eq(self, key, value):
        self.filter_key = key
        self.filter_val = value
        return self

    def maybe_single(self):
        self.single = True
        return self

    def upsert(self, data, on_conflict=None):
        self.upsert_data = data
        return self
        
    def update(self, data):
        self.update_data = data
        return self

    async def execute(self):
        class Response:
            pass
        res = Response()
        
        if hasattr(self, "update_data") and self.update_data is not None:
            if self.current_table == "sessions":
                for s in self.sessions:
                    if s["id"] == self.filter_val:
                        s.update(self.update_data)
                res.data = self.sessions
            self.update_data = None
            return res

        if hasattr(self, "upsert_data") and self.upsert_data is not None:
            if self.current_table == "answers":
                self.answers.append(self.upsert_data)
                res.data = self.upsert_data
            self.upsert_data = None
            return res

        res.data = []
        if self.current_table == "assessments":
            for a in self.assessments:
                if a["id"] == self.filter_val:
                    res.data = a if getattr(self, "single", False) else [a]
        elif self.current_table == "sessions":
            for s in self.sessions:
                if s["id"] == self.filter_val:
                    res.data = s if getattr(self, "single", False) else [s]
        elif self.current_table == "question_bank":
            res.data = [q for q in self.question_bank if q["competency_id"] == self.filter_val]
            if hasattr(self, "filter_val"):
                res.data = [q for q in res.data if any(i["question_id"] == q["id"] and i["set_id"] == "set1" for i in self.question_set_items)]
                
        self.single = False
        self.filter_key = None
        self.filter_val = None
        return res

@pytest.fixture
def fake_db():
    return SchemaFaithfulFakeDB()

@pytest.mark.asyncio
async def test_select_grade_persist_cycle(fake_db):
    session = fake_db.sessions[0]
    state = session["agent_state"]
    
    new_state = await run_turn(fake_db, session, state, None)
    
    assert new_state["initialized"] is True
    assert "queue" in new_state
    assert new_state["queue"] == ["comp1"]
    
    assert "_emit" in new_state
    assert new_state["_emit"]["body"] == "What is 2+2?"
    assert new_state["question_number"] == 1
    
    tool_result = {"answer": "4"}
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.agent.adaptive_loop.grade_answer", AsyncMock(return_value={"score": 5, "rationale": "Correct", "flagged": False}))
        
        state_after_turn_1 = new_state.copy()
        result_state = await run_turn(fake_db, session, state_after_turn_1, tool_result)
        
        assert len(fake_db.answers) == 1
        ans = fake_db.answers[0]
        assert ans["question_number"] == 1
        assert ans["question_id"] == "q1"
        assert ans["score"] == 5
        assert "tool_result" not in ans
        assert "answer_text" in ans
        
        assert result_state["per_competency"]["comp1"]["converged"] is True
        
@pytest.mark.asyncio
async def test_duplicate_retry_rejection(fake_db):
    session = fake_db.sessions[0]
    session["agent_state"] = {"turn_number": 1, "question_number": 2, "initialized": True}
    
    body = {
        "session_id": "session1",
        "question_number": 1,
        "tool_result": {"answer": "old answer"}
    }
    
    with pytest.raises(HTTPException) as excinfo:
        await chat_turn(body=body, db=fake_db)
        
    assert excinfo.value.status_code == 409
    assert "Stale submission" in excinfo.value.detail
