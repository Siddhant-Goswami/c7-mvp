# Task: Add a login / signup flow to the frontend (close the open API)

## The problem, precisely

The auth *infrastructure already exists* — this task is wiring, not new architecture:

- **Supabase Auth** runs the users table (`auth.users`) and issues JWTs. (`db/02_auth.sql`)
- **RLS policies** already gate every row on `auth.uid()`. (`db/03_policies.sql`)
- **The backend already validates JWTs** in `get_user_id()` (`main.py`), handing the
  token to Supabase and trusting only what Supabase says.

Two gaps remain, and together they mean *anyone can call the APIs anonymously*:

1. **The frontend has no login UI.** `app_frontend.py` (Gradio) sends no token, so every
   `/diagnose` call is anonymous and conversations are written with `user_id = NULL`.
2. **Backend auth is optional.** `get_user_id` returns `None` when no token is present
   instead of rejecting — so a caller with no passport still gets served.

## The fix (MVP)

Make the frontend authenticate the user against Supabase (using the **public anon key**,
which is safe *because* RLS guards every row), get a JWT, and send it to the backend on
every call. Then make the backend **require** that JWT.

The anon key is the one key that is *meant* to ship to the browser — this is the payoff of
the whole RLS lesson. The service_role key stays server-only, untouched.

---

## Changes

### 1. `main.py` — require a passport for `/diagnose`

- Add a small dependency `require_user_id()` that reuses `get_user_id()` but raises
  `401` when the result is `None` (no token). Keep the original optional `get_user_id`
  intact so the teaching narrative ("optional in L06") still reads true.
- Point `/diagnose` at `Depends(require_user_id)`.
- Net effect: no passport → `401`. A forged/expired token was already rejected.

(Out of scope but noted: `GET /conversations/{id}/messages` has no auth and reads via
service_role — it can leak any conversation by id. Flag as a follow-up, not in this MVP.)

### 2. `app_frontend.py` — add the login/signup gate

Rewrite from a bare `gr.ChatInterface` to `gr.Blocks` with two views:

- **Login view (visible at start):** email, password (`type="password"`), **Log in** and
  **Sign up** buttons, and a status line.
- **Chat view (hidden until authed):** the existing `gr.ChatInterface`, with the JWT
  threaded in via `additional_inputs=[token_state]`.
- A `gr.State` holds the `access_token`.

Auth handlers use a Supabase client built with the **anon** key:
- `supabase.auth.sign_in_with_password({email, password})`
- `supabase.auth.sign_up({email, password})` — if email confirmation is on, no session is
  returned, so show "check your email, then log in"; if off, a session comes back and we
  log them straight in.
- On success: store `session.access_token` in state, hide login view, show chat view.
- On failure: show the error in the status line, stay on the login view.

`diagnose(message, history, token)` sends `Authorization: Bearer <token>` to the backend.

### 3. `.env.example` — frontend needs the public keys

Add (clearly marked as the *publishable* pair, safe for the browser):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

`requirements.txt` already has `supabase`, so no dependency change.

### 4. README — one short subsection

A brief "Step: the login flow" note matching the existing teaching tone: why the anon key
is the right key here, and how the JWT flows browser → frontend → backend → Supabase.

---

## Out of scope (call out, don't build)

- Logout button, session persistence across refresh, token refresh on expiry.
- Auth on the `/conversations/.../messages` read endpoint.
- Styling beyond Gradio defaults.

## Verification

1. `uvicorn main:app` + `python app_frontend.py`.
2. Hitting `/diagnose` with no token → `401` (curl test).
3. Sign up / log in in the UI → chat works, and a new `conversations` row carries the
   real `user_id` (not NULL).

---

## DONE — implementation log (handover notes)

Implemented and tested against the live Supabase project (`nytasdxacrkbbyvmodhh`).

### What changed
- **`main.py`**: added `require_user_id()` dependency that reuses the optional
  `get_user_id()` but raises `401 "Please log in first."` when no token is present.
  `/diagnose` now depends on `require_user_id` (was the optional `get_user_id`). The
  optional version is kept intact for narrative continuity.
- **`app_frontend.py`**: rewritten from a bare `gr.ChatInterface` to `gr.Blocks` with a
  login view (email, password, Log in / Sign up, status line) gating the chat view. Auth
  uses a Supabase client built with the **anon** key. `log_in` / `sign_up` handlers return
  `(token_state, login_view_update, chat_view_update, status)`. The JWT is threaded into
  the chat via `additional_inputs=[token_state]` and sent as `Authorization: Bearer`.
- **`.env.example`**: added `SUPABASE_ANON_KEY` (the publishable key for the frontend).
- **`README.md`**: added "Step 10 — Lock the door (the login flow)".

### Important runtime fact discovered
- The project's **"Confirm email" is ON** (the user toggled it on mid-task). So sign-up
  returns **no session** until the user clicks the email link; the UI shows
  "Account created. Check your email to confirm, then log in." The `session is not None`
  branch (immediate login) only fires if confirmation is turned off.
- Supabase's built-in SMTP has a low **email-send rate limit**; rapid repeated sign-ups
  return `"email rate limit exceeded"`. Fine in normal use, worth knowing when testing.

### Tests run (all passed)
1. Frontend `sign_up` with confirm-on → no token, "check your email" status. ✓
2. `log_in` with wrong password / empty fields → graceful error, no token. ✓
3. Confirmed a test user via SQL → `log_in` returns a token and flips the views
   (login hidden, chat shown). ✓
4. Token resolves to the correct user id/email via `supabase.auth.get_user(token)` (the
   exact logic the backend's `get_user_id` uses). ✓
5. `require_user_id(None)` → `HTTPException 401`; `require_user_id(<id>)` → passthrough. ✓
6. All test users deleted afterward; `auth.users` back to 1 row.

### NOT tested live (could not boot backend locally)
- No local `.env` with `GROQ_API_KEY` / `service_role` key, so `uvicorn main:app` was not
  run end to end. The new backend guard was unit-tested in isolation; the unchanged JWT
  path is exercised by test #4. To confirm end to end: create `.env` (now also needs
  `SUPABASE_ANON_KEY`), run both processes, sign up, confirm via email, log in, chat, and
  check a new `conversations` row carries the real `user_id`.

### Known follow-ups (out of scope, real)
- `GET /conversations/{id}/messages` still has **no auth** and reads via service_role — it
  can leak any conversation by id. Lock it next.
- No logout button, no session persistence across refresh, no token-refresh on expiry.
