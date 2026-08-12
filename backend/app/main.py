"""FastAPI entrypoint.

Run:
    uvicorn app.main:app --reload
"""

import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import os

from app.routes import admin, candidate_intake, chat, sandbox, transcribe, proctoring
from app.workers.proctoring_worker import start_worker, stop_worker
from app.middleware import TimingMiddleware

logger = logging.getLogger(__name__)

# Load routers whose filenames are Python keywords
import_router = importlib.import_module("app.api.routers.import")
questions_router = importlib.import_module("app.api.routers.questions")
question_sets_router = importlib.import_module("app.api.routers.question_sets")


# ---- Lifespan: start/stop the proctoring vision worker ---------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENABLE_PROCTORING_WORKER", "true").lower() == "true":
        start_worker()
        logger.info("Proctoring vision worker enabled.")
    else:
        logger.info("Proctoring vision worker disabled (ENABLE_PROCTORING_WORKER != true).")
    try:
        yield
    finally:
        await stop_worker()


app = FastAPI(
    title="Adaptive Competency Assessment (intern starter)",
    lifespan=lifespan,   # <-- ADDED
)

_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

if "*" in _cors_origins:
    raise RuntimeError("CORS_ORIGINS=* cannot be combined with allow_credentials=True")
if not _cors_origins:
    raise RuntimeError("CORS_ORIGINS is empty — at least one origin is required")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TimingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Without this, an unhandled exception (e.g. a route that's still `raise
    NotImplementedError` while under active development) can produce a response that skips
    CORSMiddleware entirely — the browser then reports a confusing "blocked by CORS policy"
    error that hides the real 500/exception, costing real debugging time chasing the wrong
    problem. This guarantees every unhandled error still gets a clean JSON body and CORS headers,
    so the frontend sees the actual failure instead of a misleading CORS message.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
        headers={"Access-Control-Allow-Origin": _cors_origins[0] if _cors_origins else "*"},
    )


app.include_router(admin.router)
app.include_router(candidate_intake.router)
app.include_router(chat.router)
app.include_router(proctoring.router)
app.include_router(transcribe.router)

if os.getenv("ENABLE_SANDBOX_ROUTE", "false").lower() == "true":
    app.include_router(sandbox.router)

# ---------------------------------------------------------
# Question Bank API
# ---------------------------------------------------------

app.include_router(import_router.router)
app.include_router(questions_router.router)
app.include_router(question_sets_router.router)

# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
async def health():
    return {"ok": True}
