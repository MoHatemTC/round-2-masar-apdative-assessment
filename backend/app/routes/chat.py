"""
Candidate API: start a session, submit intake, and run one adaptive turn.
"""
from __future__ import annotations
from fastapi import APIRouter, Body, Depends, HTTPException, status
from supabase import AsyncClient
from datetime import datetime, timedelta, timezone
# Dependency injection for the async database client
from app.db import get_db
from app.agent import adaptive_loop

router = APIRouter(tags=["candidate"])

'''
@router.post("/session/start")
async def start_session(body: dict = Body(...)):
    """Create a session for {assessment_id, candidate_name, candidate_email, cv_json?}.
    TODO: insert into `sessions`; return {session_id}."""
    raise NotImplementedError


@router.post("/session/{session_id}/intake")
async def submit_intake(session_id: str, body: dict = Body(...)):
    """Save the candidate's 1–5 self-ratings (and any CV) before the loop starts.
    TODO: update sessions.intake_answers / cv_json. Store self-ratings keyed by competency id."""
    raise NotImplementedError
'''
@router.post("/session/{session_id}/answer-timer/start")
async def start_answer_timer(
    session_id: str,
    body: dict = Body(...),
    db: AsyncClient = Depends(get_db),
):
    """Server-authoritative start of the per-question answer clock. Idempotent per
    question_number, so a refresh or repeated click never grants extra time — and the time
    limit is always read from the question's own payload server-side, never trusted from the
    client."""
    question_number = body.get("question_number")
    if question_number is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_number is required")

    response = await db.table("sessions").select("*").eq("id", session_id).maybe_single().execute()
    if not response or not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session = response.data
    state = session.get("agent_state") or {}

    if state.get("question_number") != question_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is not the current active question.",
        )

    current_question = state.get("current_question") or {}
    time_limit_seconds = (current_question.get("payload") or {}).get("time_limit_seconds", 120)

    if state.get("answer_timer_question_number") == question_number and state.get("answer_started_at"):
        # Already started for this exact question — return the original deadline unchanged.
        started_at = datetime.fromisoformat(state["answer_started_at"])
    else:
        started_at = datetime.now(timezone.utc)
        state["answer_started_at"] = started_at.isoformat()
        state["answer_timer_question_number"] = question_number
        await db.table("sessions").update({"agent_state": state}).eq("id", session_id).execute()

    deadline = started_at + timedelta(seconds=time_limit_seconds)
    return {
        "deadline_at_ms": int(deadline.timestamp() * 1000),
        "time_limit_seconds": time_limit_seconds,
    }


@router.post("/chat/turn")
async def turn(
    body: dict = Body(...),
    db: AsyncClient = Depends(get_db)
):
    """
    Executes one adaptive turn for the candidate.
    Expects a JSON body containing 'session_id' and optionally 'tool_result' (the candidate's answer).
    """
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="session_id is required"
        )

    # 1. Fetch the existing session data and state from the Supabase 'sessions' table
    response = await db.table("sessions").select("*").eq("id", session_id).maybe_single().execute()
    
    # Ensure the session actually exists in the database
    if not response or not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Session not found"
        )
        
    session = response.data
    state = session.get("agent_state") or {}

    # Server-enforced time limit — never trust a client-sent countdown.
    seconds_left = None
    if session.get("started_at"):
        assess_resp = await db.table("assessments").select("time_limit_min").eq("id", session["assessment_id"]).maybe_single().execute()
        time_limit_min = (assess_resp.data or {}).get("time_limit_min")
        if time_limit_min:
            started_at = datetime.fromisoformat(session["started_at"])
            deadline = started_at + timedelta(minutes=time_limit_min)
            seconds_left = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))

            if seconds_left <= 0 and body.get("tool_result") is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Time limit for this assessment has expired.",
                
                )
    # Extract the current state dictionary, defaulting to an empty dict if uninitialized
    state = session.get("agent_state") or {}

    # Infinite Loop Protection
    # Prevent a broken session from looping forever and racking up LLM costs
    turn_count = state.get("turn_number", 0) + 1
    if turn_count > 100:  
        raise HTTPException(status_code=400, detail="Maximum session turns exceeded.")
    state["turn_number"] = turn_count
    
    # Idempotency / Stale submission guard
    tool_result = body.get("tool_result")
    if tool_result is not None:
        req_qnum = body.get("question_number")
        state_qnum = state.get("question_number")
        # question_number is mandatory for every answer submission
        if req_qnum is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_number is required when submitting an answer"
            )
        if state_qnum is not None and req_qnum != state_qnum:
            # The client is answering a question we already graded or moved past.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stale submission or duplicate request"
            )
        # Per-question deadline — re-derived server-side, never trusted from the client.
    if state.get("answer_timer_question_number") == state_qnum and state.get("answer_started_at"):
     current_question = state.get("current_question") or {}
     q_time_limit = (current_question.get("payload") or {}).get("time_limit_seconds", 120)
     started_at = datetime.fromisoformat(state["answer_started_at"])
     q_deadline = started_at + timedelta(seconds=q_time_limit)

    if datetime.now(timezone.utc) > q_deadline:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Time limit for this question has expired.",
        )
    try:
        # 2. Execute the adaptive loop logic, passing the current state and any user tool_result
        new_state = await adaptive_loop.run_turn(
            db, 
            session, 
            state, 
            body.get("tool_result")
        )
        
        # 3. Sanitize the state by stripping out any internal keys prefixed with an underscore '_'
        # This prevents transient execution metrics from polluting the persistent database
        clean_state = {k: v for k, v in new_state.items() if not k.startswith("_")}
        
        # Persist the sanitized state back to the 'sessions' table
        await db.table("sessions").update({"agent_state": clean_state}).eq("id", session_id).execute()
        
        # 4. Return the next action to the frontend, pulling the transient emit/complete flags 
        # directly from the pre-sanitized state object
        return {
            "emit": new_state.get("_emit"),
            "complete": new_state.get("_complete", False),
            "seconds_left": seconds_left,
        }
    except Exception as e:
        # Catch internal processing errors and bubble them up cleanly
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )