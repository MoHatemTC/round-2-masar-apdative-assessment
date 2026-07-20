"""
Orchestration layer for the Adaptive Assessment Engine.
Manages the turn-based execution and state-updating lifecycle.
"""
from typing import Dict, Any, Tuple, Optional
from supabase import AsyncClient
from app.agent.state import AgentStateModel
from app.services.selection import select_competency_question

async def run_turn(
    agent_state: dict, 
    supabase: AsyncClient,
    fallback_competency: str = "Python-Backend"
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Executes a single evaluation turn on an incoming state dictionary.
    
    Args:
        agent_state: Raw dictionary representing the session memory.
        supabase: The active async Supabase database client.
        fallback_competency: Initial competency to choose if state is uninitialized.
        
    Returns:
        A tuple of (updated_agent_state_dict, selected_question_dict or None)
    """
    # 1. Load the dictionary into our Pydantic validation model
    state = AgentStateModel(**agent_state)
    
    # 2. Check for initialization (Turn 1 scaffold)
    if not state.current_competency:
        state.current_competency = fallback_competency
        state.turn_number = 0
        state.sub_ids = []
    
    # 3. Call the question selector service to get an unasked question
    question = await select_competency_question(
        supabase=supabase,
        competency=state.current_competency,
        sub_ids=state.sub_ids
    )
    
    # 4. If a question was successfully picked, update the session tracking parameters
    if question:
        question_id = str(question.get("id"))
        state.sub_ids.append(question_id)
        state.turn_number += 1
        
        # Inject an internal transient key to simulate internal runtime variables
        # Our Pydantic model allows extra fields; we add this to verify database stripping logic later
        setattr(state, "_transient_execution_timestamp", "2026-07-19T17:23:00Z")
    
    # Return the state as a mutable dictionary along with the question payload
    # Note: We return the complete dictionary (with the transient key intact) because 
    # the stripping action explicitly happens at the API route persistence border
    return state.model_dump(), question