# Sandbox Provider Decision

**Project:** Adaptive Assessment Platform – Week 3 Coding Question Type

**Author:** Nour Magdy ElMansoury

**Date:** July 2026

---

# Decision

The coding execution sandbox uses **E2B** as the primary execution provider.

If E2B is unavailable, grading gracefully falls back by flagging the submission for manual review instead of executing untrusted code on the application host.

This satisfies the sprint requirement that candidate code is never executed directly inside the backend application process.

---

# Provider

Primary Provider

- E2B Code Interpreter
- API Key configured through:

```env
E2B_API_KEY=<configured in .env>
```

The backend automatically detects whether the E2B API key exists.

```
if E2B_API_KEY exists
    -> use E2B
else
    -> provider unavailable
```

---

# Why E2B

E2B provides an isolated cloud execution environment specifically designed for AI-generated and untrusted code.

Advantages include:

- isolated runtime
- no execution on the FastAPI host
- disposable containers
- filesystem isolation
- resource limits
- suitable for arbitrary user code

Compared with running code locally, E2B greatly reduces security risks while requiring minimal infrastructure.

---

# Execution Flow

Candidate submits code

↓

Backend receives submission

↓

Sandbox Provider (E2B)

↓

Run against payload.test_cases

↓

Collect pass/fail results

↓

Calculate deterministic pass rate

↓

LLM judge evaluates expected approach

↓

Blend scores (50% tests + 50% judge)

↓

Return

```
{
    score,
    rationale,
    flagged
}
```

---

# Security Bounds

The sandbox is configured with the following constraints.

## Network

- Outbound internet access disabled
- No HTTP requests allowed
- No socket connections

This prevents:

- downloading malware
- contacting external APIs
- data exfiltration

---

## CPU

Execution time is limited.

Current timeout:

- 5 seconds

Infinite loops are terminated automatically.

Result:

```
Execution timed out.
```

---

## Memory

Memory is limited by the sandbox provider.

Large allocations are terminated automatically.

---

## Filesystem

Each execution receives an isolated temporary filesystem.

Candidate code cannot:

- read backend files
- modify project source code
- access host filesystem

All files are destroyed after execution.

---

## Environment Variables

No application secrets are exposed inside the sandbox.

The following variables are **not** available:

- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_SERVICE_ROLE_KEY
- OPENAI_API_KEY
- LLM_API_KEY
- E2B_API_KEY

This prevents secret leakage.

---

## Process Isolation

Candidate code executes inside an isolated sandbox.

It cannot:

- spawn privileged processes
- escape the container
- access the FastAPI process

---

# Failure Handling

If the provider is unavailable:

```
{
    score: null,
    flagged: true,
    rationale:
        "Sandbox provider unavailable. Submission flagged for manual review."
}
```

The assessment session continues normally.

---

# Determinism

Sandbox execution is deterministic.

The same submission and identical test cases produce the same pass rate.

Only the LLM evaluation may introduce slight score variation.

If the LLM fails:

- grading falls back to the deterministic pass-rate score
- submission is marked as flagged

This ensures assessments continue even during LLM outages.

---

# Rationale

E2B was selected because it:

- executes untrusted code outside the application server
- provides strong isolation
- supports multiple programming languages
- integrates easily with Python
- minimizes infrastructure maintenance
- satisfies the Week 3 security requirements

The architecture also supports replacing E2B with a locked-down Docker runner in the future without changing the grading API.

---

# Future Docker Fallback

If E2B becomes unavailable or self-hosting is required, the sandbox provider can be replaced with a Docker-based executor configured with:

- `--network=none`
- CPU limits
- Memory limits
- Read-only filesystem
- Temporary writable volume
- Automatic timeout
- Container removal after execution

No changes to the grading interface are required because both providers implement the same `run_code()` contract.

---

# Conclusion

The project adopts **E2B** as the primary sandbox provider because it offers secure execution of untrusted code outside the application host while meeting the Week 3 requirements for safety, determinism, and resource isolation.