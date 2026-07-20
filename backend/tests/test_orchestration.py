"""
Unit tests for the orchestration layer wrapper.
These tests verify that the session state initializes correctly and that 
transient variables (starting with '_') are safely removed.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.orchestration import run_turn
from app.agent.state import AgentStateModel

@pytest.mark.asyncio
async def test_run_turn_initialization():
    """
    Assert that passing an empty state dictionary initializes the required turn tracking values.
    """
    # 1. Define the fake question payload that the database "returns"
    mock_question = {"id": "999", "competency": "Python-Backend", "body": "What is FastAPI?"}
    
    # 2. Mock the final execution response of the database query
    mock_execute = MagicMock()
    mock_execute.data = [mock_question]
    
    # 3. Mock the query builder chain
    # The actual code calls: supabase.table().select().eq().execute()
    mock_query = MagicMock()
    # .select() returns the query object itself to allow chaining
    mock_query.select = MagicMock(return_value=mock_query)
    # .eq() also returns the query object
    mock_query.eq = MagicMock(return_value=mock_query)
    # .execute() is the final call, and because it is 'await'ed, it MUST be an AsyncMock
    mock_query.execute = AsyncMock(return_value=mock_execute)
    
    # 4. Mock the Supabase client base
    mock_supabase = MagicMock()
    # .table() returns the query chain we built above
    mock_supabase.table = MagicMock(return_value=mock_query)
    
    # 5. Invoke the function with a completely blank state
    empty_state = {}
    updated_state, question = await run_turn(empty_state, mock_supabase)
    
    # 6. Verify that the system initialized the state and picked the mocked question
    assert question is not None
    assert updated_state["current_competency"] == "Python-Backend"
    assert updated_state["turn_number"] == 1
    # Verify the question's ID was added to the exclusion list
    assert "999" in updated_state["sub_ids"]

def test_transient_variable_stripping():
    """
    Assert that the Pydantic v2 state wrapper safely drops any keys starting with an underscore.
    """
    # Create a raw state containing both persistent data and temporary runtime data
    raw_state = {
        "current_competency": "Python-Backend",
        "sub_ids": ["1"],
        "turn_number": 1,
        "_transient_execution_timestamp": "2026-07-19T17:23:00Z", # Should be stripped
        "_db_connection_pool_link": "0xDEADBEEF"                  # Should be stripped
    }
    
    # Pass the raw dictionary through our Pydantic model
    state_validator = AgentStateModel(**raw_state)
    # Extract the clean dictionary using our custom helper method
    clean_dict = state_validator.to_persistent_dict()
    
    # Persistent keys must be preserved exactly as they were
    assert clean_dict["current_competency"] == "Python-Backend"
    assert clean_dict["turn_number"] == 1
    
    # Transient underscore keys must be completely removed
    assert "_transient_execution_timestamp" not in clean_dict
    assert "_db_connection_pool_link" not in clean_dict