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

## Exercise: predict, then run

Route these on paper **first**, against `diagnoser.py`:

1. "Diagnose my invoice approval process."
2. "How many hours does a 40-minute daily task cost per year?"
3. "Good morning."

Which fires which tool; which fires nothing? If you cannot predict the
routing, your descriptions are not done: **the description is the router.**

Then strip the numbers from the hours question — *"How many hours does my
daily standup cost per year?"* — and watch what happens. The schema marks
both fields `required`, yet the model **invents** a standup length (15
minutes, say) rather than asking you. You just met the rule again: **if you
do not specify it, the LLM assumes it.** `required` forces the model to
*provide* the field; only your prompt can tell it *where the value must come
from*. Add one line to `SYSTEM_PROMPT` —

> "If a calculation needs numbers the user has not given, ask for them;
> never assume values."

— re-run, and confirm the model now asks a follow-up instead of inventing
minutes. One unspecified boundary, one line to specify it.

**The loose thread.** The input side is now specified: schema, types,
required fields. The output side stays open — generation is next-token
prediction, and one stray quote can break a deterministic parser. Is a
prompt alone enough to guarantee format? That is the homework rabbit hole,
one level below MCP. Watch the socket closely: it quietly solves half of it
on the input side.

## Run the socket locally

```bash
python server.py          # serving at http://localhost:8000/mcp
fastmcp dev server.py     # opens the MCP Inspector
```

The Inspector is your `/docs` page from Lecture 06, reborn: it lists both
tools and lets you call them before any host is involved. Both tools
visible means the socket is live.

**The URL rule.** Your endpoint is the URL ending in `/mcp`, speaking
streamable HTTP. `localhost:8000/mcp` works for the Inspector and Claude
Code, but claude.ai cannot reach your laptop — exactly as Hugging Face
could not in Lecture 06. Then the answer was Render; now it is FastMCP
Cloud.

## Deploy (FastMCP Cloud)

1. Push the repo to GitHub.
2. On [fastmcp.cloud](https://fastmcp.cloud): create a project from the
   repo. **Entrypoint: `c7-mcp/server.py:mcp`** — the `uvicorn main:app`
   grammar, with the folder prefix because this build lives in a subfolder
   of the repo.
3. Add both env vars, `GROQ_API_KEY` and `TAVILY_API_KEY`, in project
   settings. The cloud machine never saw your `.env`.
4. Deploy. You get `https://<project>.fastmcp.app/mcp`.

That URL is the whole handshake.

## Connect and talk

- **claude.ai** — "+" → Connectors → Add custom connector → paste the
  `/mcp` URL.
- **Claude Code**:

```bash
claude mcp add --transport http aarav-advisor \
    https://<project>.fastmcp.app/mcp
```

Ask Claude: *"Diagnose my morning Jira routine and tell me how many hours
automating it would save at 40 minutes a day, 5 days a week."*

Under the hood the host calls `tools/list` to discover, then `tools/call`
twice: into `diagnose_workflow` (which runs its inner search loop on your
server) and into `estimate_time_saved`. **Done equals:** both tools in
`tools/list`, two correctly routed calls in your server logs.

**The two intents.** Every MCP conversation is two verbs. `tools/list`
asks "what can you do?"; `tools/call` says "do this one, with these
arguments." You did both by hand in Piece One: passing `TOOLS` was
`tools/list`, executing the JSON decision was `tools/call`. MCP added no
machinery; it standardised yours. That is what a grammar is.

## The receptionist you never hired

Everything you designed for LLM 1 exists in the running system. You built
none of it:

| What LLM 1 needs | On paper: you | Today: the host provides |
|---|---|---|
| The model + chat loop | Pick one, wrap a loop around it | Claude, maintained by Anthropic |
| The tool contract | Hand-written JSON | `@mcp.tool`, from name, docstring, hints |
| Input extraction | Parameter descriptions | Same descriptions, via `tools/list` |
| The follow-up rule | "If required is missing, ask" | Schema marks it `required`; the host asks |
| Rendering the answer | A chat UI you build | The conversation itself |

Count what you did **not** build: no Gradio, no HTML, no `BACKEND_URL`,
no input box. The front end's whole job was collecting structured intent
from an unstructured human, and the model does that conversion natively.
Language itself became the user interface, and the LLM became the layer
that renders it. You did not delete the interface; you moved the line as
far as it goes.

**Cross-track check** — the host cannot tell which track built the server:

| Layer | n8n (no-code track) | Python (this build) |
|---|---|---|
| Tool name | Tool node name | Function name |
| Description (the router) | Tool Description field | Docstring |
| Input schema | `$fromAI('city')` | Type hints |
| Secret | Credential | Environment variable |
| The socket | MCP Server Trigger node | `@mcp.tool` decorator |

## If something doesn't connect

| Symptom | Likely cause | Fix |
|---|---|---|
| Model answers without searching | Weak tool description or prompt | Say *when* to search in both; re-run |
| Model asks instead of calling | A `required` field is missing | That is the spec working; answer it |
| `tool_use_failed` 400 from Groq | The model emitted malformed call JSON | Re-run; if frequent, switch the model id |
| `KeyError` on a key name | Env var not set where the code runs | `.env` locally; project settings on cloud |
| Client connects, no tools | Missing decorator or wrong entrypoint | Add `@mcp.tool`; entrypoint `c7-mcp/server.py:mcp` |
| claude.ai cannot add localhost | Hosted clients cannot reach your laptop | Deploy; paste the public `/mcp` URL |
| Right tools, wrong tool called | Vague docstring | Rewrite it to say *when* to use the tool |
| Anyone can call it by default | No auth on the endpoint | Add bearer auth, or take the demo down |

**Clarity first, generation second.** For an MCP tool the design *is* the
docstring and the type hints. Write those as carefully as you wrote the
hand-written contract, and only then hand the implementation to Claude.
Generation without clarity is how you get boundaries nobody specified.

## The whole thing in five sentences

1. **The two LLMs.** One faces the user and routes; one sits inside the
   workflow and works; every reliability problem lives at their boundaries.
2. **One pass.** The model decides in JSON, your backend executes, the
   result goes back, the model answers grounded.
3. **The loop.** You cannot know how many decisions a question needs, so
   you repeat decide–execute–respond until the model stops deciding.
4. **The socket.** One decorator generates the contract from the function
   you already wrote, serves it at `/mcp`, and validates inputs against
   your type hints before your code runs.
5. **The interface.** Deploy once and every MCP host becomes your front
   end; the UI is the conversation itself.

Now do it for your own workflow: take the function at the heart of your
MVP, give it the one tool that grounds its weakest claim, run one pass by
hand, break it, wrap the loop, put `@mcp.tool` on top, deploy, paste the
URL into Claude.

## Stop and think (self-test)

1. Say why the straight-line version returned `None`, in one sentence.
2. When Claude calls your server, point at LLM 1 and LLM 2 and say where
   each system prompt lives.
3. Name the three fields `@mcp.tool` generates, plus what FastMCP does
   with your type hints *before* your function runs.
4. Say what `tools/list` and `tools/call` do, and where you did both by
   hand.
5. Say why claude.ai cannot use localhost.

If any answer feels shaky, rebuild the weak part once more.
