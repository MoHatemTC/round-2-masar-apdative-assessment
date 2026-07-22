"""
Selection service for the Adaptive Assessment Engine.
Connects to Supabase to fetch questions while ensuring no repetitions.
"""
from supabase import AsyncClient
import random
from typing import List, Optional, Dict, Any

async def select_competency_question(
    supabase: AsyncClient, 
    competency: str, 
    sub_ids: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Fetches a baseline question for the current competency from the question bank.
    Ensures that any question ID present in `sub_ids` is never returned[cite: 1].
    
    Args:
        supabase: The async Supabase client instance.
        competency: The competency to query.
        sub_ids: List of question IDs already asked in the current session.
        
    Returns:
        A dictionary representing the question payload, or None if the bank is exhausted.
    """
    # Build the base query for the given competency
    query = supabase.table("question_bank").select("*").eq("competency", competency)
    
    # Execute the query using the async client
    response = await query.execute()
    
    if not response.data:
        return None
        
    # Filter out any questions that have already been asked to guarantee no repeats
    # This is handled in Python memory to bypass PostgREST array syntax quirks for the baseline
    available_questions = [
        q for q in response.data 
        if str(q.get("id")) not in sub_ids
    ]
    
    if not available_questions:
        return None
        
    # Baseline selection: randomly select an unasked question
    selected_question = random.choice(available_questions)
    
    return selected_question