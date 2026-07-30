from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Literal

MAX_CODE_SIZE = 20_000
MAX_TEST_CASES = 5
MAX_INPUT_SIZE = 500


class SandboxRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Literal["python"] = "python"
    test_cases: list[dict[str, Any]] = []


def validate_sandbox_request(req: SandboxRequest) -> None:
    if len(req.code) > MAX_CODE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Submitted code is too large.",
        )

    if len(req.test_cases) > MAX_TEST_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_TEST_CASES} test cases allowed.",
        )

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