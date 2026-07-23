"""
Selection service for the Adaptive Assessment Engine.

Connects to Supabase to retrieve competency questions while ensuring:
- No question is repeated within the current interview session.
- Question difficulty is aligned with the candidate's current estimate.
- Tool types are balanced to improve assessment variety.
"""
from supabase import AsyncClient
import random
from typing import List, Optional, Dict, Any

async def select_competency_question(
    supabase: AsyncClient,
    competency: str,
    sub_ids: List[str],
    current_estimate: float = 3.0,
    tool_type_counts: Dict[str, int] = None,
    question_set_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Selects the next competency question using adaptive difficulty and
    tool-type balancing.

    The selection process follows these steps:
        1. Retrieve all questions for the requested competency.
        2. Remove questions already asked during this interview.
        3. Match questions to the candidate's estimated difficulty.
        4. Balance tool types by preferring those used least frequently.
        5. Randomly select one question from the qualified candidates.

    Args:
        supabase:
            Async Supabase client instance.

        competency:
            Competency currently being assessed.

        sub_ids:
            List of question IDs already asked during this interview.

        current_estimate:
            Current estimated competency level used to match question
            difficulty. Defaults to 3.0 (medium).

        tool_type_counts:
            Dictionary tracking how many questions have already been asked
            from each tool type.

    Returns:
        A question dictionary if one is available, otherwise None.
    """

    # Initialize tool-type tracking
    # Create an empty tracking dictionary if one was not provided.
    if tool_type_counts is None:
        tool_type_counts = {}

    # Retrieve questions for the requested competency
    if question_set_id:
        query = (
            supabase.table("question_bank")
            .select("*, question_set_items!inner(set_id)")
            .eq("competency_id", competency)
            .eq("question_set_items.set_id", question_set_id)
        )
    else:
        query = (
            supabase.table("question_bank")
            .select("*")
            .eq("competency_id", competency)
        )

    response = await query.execute()

    # No questions exist for this competency.
    if not response.data:
        return None

    # Remove questions that have already been asked
    # Prevent duplicate questions within the same interview session.
    available_questions = [
        question
        for question in response.data
        if str(question.get("id")) not in sub_ids
    ]

    # Every question has already been used.
    if not available_questions:
        return None

    # Match candidate ability to question difficulty
    # Round the candidate estimate to the nearest integer difficulty level.
    target_difficulty = round(current_estimate)

    difficulty_matched_questions = []

    for question in available_questions:

        # Default to medium difficulty if the value is missing or invalid.
        difficulty = 3
        raw_difficulty = question.get("difficulty")

        # Handle text-based difficulty values.
        if isinstance(raw_difficulty, str):
            difficulty_text = raw_difficulty.lower()

            if difficulty_text == "easy":
                difficulty = 2
            elif difficulty_text == "medium":
                difficulty = 3
            elif difficulty_text == "hard":
                difficulty = 4
            else:
                try:
                    difficulty = int(difficulty_text)
                except ValueError:
                    difficulty = 3

        # Handle numeric difficulty values.
        elif isinstance(raw_difficulty, (int, float)):
            difficulty = round(raw_difficulty)

        # Keep only questions matching the target difficulty.
        if difficulty == target_difficulty:
            difficulty_matched_questions.append(question)

    # If no exact difficulty match exists, use every remaining question.
    question_pool = (
        difficulty_matched_questions
        if difficulty_matched_questions
        else available_questions
    )

    # Balance tool-type distribution
    # Prioritize tool types that have been used the fewest times.
    question_pool.sort(
        key=lambda question: tool_type_counts.get(
            question.get("tool_type", ""),
            0,
        )
    )

    lowest_usage = tool_type_counts.get(
        question_pool[0].get("tool_type", ""),
        0,
    )

    # Keep only questions belonging to the least-used tool types.
    candidate_questions = [
        question
        for question in question_pool
        if tool_type_counts.get(question.get("tool_type", ""), 0)
        == lowest_usage
    ]


    # Final selection
    # Randomly choose one qualified question to avoid deterministic ordering.
    return random.choice(candidate_questions)