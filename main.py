import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from groq import Groq
from supabase import create_client

# Read SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY from the .env file
# into the environment. (On Render these come from the dashboard instead.)
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Connect to the database. We use the SERVICE_ROLE key because this file runs on
# the server — the machine WE control. This key bypasses every rule, so it must
# never leave the server and never appear in the frontend. (The `anon` key is
# the public one; it is not used here.)
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

app = FastAPI(title="Workflow Diagnoser API")

@app.get("/")
def read_root():
    return {"message": "Hello, builder"}


def call_groq(user_content: str) -> str:
    """The L06 brain, unchanged: ask the LLM for a diagnosis."""
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a workflow diagnosis assistant. Analyze the described workflow and "
                    "respond in plain text with repeatable steps, automation opportunities, and "
                    "a suggested MVP."
                ),
            },
            {"role": "user", "content": user_content},
        ],
    )
    return completion.choices[0].message.content


@app.post("/diagnose", response_class=PlainTextResponse)
def diagnose(body: dict):
    user_content = body.get("workflow_description", "")

    # Four beats: open a conversation, store the question, think, store the answer.
    # We wrap MEMORY around last week's brain — we don't replace it.

    # 1. open a conversation (the domain-model "conversation" gets a row)
    convo = supabase.table("conversations").insert(
        {"title": user_content[:60]}
    ).execute()
    conversation_id = convo.data[0]["id"]

    # 2. store what the user said
    supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "role": "user",
        "content": user_content,
    }).execute()

    # 3. think (the L06 logic, untouched)
    plan = call_groq(user_content)

    # 4. store what the model answered
    supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": plan,
    }).execute()

    # The plan still comes back as plain text, so the L06 frontend keeps working.
    # The new conversation_id is also returned in a header for anyone who wants it.
    return PlainTextResponse(plan, headers={"X-Conversation-Id": conversation_id})
