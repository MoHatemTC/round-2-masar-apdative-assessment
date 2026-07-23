"""FastAPI entrypoint.

Run:
    uvicorn app.main:app --reload
"""

import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import admin, chat, candidate_intake

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

# ---------------------------------------------------------
# Existing application routes
# ---------------------------------------------------------

app.include_router(admin.router)
app.include_router(candidate_intake.router)
app.include_router(chat.router)

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
