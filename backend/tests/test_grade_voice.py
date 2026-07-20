import asyncio
from app.services.grading import grade_answer

question = {
    "id": "q-voice-1",
    "tool_type": "voice",
    "body": "Describe a time you resolved a conflict on a team.",
    "payload": {
        "evaluation_criteria": ["Names the situation", "Explains their actions", "Reflects on the outcome"],
    },
}

# Replace this with whatever you actually typed in the frontend test
tool_result = {"answer_text": "My teammate and I disagreed on the API design. I set up a call, we listed pros and cons together, and picked the option with better test coverage. It worked out well and we shipped on time."}

async def main():
    result = await grade_answer("voice", question, tool_result)
    print("Score:", result["score"])
    print("Rationale:", result["rationale"])

asyncio.run(main())