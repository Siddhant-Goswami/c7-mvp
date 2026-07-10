"""Stage 3 of 3 — THE LOOP. Repeat until the model stops deciding.

Name what the straight line really was: decide, execute, respond, ONCE.
The fix is not new machinery; it is repetition with an exit: repeat
until the model stops deciding and answers. That is a while loop with
one exit condition — no tool calls.

Same tools, same contract, same prompt as diagnoser_two_tools.py. Only
diagnose() changed. Re-run the two-tool question that broke the straight
line and read the trace: search fires, estimate_time_saved fires with
the extracted numbers, then no tool call — the model weaves the grounded
plan and 173.3 hours into one reply. This file is what server.py serves.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# Read GROQ_API_KEY and TAVILY_API_KEY from .env into the environment.
# (On FastMCP Cloud these come from the project settings instead.)
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

SYSTEM_PROMPT = (
    "You are a workflow diagnosis assistant. ALWAYS use the search_web tool "
    "first, before answering or calling any other tool, to find the current "
    "tools that fit the described workflow. Never do arithmetic yourself; "
    "use a tool for any calculation. Then respond in plain text with "
    "repeatable steps, automation opportunities, and a suggested MVP, "
    "naming specific, current tools."
)


def search_web(query: str) -> dict:
    """Search the web via Tavily (1,000 free credits/month)."""
    return tavily.search(query=query, max_results=5,
                         include_answer=True)


def estimate_time_saved(minutes_per_day: float, days_per_week: int) -> dict:
    """A pure function: arithmetic the model should not freestyle."""
    hours_per_year = minutes_per_day * days_per_week * 52 / 60
    return {"hours_per_year": round(hours_per_year, 1)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": ("Search the web for current information. ALWAYS "
                            "call this first when diagnosing a workflow: the "
                            "plan must name tools that exist today, and only "
                            "a search can know them."),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string",
                                         "description": "The search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_time_saved",
            "description": ("Convert a task's minutes per day and days per "
                            "week into hours lost per year. Use for any "
                            "time-cost or hours-saved question, after "
                            "search_web has grounded the plan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes_per_day": {
                        "type": "number",
                        "description": "Minutes the task takes each day"},
                    "days_per_week": {
                        "type": "integer",
                        "description": "Days per week the task happens"},
                },
                "required": ["minutes_per_day", "days_per_week"],
            },
        },
    },
]


def run_tools(name: str, args: dict):
    """Execute layer: validate the decision, make the real call."""
    print(f"  [tool call] {name}({args})")
    if name == "search_web":
        return search_web(**args)
    if name == "estimate_time_saved":
        return estimate_time_saved(**args)
    return {"error": f"unknown tool: {name}"}


# ---------------------------------------------------------------------------
# The loop. The same routing decision made repeatedly, each result changing
# the next decision. Every pass, the model re-reads the whole tool menu —
# which is why descriptions matter more as tools multiply.
# ---------------------------------------------------------------------------

def diagnose(workflow_description: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": workflow_description},
    ]
    while True:
        msg = client.chat.completions.create(
            model="qwen/qwen3-32b", messages=messages,
            tools=TOOLS, tool_choice="auto",
        ).choices[0].message

        if not msg.tool_calls:      # the model answered: done
            return msg.content

        messages.append(msg)        # keep the decision in history
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = run_tools(call.function.name, args)  # WE execute
            messages.append({"role": "tool",
                             "tool_call_id": call.id,
                             "content": json.dumps(result)})


if __name__ == "__main__":
    # The question that broke the straight line. Nothing else changed —
    # the while was already enough.
    plan = diagnose(
        "Diagnose my morning routine and name the current tools I should "
        "use: I open Jira, pick a priority task, write a report, and Slack "
        "it to my manager. It takes about 40 minutes a day, 5 days a week. "
        "How many hours a year would automating it save me?"
    )
    print("\n" + plan)
