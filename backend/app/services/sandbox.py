"""
Sandbox execution service.

Provides:
- E2B Code Interpreter execution
- Test case evaluation
- Timeout handling
- Runtime error detection
- Security restrictions

Return format:

{
    "provider_failed": bool,
    "timed_out": bool,
    "pass_rate": float,
    "stderr": str,
    "results": [
        {
            "passed": bool,
            "input": str,
            "expected": str,
            "actual": str,
            "stderr": str
        }
    ]
}
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox


load_dotenv()


TIMEOUT_SECONDS = 10


# ==========================================================
# Public API
# ==========================================================

async def run_code(
    language: str,
    code: str,
    test_cases: list[dict],
) -> dict:
    """
    Execute submitted code against test cases.
    """

    response = {
        "provider_failed": False,
        "timed_out": False,
        "pass_rate": 0.0,
        "stderr": "",
        "results": [],
    }

    try:

        api_key = os.getenv(
            "E2B_API_KEY"
        )

        if not api_key:
            raise RuntimeError(
                "Missing E2B_API_KEY"
            )

        sandbox = Sandbox.create(
            api_key=api_key
        )

        try:
            passed_count = 0

            for test_case in test_cases:

                result = await _execute_case(
                    sandbox=sandbox,
                    code=code,
                    test_case=test_case,
                )

                response["results"].append(result)

                if result["passed"]:
                    passed_count += 1

                if result.get("timed_out"):
                    response["timed_out"] = True

            if test_cases:
                response["pass_rate"] = round(
                    passed_count / len(test_cases),
                    2
                )

            stderr_list = [
                r["stderr"]
                for r in response["results"]
                if r["stderr"]
            ]

            if stderr_list:
                response["stderr"] = "\n".join(stderr_list)

            return response

        finally:
            try:
                sandbox.kill()
            except Exception:
                pass

    except Exception as exc:

        response["provider_failed"] = True
        response["stderr"] = str(exc)

        return response


# ==========================================================
# Execute one test case
# ==========================================================

async def _execute_case(
    sandbox,
    code: str,
    test_case: dict,
) -> dict:

    input_data = str(
        test_case.get(
            "input",
            ""
        )
    )

    expected = str(
        test_case.get(
            "expected_output",
            ""
        )
    ).strip()

    try:

        # -------------------------------------------------
        # Detect whether this is a function-call test
        # (golden tests) or stdin test (sandbox tests)
        # -------------------------------------------------

        is_function_call = (
            "(" in input_data
            and ")" in input_data
            and "\n" not in input_data
        )

        if is_function_call:

            wrapped_code = _build_wrapper(
                code=code,
                input_data="",
            )

            wrapped_code += f"""

result = {input_data}
print(result)
"""

        else:

            wrapped_code = _build_wrapper(
                code=code,
                input_data=input_data,
            )

        execution = await asyncio.wait_for(
            asyncio.to_thread(
                sandbox.run_code,
                wrapped_code,
            ),
            timeout=TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:

        return {
            "passed": False,
            "input": input_data,
            "expected": expected,
            "actual": "",
            "stderr": "Execution timeout",
            "timed_out": True,
        }

    except Exception as exc:

        return {
            "passed": False,
            "input": input_data,
            "expected": expected,
            "actual": "",
            "stderr": str(exc),
            "timed_out": False,
        }

    stdout = ""
    stderr = ""
    has_error = False

    if execution.logs:

        if execution.logs.stdout:
            stdout = "".join(
                execution.logs.stdout
            )

        if execution.logs.stderr:
            stderr = "".join(
                execution.logs.stderr
            )

    if execution.error:
        has_error = True
        stderr += str(execution.error)

    actual = stdout.strip()

    return {
        "passed": (
            not has_error
            and actual == expected
        ),
        "input": input_data,
        "expected": expected,
        "actual": actual,
        "stderr": stderr,
        "timed_out": False,
    }

# ==========================================================
# Security wrapper
# ==========================================================

def _build_wrapper(
    code: str,
    input_data: str,
) -> str:
    """
    Creates execution environment.

    IMPORTANT:
    Candidate code is inserted without indentation
    to avoid IndentationError.
    """

    wrapper = f"""
import builtins
import socket
import os


# ----------------------------
# Disable network
# ----------------------------

def blocked_socket(*args, **kwargs):
    raise RuntimeError(
        "Network access disabled"
    )


socket.socket = blocked_socket



# ----------------------------
# Filesystem restrictions
# ----------------------------

_original_exists = os.path.exists


def safe_exists(path):

    if path == "/etc/passwd":
        return False

    return _original_exists(path)


os.path.exists = safe_exists



# ----------------------------
# Environment isolation
# ----------------------------

_original_getenv = os.getenv


def safe_getenv(key, default=None):

    if key == "SECRET_KEY":
        return None

    return default


os.getenv = safe_getenv



# ----------------------------
# Input mocking
# ----------------------------

_input_value = {input_data!r}


def fake_input(*args):
    return _input_value


builtins.input = fake_input



# ----------------------------
# Candidate submission
# ----------------------------

{code}

"""

    return wrapper