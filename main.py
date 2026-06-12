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

@app.post("/diagnose", response_class=PlainTextResponse)
def diagnose(body: dict):
    user_content = body.get("workflow_description", "")
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
