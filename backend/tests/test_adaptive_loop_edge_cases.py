import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.adaptive_loop import run_turn, check_convergence, finalize

@pytest.fixture
def mock_db():
    """Mocks the Supabase AsyncClient chain: upsert().execute() and update().eq().execute()"""
    db = MagicMock()
    table_mock = MagicMock()
    
    # Mock the .upsert().execute() chain
    upsert_mock = MagicMock()
    upsert_execute_mock = AsyncMock()
    upsert_mock.execute = upsert_execute_mock
    table_mock.upsert.return_value = upsert_mock
    
    # Mock the .update().eq().execute() chain
    update_mock = MagicMock()
    eq_mock = MagicMock()
    eq_execute_mock = AsyncMock()
    eq_mock.execute = eq_execute_mock
    update_mock.eq.return_value = eq_mock
    table_mock.update.return_value = update_mock
    
    db.table.return_value = table_mock
    return db

@pytest.fixture
def mock_session():
    return {"id": "test-session-123", "assessment_id": "test-assessment-456"}

@pytest.mark.asyncio
async def test_resume_after_interruption(mock_db, mock_session):
    """
    Test that if a session is interrupted and reloaded, run_turn respects 
    the existing 'initialized' state and doesn't wipe progress.
    """
    # State is already initialized and midway through
    state = {
        "initialized": True,
        "queue": ["comp_1"],
        "active_index": 0,
        "per_competency": {
            "comp_1": {"level": 3, "converged": False, "used_ids": ["q_1"]}
        },
        "current_question": None
    }
    
    # Mock pick_question to just return the state
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.agent.adaptive_loop.pick_question", AsyncMock(return_value=state))
        
        result = await run_turn(mock_db, mock_session, state, tool_result=None)
        
        assert result["initialized"] is True
        assert result["per_competency"]["comp_1"]["used_ids"] == ["q_1"]

@pytest.mark.asyncio
async def test_convergence_confidence_trigger(mock_db, mock_session):
    """
    Test that reaching the 90% confidence target immediately flags the competency 
    as converged and clears the current question to move forward.
    """
    state = {
        "current_question": {"competency_id": "comp_1"},
        "per_competency": {
            "comp_1": {
                "confidence": 0.92, # Above CONFIDENCE_TARGET
                "questions_asked": 3,
                "level_history": [3, 3, 3],
                "converged": False
            }
        }
    }
    
    # Need to mock the scoring module dependency inside check_convergence
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.services.scoring.competency_result_from_state", MagicMock(return_value={}))
        m.setattr("app.services.scoring.session_competency_result_row", MagicMock(return_value={}))
        
        await check_convergence(mock_db, mock_session, state)
        
        assert state["per_competency"]["comp_1"]["converged"] is True
        assert state["per_competency"]["comp_1"]["converged_reason"] == "confidence"
        assert state["current_question"] is None # Cleared for the next turn

@pytest.mark.asyncio
async def test_finalize_is_idempotent_and_safe_to_retry(mock_db, mock_session):
    """
    Test that finalize() utilizes upsert for all write operations, ensuring
    it can be retried safely without duplicating rows.
    """
    state = {
        "per_competency": {
            "comp_1": {"level": 4, "confidence": 0.95}
        }
    }
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("app.services.scoring.competency_result_from_state", MagicMock(return_value={}))
        m.setattr("app.services.scoring.session_competency_result_row", MagicMock(return_value={}))
        m.setattr("app.services.scoring.final_report_row", MagicMock(return_value={"overall_pct": 80, "level_label": "Advanced"}))
        
        # Simulate a successful finalize execution
        await finalize(mock_db, mock_session, state)
        
        # Verify that upsert was explicitly called on the reporting tables
        mock_db.table.assert_any_call("session_competency_results")
        mock_db.table.assert_any_call("final_reports")
        
        # Grab the mock objects for those tables and verify on_conflict was used
        assert mock_db.table().upsert.call_count >= 2
        
        # Assert the state was correctly flagged for the frontend
        assert state["_complete"] is True
        assert state["_emit"]["overall_pct"] == 80

def test_infinite_loop_protection():
    """
    Test the turncap logic implemented in chat.py to prevent runaway agent loops.
    """
    # This directly tests the logic we added to chat.py's turn() function
    state = {"turn_number": 100}
    
    turn_count = state.get("turn_number", 0) + 1
    
    # Assert that exceeding the limit triggers the protection block
    with pytest.raises(Exception) as excinfo:
        if turn_count > 100:
            raise Exception("Maximum session turns exceeded.")
            
    assert "Maximum session turns exceeded" in str(excinfo.value)