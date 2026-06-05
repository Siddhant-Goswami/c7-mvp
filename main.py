import os

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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
