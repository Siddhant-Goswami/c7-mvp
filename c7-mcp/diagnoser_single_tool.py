"""Stage 1 of 3 — ONE tool, ONE decision, ONE execution, NO loop.

The straight-line version: the model decides, we execute, the model
answers, grounded. Feel each beat before any abstraction hides it.
(Next stage: diagnoser_two_tools.py, where a second tool breaks this.)

LLM 2's side of the untangling: this file sits inside the workflow —
description in, plan out, via the Groq API. The model never touches the
network; every real call happens here, on a machine we control.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

# Read GROQ_API_KEY and TAVILY_API_KEY from .env into the environment.
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

# The grounded system prompt: diagnosis logic, plus WHEN to reach for
# tools. If you do not specify it, the LLM assumes it — so specify it.
SYSTEM_PROMPT = (
    "You are a workflow diagnosis assistant. ALWAYS use the search_web tool "
    "first, before answering or calling any other tool, to find the current "
    "tools that fit the described workflow. Never do arithmetic yourself; "
    "use a tool for any calculation. Then respond in plain text with "
    "repeatable steps, automation opportunities, and a suggested MVP, "
    "naming specific, current tools."
)


# ---------------------------------------------------------------------------
# The tool: any deterministic function with a defined input and output.
# Ours is Tavily search — it returns page content plus a model-ready summary,
# not just links. Key in an environment variable, as always. The model will
# never run this function; it will only ASK for it to be run.
# ---------------------------------------------------------------------------

def search_web(query: str) -> dict:
    """Search the web via Tavily (1,000 free credits/month)."""
    return tavily.search(query=query, max_results=5,
                         include_answer=True)


# ---------------------------------------------------------------------------
# The contract: the Exercise 2 shape, in the form the Groq API expects,
# passed as a FIRST-CLASS tools input — never mixed into the system prompt.
# Name: specific and verb-like. Description: says WHEN, because the model
# routes from this text alone. `required` is what lets the model ask a
# follow-up instead of guessing when a field is missing.
# ---------------------------------------------------------------------------

TOOLS = [{
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
}]


def run_tools(name: str, args: dict):
    """Execute layer: validate the decision, make the real call."""
    print(f"  [tool call] {name}({args})")
    if name == "search_web":
        return search_web(**args)
    # A decision you did not anticipate is an error you report,
    # never a guess you execute.
    return {"error": f"unknown tool: {name}"}


# ---------------------------------------------------------------------------
# One pass, no loop. The exchange as a straight line, exactly as it happens
# on the wire: the model decides, we execute, the model answers.
# ---------------------------------------------------------------------------

def diagnose(workflow_description: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": workflow_description},
    ]

    # Pass 1: the model DECIDES (it cannot execute anything)
    first = client.chat.completions.create(
        model="qwen/qwen3-32b", messages=messages,
        tools=TOOLS, tool_choice="auto",
    ).choices[0].message

    # WE execute the decision
    call = first.tool_calls[0]
    args = json.loads(call.function.arguments)
    result = run_tools(call.function.name, args)

    # Pass 2: result goes back in; the model answers, grounded
    messages.append(first)
    messages.append({"role": "tool", "tool_call_id": call.id,
                     "content": json.dumps(result)})
    final = client.chat.completions.create(
        model="qwen/qwen3-32b", messages=messages, tools=TOOLS,
    ).choices[0].message
    return final.content


if __name__ == "__main__":
    # The golden input from Lecture 10. Watch the trace: one search_web
    # call with a sensible query, then a plan naming tools that exist
    # this month. The model never touched the network — it read text and
    # emitted a JSON decision; our Python made the real call.
    plan = diagnose(
        "I open Jira to check my weekly to dos, pick a high priority task, "
        "create a report, and send it to my manager on Slack."
    )
    print("\n" + str(plan))
