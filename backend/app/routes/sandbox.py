from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field

from app.services.sandbox import run_code

router = APIRouter(tags=["sandbox"])

# ----------------------------
# Limits
# ----------------------------

MAX_CODE_SIZE = 20_000          # chars
MAX_TEST_CASES = 5
MAX_INPUT_SIZE = 500            # chars
OVERALL_TIMEOUT = 20            # seconds


# -------------------------------------------------
# TODO:
# Replace this with your project's real auth
# dependency.
# -------------------------------------------------
async def require_authenticated_user():
    """
    Temporary placeholder.

    Replace with your project's authentication
    dependency before merging.
    """
    return {"id": "demo-user"}


class SandboxRunRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Literal["python"] = "python"
    test_cases: list[dict[str, Any]] = []


@router.post("/sandbox/run")
async def sandbox_run(
    req: SandboxRunRequest,
    user=Depends(require_authenticated_user),
):
    """
    Execute candidate code inside E2B.
    """

    # ----------------------------
    # Code size
    # ----------------------------
    if len(req.code) > MAX_CODE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Submitted code is too large.",
        )

    # ----------------------------
    # Test count
    # ----------------------------
    if len(req.test_cases) > MAX_TEST_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_TEST_CASES} test cases allowed.",
        )

    # ----------------------------
    # Input size
    # ----------------------------
    for tc in req.test_cases:

        if len(str(tc.get("input", ""))) > MAX_INPUT_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Test input exceeds size limit.",
            )

        if len(str(tc.get("expected_output", ""))) > MAX_INPUT_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Expected output exceeds size limit.",
            )

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