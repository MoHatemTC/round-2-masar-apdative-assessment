"""
Sandbox endpoint.

Not mounted in production until the project has real
authentication/session protection because this endpoint
creates paid E2B sandboxes.
"""

from __future__ import annotations

import asyncio

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.services.sandbox import run_code
from app.services.sandbox_validation import (
    SandboxRequest,
    validate_sandbox_request,
)

router = APIRouter(tags=["sandbox"])

# ----------------------------
# Limits
# ----------------------------

OVERALL_TIMEOUT = 20            # seconds


SandboxRunRequest = SandboxRequest


@router.post("/sandbox/run")
async def sandbox_run(req: SandboxRunRequest):
    """
    Execute candidate code inside E2B.
    """

    validate_sandbox_request(req)

    try:
        result = await asyncio.wait_for(
            run_code(
                language=req.language,
                code=req.code,
                test_cases=req.test_cases,
            ),
            timeout=OVERALL_TIMEOUT,
        )

        return result

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Sandbox execution timed out.",
        )