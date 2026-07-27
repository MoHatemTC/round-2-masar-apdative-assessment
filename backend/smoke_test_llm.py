"""Throwaway script to confirm the real LLM gateway responds. Not part of the app — delete after use."""
import asyncio
from app.services.llm import chat_json


async def main():
    result = await chat_json(
        system="Reply with ONLY a JSON object.",
        user='Return this exact object: {"status": "ok", "n": 2}',
    )
    print("data :", result.data)
    print("raw  :", result.raw)
    print("error:", result.error)


asyncio.run(main())