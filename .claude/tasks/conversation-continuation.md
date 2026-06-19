# Task: Conversation continuation — follow-up messages append to the same thread

## The problem, precisely

Today every `/diagnose` call **unconditionally creates a new `conversations` row**
(`main.py`) and titles it with the first 60 chars of the message. There is no
"continue this thread" path, so:

1. The domain model promises `conversation` → *many* `messages` (a back-and-forth),
   but in practice every conversation holds exactly **one** Q+A pair.
2. The AI has **no memory within a session** — `call_groq` only ever sends the
   system prompt + the single current message. Ask a follow-up ("make that
   simpler") and the model has no idea what "that" refers to.
3. The table fills with near-duplicate one-shot rows (what the user just saw).

This is the natural next feature the MVP deliberately left open.

## The fix (MVP)

Let the frontend carry a `conversation_id` for the browser session. Send it on
every `/diagnose`. The backend, if given a valid id **owned by the caller**,
appends to that thread and feeds the prior turns back to the model for context;
otherwise it starts a new conversation exactly as today.

**Key teaching point baked in:** the backend uses the `service_role` key, which
*bypasses RLS*. So when it acts on a user's behalf, **the backend itself must
verify ownership** — RLS won't do it here. This is the mirror image of the RLS
lesson: the master key is powerful precisely because it skips the guards, so the
code holding it carries the responsibility the guards normally would.

---

## Changes

### 1. `main.py` — accept an optional `conversation_id`, append + add context

- Refactor `call_groq` to take the **conversation turns** instead of a lone
  string:
  ```python
  def call_groq(turns):                      # turns = [{"role","content"}, ...]
      raw = client.chat.completions.with_raw_response.create(
          model="llama-3.3-70b-versatile", max_tokens=1024,
          messages=[{"role": "system", "content": current_system_prompt()}, *turns],
      )
      ...                                     # meta unchanged
  ```
- In `/diagnose`, read `conversation_id = body.get("conversation_id")` and resolve
  the thread:
  - **If provided:** look it up and confirm `user_id` matches the caller. If it
    matches → reuse. If it does not exist, or is owned by someone else →
    **`403 Forbidden`** ("That conversation isn't yours."). We refuse rather than
    silently fork, because the backend holds `service_role` and is the only thing
    standing between a forged id and another user's thread.
  - **If not provided:** create a new conversation (title = first 60 chars), as
    today.
- New order of operations:
  1. resolve/insert the conversation,
  2. insert the user message,
  3. **load the thread's messages** (`role, content` ordered by `created_at`) —
     this now includes the just-inserted user turn,
  4. **cap to the last ~20 turns** so a long thread can't blow the context window
     (simple slice; leave a comment that this is the naive bound),
  5. `call_groq(turns)`,
  6. insert the assistant message,
  7. `log_event(...)` (unchanged),
  8. return the plain-text plan with `X-Conversation-Id` header (already there).
- Add `X-Conversation-Id` to the **429** response too, so a rate-limited turn
  doesn't orphan the thread.

### 2. `app_frontend.py` — remember the thread for the session

- Add a second state: `convo_state = gr.State(None)`.
- Thread it through `ChatInterface`:
  ```python
  gr.ChatInterface(
      diagnose,
      additional_inputs=[token_state, convo_state],
      additional_outputs=[convo_state],         # lets the fn write the id back
      ...
  )
  ```
- `diagnose(message, history, token, conversation_id)` now:
  - sends `{"workflow_description": message, "conversation_id": conversation_id}`,
  - reads the returned `X-Conversation-Id` header,
  - **returns `(response_text, new_conversation_id)`** (tuple — first element is
    the chat reply, second updates `convo_state`),
  - on error, returns `(error_text, conversation_id)` so the thread id is **not**
    lost.

### 3. README — short note under "Where to go next" → becomes a real subsection

A few lines: what changed, why the backend must check ownership itself
(service_role bypasses RLS), and the naive context cap as the next thing to
improve.

`requirements.txt` / `.env` — no changes.

---

## Out of scope (call out, don't build)

- **Resetting the thread on Gradio's "clear/new chat" button.** For the MVP, a
  **page reload** starts a fresh thread (gr.State resets to None). Wiring the
  clear button to reset state is version-fragile; document it instead.
- A conversation **picker / sidebar** to resume *old* threads across sessions.
- Smarter context management (summarisation, token-aware truncation) beyond the
  naive last-20 slice.
- Auth on `GET /conversations/{id}/messages` (still open; tracked separately).

## Verification

1. `uvicorn main:app --reload` + `python app_frontend.py`, log in.
2. Ask a question, then a **follow-up that depends on the first** (e.g. "now make
   that a 3-step version"). The reply should reference the earlier answer.
3. In Supabase: **one** `conversations` row for the whole exchange, with **4+**
   messages under it (not two separate rows).
4. Pass a forged `conversation_id` (a real id owned by a different user) via curl
   → backend returns **403**; it must **not** append to someone else's thread.
5. Reload the page → next message starts a new conversation row.

---

## DONE — implementation log (handover notes)

Implemented and verified end-to-end against the live Supabase project + Groq.

### What changed
- **`main.py`**
  - `call_groq(user_content)` → `call_groq(turns)`: now takes the conversation so
    far (list of `{role, content}`, oldest first) and prepends the system prompt,
    so the model sees the whole thread. Meta/rate-limit logic unchanged.
  - New helper `resolve_conversation(conversation_id, user_id, first_message)`:
    if an id is passed, it must belong to the caller (explicit ownership check,
    because service_role bypasses RLS) → else `403 "That conversation isn't
    yours."`; if no id, opens a new conversation titled with the first 60 chars.
  - `/diagnose` now reads `conversation_id` from the body, resolves the thread,
    inserts the user message, **reloads the thread's messages (capped at last 20)**
    and feeds them to `call_groq`, then stores the answer. The `X-Conversation-Id`
    header is returned on the 200 path **and** the 429 path (no orphaned thread).
- **`app_frontend.py`**
  - Added `convo_state = gr.State(None)`.
  - `diagnose(message, history, token, conversation_id)` now sends
    `conversation_id` (when set), reads the `X-Conversation-Id` response header,
    and **returns `(reply, new_id)`**. On error it returns the existing id so a
    hiccup doesn't fork the thread.
  - `gr.ChatInterface(... additional_inputs=[token_state, convo_state],
    additional_outputs=[convo_state])` — reads the id and writes it back each turn.
    (Requires Gradio ≥5; project has 6.16.0.)
- **README** — added "Step 11 — Pick up the thread (conversation continuation)"
  before "Where to go next", in the existing teaching tone (the service_role /
  RLS ownership point is the mirror of Step 7).

### Tests run (all passed)
1. HTTP, turn 1 (no id) → 200, new conversation id in header. ✓
2. HTTP, turn 2 (same id) → 200, same thread; a context-only follow-up ("smallest
   first step from what you said") produced an invoice-specific answer → model had
   prior turn as context. ✓
3. DB: that conversation has **4 messages** in **one** row (not two rows). ✓
4. Forged id — nonexistent uuid → **403**; existing-but-not-mine (NULL-owned)
   id → **403**. ✓
5. Frontend `diagnose()` called directly: turn 1 sets id, turn 2 reuses it, reply
   is contextual (Zapier for a spreadsheet workflow). ✓
6. Frontend boots clean on the new code (HTTP 200), confirming Gradio accepts the
   `additional_outputs` wiring.

### Still open (unchanged from plan's out-of-scope)
- Gradio "clear/new chat" button does not reset `convo_state`; **page reload** is
  how you start a fresh thread.
- No sidebar to resume *old* threads across sessions; naive last-20 context cap;
  `GET /conversations/{id}/messages` still unauthenticated (separate follow-up).
