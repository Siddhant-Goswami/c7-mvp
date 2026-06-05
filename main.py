"""
The Workflow Diagnoser API. The thing at the address that answers the call.

Lecture 05: you wrote the contract on paper (Practice Set 01). This file makes
it real. FastAPI does the six jobs anything behind an address must do:

    1. Listen   at an address + path        (WHERE)
    2. Route    by method + path            (ACTION)
    3. Read     the incoming request        (SEND, the input)
    4. Run      the logic
    5. Return   an answer in the agreed shape(BACK, the output)
    6. Reject   anything that does not match (Pydantic, automatically)

Run it locally:
    uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs to read and call your own contract.
"""

import json
import os

from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq

MODEL = "llama-3.3-70b-versatile"

# Flip to False to run the deterministic stub with no LLM in the loop.
# Section 6 of the guide: prove the plumbing before adding the brain.
USE_LLM = True

# The whole reason the backend exists, in one line: the key comes from an
# environment variable, never from the code, never from the frontend.
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI(
    title="Workflow Diagnoser API",
    description="Describe a repeated task. Get back the steps you could automate.",
)


# --- The contract, as enforced shapes (Section 5) ----------------------------

class DiagnoseRequest(BaseModel):
    """Your Practice Set 01 input, line for line. FastAPI rejects anything
    that does not match this with a 422 before your logic ever runs."""
    workflow_description: str
    tools_used: list[str] = []
    biggest_pain: str = ""


class DiagnoseResponse(BaseModel):
    """The ideal answer Aarav sketched in discovery, now the agreed output shape."""
    repeatable_steps: list[str]
    automation_opportunities: list[str]
    suggested_mvp: str


# The golden output. Doubles as the fallback so the contract never breaks,
# even when the model is weird or unreachable.
GOLDEN = DiagnoseResponse(
    repeatable_steps=["check Jira", "build the report", "send it on Slack"],
    automation_opportunities=["auto-draft the daily report from Jira"],
    suggested_mvp="a Jira to Slack summary drafter",
)


SYSTEM_PROMPT = (
    "You are a workflow diagnosis assistant. The user describes one repeated "
    "task they do at work. Return ONLY a JSON object, no prose, no markdown "
    "fences, with exactly these keys:\n"
    '  "repeatable_steps": a list of the main steps, in order\n'
    '  "automation_opportunities": a list of steps an AI could speed up\n'
    '  "suggested_mvp": one sentence naming the smallest thing worth building'
)


# --- The brain (Section 7) ---------------------------------------------------

def run_diagnosis(request: DiagnoseRequest) -> DiagnoseResponse:
    """Call the LLM through the Groq wrapper and shape its text into the
    response contract. Falls back to the golden shape on any failure, so the
    endpoint always honors DiagnoseResponse."""
    user_content = (
        f"Workflow: {request.workflow_description}\n"
        f"Tools used: {', '.join(request.tools_used) or 'unspecified'}\n"
        f"Biggest pain: {request.biggest_pain or 'unspecified'}"
    )
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        data = json.loads(completion.choices[0].message.content)
        return DiagnoseResponse(
            repeatable_steps=data.get("repeatable_steps", GOLDEN.repeatable_steps),
            automation_opportunities=data.get(
                "automation_opportunities", GOLDEN.automation_opportunities
            ),
            suggested_mvp=data.get("suggested_mvp", GOLDEN.suggested_mvp),
        )
    except Exception:
        # The model misbehaved or was unreachable. The contract still holds.
        return GOLDEN


# --- The endpoints (Sections 4 and 6) ----------------------------------------

@app.get("/")
def read_root():
    # GET = Read. The smallest possible thing that listens and answers.
    return {"message": "Hello, builder"}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest):
    # POST = Create. ACTION + WHERE in one line; `request` is SEND, read and
    # validated against DiagnoseRequest; the return value is BACK.
    if not USE_LLM:
        return GOLDEN
    return run_diagnosis(request)
