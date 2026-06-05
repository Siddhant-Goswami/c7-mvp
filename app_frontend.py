"""
The thin frontend (Section 8). The logic no longer lives here — this file only
collects the user's message, calls your backend over the internet, and shows
the answer. Notice there is no key anywhere in this file. That is the design.

Run the backend first:
    uvicorn main:app --reload
Then run this:
    python app_frontend.py

Point it at a deployed backend with the BACKEND_URL environment variable, e.g.
    export BACKEND_URL=https://<your-space>.hf.space/diagnose
"""

import os

import gradio as gr
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/diagnose")


def diagnose(message, history):
    # You → here (public) → HTTP → FastAPI (private, holds the key) → Groq → back.
    try:
        response = requests.post(
            BACKEND_URL,
            json={
                "workflow_description": message,
                "tools_used": [],
                "biggest_pain": "",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return f"Could not reach the backend at {BACKEND_URL}.\n\n{e}"

    steps = "\n".join("  - " + s for s in data.get("repeatable_steps", []))
    autos = "\n".join("  - " + a for a in data.get("automation_opportunities", []))
    return (
        "Repeatable steps:\n" + steps + "\n\n"
        "Automation opportunities:\n" + autos + "\n\n"
        "Suggested MVP: " + data.get("suggested_mvp", "")
    )


demo = gr.ChatInterface(
    diagnose,
    type="messages",
    title="Workflow Diagnoser",
    description="Describe one repeated task you do at work. The brain lives in the backend.",
)

if __name__ == "__main__":
    demo.launch()
