# Build plan: "A Server Anyone Can Call" v3 (`c7-mcp/`)

Source: `100x_C7_ConnectingTheDots_ServerAnyoneCanCall_v3.docx` (supersedes the v1 notes from `files (18).zip`).
Goal: a progressive, beginner-friendly build with atomic commits, performable live. v3 arc: **one pass by hand → second tool breaks it → derive the loop → the socket**.

## Decisions
- `c7-mcp/` subfolder, branch `mcp` (history rewritten for v3 + force-pushed; user approved).
- **Separate files per stage** (user requirement): `diagnoser_single_tool.py` (one tool, straight line) → `diagnoser_two_tools.py` (the break, kept as a runnable exhibit) → `diagnoser.py` (the loop; what `server.py` imports). Self-contained on purpose — students diff the stages.
- The word "agent" appears **nowhere** (standing user requirement; v3's `agent.py` is `diagnoser.py` here).
- Tavily via `tavily-python` SDK (v3), `run_tools` plural (v3), tags `mcp-step-0` … `mcp-step-7`.

## Model choice — deliberate deviation from the notes
The notes use `llama-3.3-70b-versatile`; on 2026-07-11 it failed ~50% of tool calls on Groq (`tool_use_failed` 400s, malformed generations). Tested alternatives on this exact workload:
- `meta-llama/llama-4-scout…`: emits string args for numeric fields → schema 400s (~40%).
- `openai/gpt-oss-120b`: superb tool discipline but hits free-tier 429s and once invented a `top_k` arg.
- **`qwen/qwen3-32b` (chosen)**: zero API errors across all runs; single-tool stage searches-then-answers 3/3; loop fires both tools 4/4 with the tuned demo question.
Swap is one string in each file if llama recovers.

## Reliability tuning (all verified live)
- Tool descriptions carry the routing/order ("ALWAYS call this first…", "after search_web has grounded the plan") — the description is the router.
- SYSTEM_PROMPT: search-first + "never do arithmetic yourself".
- The Step-5 demo question includes "name the current tools I should use" — without it, qwen skips search ~50%; with it, search→estimate 4/4.
- Break exhibit gate: `diagnoser_two_tools.py` counts executed tools and prints `[the gate] … 1 executed` every run — deterministic even though the failure flavor varies (None / ungrounded plan / freestyled math). The doc's exact `None` flavor reproduces often with the tuned question.
- Strip-the-numbers exercise: qwen INVENTS minutes despite `required`; README exercise rewritten as a two-beat demo (watch it assume → add the "ask, never assume" prompt line → watch it ask; line verified to work).

## Commit sequence (all done ✅)
0. Scaffold — README (v3 arc, LLM1/LLM2 table, files table), requirements (groq, tavily-python, python-dotenv), .env.example
1. The tool — `diagnoser_single_tool.py`: TavilyClient `search_web` + direct demo
2. The contract — TOOLS + `run_tools` (trace print, unknown-tool error)
3. One pass, no loop — straight-line `diagnose()`, golden input ✅ live
4. The break — `diagnoser_two_tools.py` (two edits + gate print) ✅ live (`None` + "1 executed")
5. Derive the loop — `diagnoser.py` + README exercise ✅ live (search→estimate→173.3)
6. The socket — `server.py` (imports `diagnose`; estimate math inline per doc), requirements += fastmcp ✅ `list_tools` + HTTP initialize handshake
7. Ship it — README: Inspector, URL rule, FastMCP Cloud (entrypoint `c7-mcp/server.py:mcp`), connect, receptionist table, cross-track table, troubleshooting (+ new "model asks instead of calling" and "tool_use_failed 400" rows), five sentences, self-test

## Verification summary (2026-07-11)
- Steps 3/4/5 all run live end-to-end with keys in `c7-mcp/.env`.
- `grep -ri agent c7-mcp/` → zero hits. `git log api..mcp` reads as the v3 outline.
- Outstanding: FastMCP Cloud deploy rehearsal (live-day), re-check keys on lecture day.
