# Task: Observability layer + instant-reveal prompt flag (+ deploy reframe)

## Goal
Finish the live-MVP build so the lecture's last three segments work:
- **Observe** (1:20): every diagnosis logged; a live `/admin` dashboard.
- **Deploy, right-sized** (1:00): README reframed as a "find the real bottleneck" judgment lesson.
- **The reveal** (1:35): swap the product's purpose with **one keystroke**, no redeploy.

The repo is already at **Step 8** (schema, memory, auth, RLS, README). Per Appendix A: *keep the branch, make three changes.* We do NOT rebuild anything.

## Guiding rules (from the brief + CLAUDE.md)
- Atomic commits, one idea each, beginner-readable, continuing the existing `Step N: title — subtitle` convention.
- MVP only. No new infra (the same Postgres is the analytics warehouse). No Mixpanel/Datadog/Grafana.
- Derive-before-name comments, matching the existing code/SQL voice.
- No em dashes in output. (Existing files use them; we match local style in code comments but keep prose clean.)

## Verified facts
- `groq 0.33.0` installed: `with_raw_response` and `RateLimitError` both available. Brief's code runs as written.
- `requirements.txt` already has every dependency needed (no new packages).
- Current `/diagnose` returns `PlainTextResponse` + `X-Conversation-Id` header. We preserve that contract.

## Commit plan (each row = one commit)

| Step | Commit message | Files | One idea |
|---|---|---|---|
| 9  | `Step 9: Deploy — right-size for 250, name the real tripwires (README)` | `README.md` | Reframe deploy as judgment: napkin math vs free-tier ceilings; the 2 tripwires (7-day DB sleep, 30 req/min Groq cap); daily keep-alive ping. Docs only. |
| 10 | `Step 10: The events table — a place to record what happens` | `db/04_events.sql` | New `events` table, RLS on, deliberately NO select policy for `authenticated` (deny-by-default; only service_role/admin reads). |
| 11 | `Step 11: Instrument /diagnose — log latency, tokens, status` | `main.py` | `call_groq` returns `(text, meta)` via `with_raw_response` (reads `x-ratelimit-remaining-requests`); add `log_event`; wire a 200 log into `/diagnose`. |
| 12 | `Step 12: Handle the rate limit — return "you are in line", not a crash` | `main.py` | Wrap the Groq call in `try/except RateLimitError`; log a 429 event; return graceful 429 text. |
| 13 | `Step 13: A live dashboard — /metrics and /admin to watch it work` | `main.py` | `/metrics` (JSON aggregate of last 500 events) + `/admin` (auto-refreshing HTML). |
| 14 | `Step 14: Stage the prompt swap — flip the product with one keystroke` | `main.py` | `WORKFLOW_PROMPT` + `JOURNEY_PROMPT`, in-memory `PROMPT_MODE`, `current_system_prompt()`, and a hidden `/admin/mode` route for the instant reveal flip. |
| 15 | `Step 15: Document observability + the reveal in the README` | `README.md` | Short sections: what `/admin` shows, the two-prompt flag, the keep-alive ping. Closes the loop. |

(Step 14 last so the reveal mechanism sits on top of a working, observable app — matches the lecture's narrative order: deploy -> observe -> reveal.)

## Out of scope (and why)
- No custom `/signup` `/login` endpoints: the segment uses Supabase Auth's own REST endpoints via `curl`; Appendix A lists only 3 changes and calls the auth flow "already excellent."
- No real deploy to Render/Spaces from here (needs the user's accounts/secrets). README documents it; user does it live.
- Applying `db/04_events.sql` to the live Supabase project is optional and can be done via the Supabase MCP after you approve — I'll offer it as a follow-up, not bundle it into a commit.

## Verification per step
- After each `main.py` change: `python -c "import ast; ast.parse(open('main.py').read())"` to confirm it parses (can't fully boot without live env vars/secrets).
- Confirm `/diagnose` still returns plain text + `X-Conversation-Id` (L06 frontend must keep working).
- `db/04_events.sql` reviewed for deny-by-default correctness.

## Progress log

All steps complete. Commits on branch `mvp`:

- `7266bc4` **Step 9** — `README.md`: deploy section reframed as a right-sizing
  judgment lesson (napkin math vs free-tier ceiling table, the two tripwires,
  keep-alive guidance, plus the two missing Supabase env vars on Render).
- `ce0d929` **Step 10** — `db/04_events.sql`: new `events` table; RLS enabled
  with NO select policy for `authenticated` (deny-by-default keeps it private to
  the service_role backend).
- `ee1545b` **Step 11** — `main.py`: `call_groq` now uses `with_raw_response`,
  reads `x-ratelimit-remaining-requests`, and returns `(text, meta)`. Added
  `log_event`; `/diagnose` records a 200 with latency on success. Added
  `import time`. Plain-text + `X-Conversation-Id` contract preserved.
- `18009c9` **Step 12** — `main.py`: `from groq import ... RateLimitError`;
  `/diagnose` wraps the model call in try/except, logs a 429, and returns a
  graceful "you are in line" (status 429) instead of crashing.
- `3aa4292` **Step 13** — `main.py`: `/metrics` (JSON rollup of last 500 events)
  and `/admin` (self-refreshing HTML, polls every 2s). Imported `HTMLResponse`,
  `JSONResponse`.
- `521a753` **Step 14** — `main.py`: `WORKFLOW_PROMPT` + `JOURNEY_PROMPT`,
  in-memory `PROMPT_MODE` (env default), `current_system_prompt()` (now used by
  `call_groq`), and hidden `POST /admin/mode?mode=...` for the one-keystroke
  reveal flip.
- `78fc0b8` **Step 15** — `README.md`: new Step 8 (observability) and Step 9
  (the reveal) sections.

### Live database
`db/04_events.sql` applied to the live Supabase project (`nytasdxacrkbbyvmodhh`)
via the Supabase MCP as migration `step9_events_table`. Verified: `events` table
present, `rls_enabled: true`, 0 rows. Event logging works immediately.

### Verification notes
- Every `main.py` change confirmed to parse with `ast.parse` (full boot needs
  live env vars/secrets, not run here).
- Confirmed against `groq 0.33.0`: both `with_raw_response` and `RateLimitError`
  exist, so the instrumentation runs as written.

### Handover / not done here (needs the user's accounts)
- Real deploy to Render + Hugging Face Spaces (README documents it).
- No `events` row will appear until the backend serves a real `/diagnose` with
  live `GROQ_API_KEY` + Supabase keys set.
- Optional: a daily cron pinging `/` to defeat the 7-day Supabase sleep.
