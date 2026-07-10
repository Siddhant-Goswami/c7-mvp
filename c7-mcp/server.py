"""The standard socket. One decorator per function, and any MCP host
(Claude, ChatGPT, Cursor) can discover and call Aarav's diagnoser.

Two tool layers, on purpose:
  INSIDE  diagnoser.py : Groq decides when to call search_web — LLM 2's world
  OUTSIDE this file    : Claude decides when to call diagnose_workflow — LLM 1's world
The whole diagnoser, loop and all, is ONE tool; its inner search stays
invisible to the host. It resolves its own tool calls as the top-level
worker of its own process.

Read the decorator against the hand-written contract: the function name
becomes the tool name, the docstring the description, the type hints the
input schema, required fields inferred from the signature. Same contract,
written once instead of twice. And the loose thread's input half, handled:
the schema is validated BEFORE your function ever runs — malformed
arguments are rejected at the boundary, not executed.
"""

import os

from fastmcp import FastMCP

from diagnoser import diagnose

mcp = FastMCP("aarav-advisor")


@mcp.tool
def diagnose_workflow(workflow_description: str) -> str:
    """Diagnose a messy, repetitive workflow and return an ordered
    automation plan grounded in current tools. Use when someone
    describes a process they want to improve or automate."""
    return diagnose(workflow_description)


@mcp.tool
def estimate_time_saved(minutes_per_day: float, days_per_week: int) -> dict:
    """Convert a task's minutes per day and days per week into hours
    lost per year. Use for any time-cost or hours-saved question."""
    return {"hours_per_year":
            round(minutes_per_day * days_per_week * 52 / 60, 1)}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)))
