"""
FastAPI router for handling adaptive chat evaluation sessions.
Manages transport, session lookup, state-scrubbing, and persistence.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from supabase import AsyncClient

# Dependency injection for the async database client
from app.db import get_supabase_client 
from app.agent.orchestration import run_turn
from app.agent.state import AgentStateModel

# Initialize the router for chat-related endpoints
router = APIRouter(prefix="/chat", tags=["chat"])

class TurnRequest(BaseModel):
    # The unique UUID string tracking the candidate session
    session_id: str = Field(...)
    # The graded text or option selection answer from the candidate
    user_input: Optional[str] = Field(default=None)

class TurnResponse(BaseModel):
    # The synchronized session tracking state
    agent_state: Dict[str, Any] = Field(...)
    # The next generated question dictionary asset
    question: Optional[Dict[str, Any]] = Field(default=None)

@router.post("/turn", response_model=TurnResponse, status_code=status.HTTP_200_OK)
async def post_chat_turn(
    payload: TurnRequest,
    supabase: AsyncClient = Depends(get_supabase_client)
):
    """
    Processes a single evaluation turn for the adaptive assessment.
    Loads the session, runs the orchestration logic, strips transient keys, 
    and persists the updated state.
    """
    session_id = payload.session_id

    # 1. Fetch the existing session state from the Supabase 'sessions' table
    db_response = await supabase.table("sessions").select("agent_state").eq("id", session_id).maybe_single().execute()
    
    # 2. If the session is uninitialized or missing data, start with an empty state dictionary
    if not db_response or not db_response.data:
        raw_current_state = {}
    else:
        raw_current_state = db_response.data.get("agent_state", {})

    try:
        # 3. Pass the current state to the core orchestration wrapper to execute the turn logic
        updated_state_dict, question = await run_turn(
            agent_state=raw_current_state,
            supabase=supabase
        )
        
        # 4. Load the updated state into the Pydantic model to validate and strip out transient '_' keys
        state_validator = AgentStateModel(**updated_state_dict)
        clean_persistent_state = state_validator.to_persistent_dict()
        
        # 5. Persist the sanitized, updated state back to the database
        await supabase.table("sessions").update({"agent_state": clean_persistent_state}).eq("id", session_id).execute()
        
        # 6. Return the clean state and the new question payload to the frontend
        return TurnResponse(
            agent_state=clean_persistent_state,
            question=question
        )

    except Exception as e:
        # Catch and surface any internal orchestration or database errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )