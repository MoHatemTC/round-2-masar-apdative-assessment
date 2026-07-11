"""FastAPI entrypoint. Run: uvicorn app.main:app --reload --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import admin, chat

app = FastAPI(title="Adaptive Competency Assessment (intern starter)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"ok": True}
