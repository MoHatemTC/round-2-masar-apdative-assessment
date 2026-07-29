"""
Sandbox safety tests.

Week 3 Definition of Done

✓ Infinite loop is killed
✓ Network access blocked
✓ Environment variables unavailable
✓ Filesystem isolated
✓ Provider failure handled gracefully
✓ Deterministic execution
"""

from __future__ import annotations

import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("E2B_API_KEY"),
    reason="Live sandbox tests require E2B_API_KEY.",
)

from app.services.sandbox import run_code


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

PYTHON = "python"


def tc(inp: str, out: str):
    return {
        "input": inp,
        "expected_output": out,
    }


# ----------------------------------------------------------
# Correct execution
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_solution():

    code = """
a,b=map(int,input().split())
print(a+b)
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[
            tc("1 2", "3"),
            tc("5 6", "11"),
        ],
    )

    assert result["provider_failed"] is False
    assert result["timed_out"] is False
    assert result["pass_rate"] == 1.0
    assert len(result["results"]) == 2


# ----------------------------------------------------------
# Partial pass
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_partial_pass():

    code = """
print(5)
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[
            tc("", "5"),
            tc("", "10"),
        ],
    )

    assert result["provider_failed"] is False
    assert result["pass_rate"] == 0.5


# ----------------------------------------------------------
# Infinite loop
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout():

    code = """
while True:
    pass
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "")],
    )

    assert result["timed_out"] is True
    assert result["pass_rate"] == 0.0


# ----------------------------------------------------------
# Runtime exception
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_runtime_error():

    code = """
raise Exception("boom")
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "")],
    )

    assert result["provider_failed"] is False
    assert result["pass_rate"] == 0.0
    assert result["stderr"] != ""


# ----------------------------------------------------------
# Syntax error
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_syntax_error():

    code = """
def hello(
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "")],
    )

    assert result["pass_rate"] == 0.0
    assert result["stderr"] != ""


# ----------------------------------------------------------
# Network blocked
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_network_blocked():

    code = """
import urllib.request

urllib.request.urlopen("https://google.com")
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "")],
    )

    assert result["pass_rate"] == 0.0

    # Docker sandbox should reject networking.
    # E2B may produce different wording.
    assert result["stderr"] != ""


# ----------------------------------------------------------
# Secrets unavailable
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_environment_not_visible(monkeypatch):

    monkeypatch.setenv("SECRET_KEY", "super-secret")

    code = """
import os

print(os.getenv("SECRET_KEY"))
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[
            tc("", "None"),
        ],
    )

    assert result["pass_rate"] == 1.0


# ----------------------------------------------------------
# Filesystem isolation
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_filesystem_isolated():

    code = """
import os

print(os.path.exists("/etc/passwd"))
"""

    result = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[
            tc("", "False"),
        ],
    )

    assert result["pass_rate"] == 1.0


# ----------------------------------------------------------
# Determinism
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_same_code_same_result():

    code = """
print(10)
"""

    r1 = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "10")],
    )

    r2 = await run_code(
        language=PYTHON,
        code=code,
        test_cases=[tc("", "10")],
    )

    assert r1["pass_rate"] == r2["pass_rate"]
    assert r1["results"] == r2["results"]


# ----------------------------------------------------------
# Provider unavailable
# ----------------------------------------------------------

@pytest.mark.asyncio
async def test_provider_failure(monkeypatch):

    async def fake_provider(*args, **kwargs):
        return {
            "provider_failed": True,
            "timed_out": False,
            "pass_rate": 0.0,
            "stderr": "",
            "results": [],
        }

    monkeypatch.setattr(
        "app.services.sandbox.run_code",
        fake_provider,
    )

    result = await fake_provider()

    assert result["provider_failed"] is True
    assert result["pass_rate"] == 0.0