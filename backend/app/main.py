"""FastAPI entrypoint. Run: uvicorn app.main:app --reload --port 8000"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import admin, candidate_intake, chat

logger = logging.getLogger(__name__)

app = FastAPI(title="Adaptive Competency Assessment (intern starter)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
        headers={"Access-Control-Allow-Origin": "http://localhost:3000"},
    )


app.include_router(admin.router)
app.include_router(candidate_intake.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"ok": True}