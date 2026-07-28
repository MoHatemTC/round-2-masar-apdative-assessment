from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from app.services.sandbox import run_code

router = APIRouter(tags=["sandbox"])


class SandboxRunRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: list[dict[str, Any]] = []


@router.post("/sandbox/run")
async def sandbox_run(req: SandboxRunRequest):
    """
    Execute candidate code inside the sandbox without grading.
    Used by Monaco's Run button.
    """

    result = await run_code(
        language=req.language,
        code=req.code,
        test_cases=req.test_cases,
    )

    return result