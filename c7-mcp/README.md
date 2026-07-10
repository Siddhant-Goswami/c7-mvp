# A Server Anyone Can Call

**Lecture · Connecting the Dots · Applied AI build series · 100xEngineers**

Last session the whiteboard became code. Today you run **one tool call end to
end**, **break it** with a second tool, **derive the loop**, and then put a
**standard socket** on the whole thing so Claude becomes your front end.

## The arc so far

- **Lecture 06** wrapped `diagnose(workflow_description)` in FastAPI on Render.
- **Lecture 10** shipped the full MVP: Gradio, Hugging Face, Supabase.
  (That code lives one folder up, in this repo.)
- **LL12 + LL13** derived the interface spec — name, description, typed
  parameters, required fields — and the three-layer rule: **the LLM decides,
  the execution environment executes, the tool touches reality.**
- **Last session** untangled the two LLM calls inside one product, connected
  Tavily, and installed the rule behind most of your future bugs:
  **if you do not specify it, the LLM assumes it.**

Hold the untangling in mind; everything today hangs on it:

| | LLM 1: the user interface | LLM 2: the API |
|---|---|---|
| Role | Talks to Aarav, extracts the workflow description, decides whether to call the tool at all | Sits inside the workflow. Description in, plan out, via the Groq API |
| System prompt | Routing rules and tool descriptions | Diagnosis logic, plus the Tavily tool description |
| Analogy | The receptionist who routes calls | The department that does the work |

One thing is still on paper: LLM 1. Today you will **not** build it. You will
put a socket on your workflow, and every host that already ships an interface
LLM (Claude, Cursor, ChatGPT) becomes LLM 1 for free.

## What you will build

1. **One tool call, executed by hand, no loop.**
2. **A second tool that breaks the straight-line code, and the loop that
   fixes it.**
3. **The diagnoser exposed as an MCP server**, deployed on FastMCP Cloud,
   answering inside Claude with no front end.

## What you need

- Python 3.10+
- A **Groq** API key — [console.groq.com](https://console.groq.com)
- A **Tavily** API key — [tavily.com](https://tavily.com)
  (1,000 free credits a month, no card)

## Setup

```bash
cd c7-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your two keys into .env
```

## How to follow this build

The single-tool → multiple-tool progression is kept in **separate files**, so
you can read, run, and diff every stage side by side:

| File | Stage | Run it and see |
|------|-------|----------------|
| `diagnoser_single_tool.py` | One tool, one pass, **no loop** — the exchange as a straight line | One search, then a grounded plan |
| `diagnoser_two_tools.py` | Second tool added, still no loop — **the break** | `None` — the straight line assumed exactly one decision |
| `diagnoser.py` | **The loop**: repeat until the model stops deciding | Both tools fire, one woven answer |
| `server.py` | The socket: `@mcp.tool`, any MCP host can call it | Both tools in the Inspector |

Each git commit is one step of the lecture, in order — the history *is* the
outline:

```bash
git log --oneline -- c7-mcp/    # the steps
git show mcp-step-4             # jump to any step's diff (tags: mcp-step-0 … mcp-step-7)
```

| Step | What happens |
|------|--------------|
| 0 | Scaffold — this README, the dependencies, the keys |
| 1 | The tool: `search_web()`, a deterministic function |
| 2 | The contract: `TOOLS` + `run_tools()`, a first-class input |
| 3 | One pass, no loop: decide → execute → answer, as a straight line |
| 4 | The second tool breaks the straight line: `None` |
| 5 | Derive the loop: repeat until the model stops deciding |
| 6 | The socket: `@mcp.tool`, and any MCP host can call it |
| 7 | Ship it: deploy, connect to Claude, troubleshoot |
