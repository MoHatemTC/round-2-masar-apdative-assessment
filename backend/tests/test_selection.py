"""
Unit tests for the question selection service.
These tests verify that the selection algorithm queries the database 
and correctly filters out questions the candidate has already seen.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.selection import select_competency_question

@pytest.mark.asyncio
async def test_select_competency_question_excludes_used_ids():
    """
    Assert that questions whose IDs are already in the `sub_ids` list are never returned, 
    satisfying the requirement to never repeat a question already served in the session[cite: 1].
    """
    # 1. Define a mock database returning three possible questions
    mock_questions = [
        {"id": "101", "competency": "Python-Backend", "body": "Q1"},
        {"id": "102", "competency": "Python-Backend", "body": "Q2"},
        {"id": "103", "competency": "Python-Backend", "body": "Q3"}
    ]
    
    # 2. Setup the Supabase mock chain (same pattern as orchestration tests)
    mock_execute = MagicMock()
    mock_execute.data = mock_questions
    
    mock_query = MagicMock()
    mock_query.select = MagicMock(return_value=mock_query)
    mock_query.eq = MagicMock(return_value=mock_query)
    mock_query.execute = AsyncMock(return_value=mock_execute)
    
    mock_supabase = MagicMock()
    mock_supabase.table = MagicMock(return_value=mock_query)
    
    # 3. Define the exclusion list: the candidate has already answered Q1 (101) and Q2 (102)
    used_sub_ids = ["101", "102"]
    
    # 4. Call the selection service
    selected = await select_competency_question(mock_supabase, "Python-Backend", used_sub_ids)
    
    # 5. Verify the engine correctly isolated and returned the only unasked question (Q3 / 103)
    assert selected is not None
    assert str(selected["id"]) == "103"

@pytest.mark.asyncio
async def test_select_competency_question_returns_none_when_exhausted():
    """
    Assert that the selection logic returns None if all available questions 
    for the competency have already been asked.
    """
    # 1. Define a mock database with only ONE question available
    mock_questions = [{"id": "101", "competency": "Python-Backend"}]
    
    # 2. Setup the Supabase mock chain
    mock_execute = MagicMock()
    mock_execute.data = mock_questions
    
    mock_query = MagicMock()
    mock_query.select = MagicMock(return_value=mock_query)
    mock_query.eq = MagicMock(return_value=mock_query)
    mock_query.execute = AsyncMock(return_value=mock_execute)
    
    mock_supabase = MagicMock()
    mock_supabase.table = MagicMock(return_value=mock_query)
    
    # 3. Define the exclusion list: the candidate has already answered that exact question
    used_sub_ids = ["101"]
    
    # 4. Call the selection service
    selected = await select_competency_question(mock_supabase, "Python-Backend", used_sub_ids)
    
    # 5. Verify the engine correctly returns None to signal the bank is empty
    assert selected is None