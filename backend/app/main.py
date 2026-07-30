"""FastAPI entrypoint.

Run:
    uvicorn app.main:app --reload
"""
import os
import importlib
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import admin, candidate_intake, chat, sandbox, transcribe

logger = logging.getLogger(__name__)

# Load routers whose filenames are Python keywords
import_router = importlib.import_module("app.api.routers.import")
questions_router = importlib.import_module("app.api.routers.questions")
question_sets_router = importlib.import_module("app.api.routers.question_sets")

app = FastAPI(
    title="Adaptive Competency Assessment (intern starter)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Without this, an unhandled exception (e.g. a route that's still `raise
    NotImplementedError` while under active development) can produce a response that skips
    CORSMiddleware entirely — the browser then reports a confusing "blocked by CORS policy"
    error that hides the real 500/exception, costing real debugging time chasing the wrong
    problem. This guarantees every unhandled error still gets a clean JSON body and CORS headers,
    so the frontend sees the actual failure instead of a misleading CORS message.
    """
    logger.exception(
    "Unhandled exception on %s %s",
    request.method,
    request.url.path,
)

    return JSONResponse(
    status_code=500,
    content={
        "detail": "Internal server error."
    },
    headers={
        "Access-Control-Allow-Origin":
        "http://localhost:3000"
    },
)


app.include_router(admin.router)
app.include_router(candidate_intake.router)
app.include_router(chat.router)
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
