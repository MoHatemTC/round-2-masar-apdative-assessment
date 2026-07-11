"""Candidate API: start a session, submit intake, and run one adaptive turn.  [TODO]"""
from __future__ import annotations
from fastapi import APIRouter, Body

# from app.db import get_db
from app.agent import adaptive_loop

router = APIRouter(tags=["candidate"])


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


@router.post("/chat/turn")
async def turn(body: dict = Body(...)):
    """One adaptive turn. Body: {session_id, tool_result?} (tool_result present = an answer).
    TODO:
      1. Load the session row (with agent_state).
      2. state = session['agent_state']; new_state = await adaptive_loop.run_turn(db, session, state,
             body.get('tool_result'))
      3. Persist new_state back to sessions.agent_state (strip transient _-prefixed keys first).
      4. Return {emit: new_state.get('_emit'), complete: new_state.get('_complete', False)}.
    """
    raise NotImplementedError
