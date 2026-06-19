# Task: Lock the conversation-read endpoint (close the last open door)

## The problem, precisely

`GET /conversations/{conversation_id}/messages` (`main.py`) had **no auth and no
ownership check**. It read straight through the `service_role` client, which
**bypasses RLS** — so anyone could read **any** conversation's full message
history just by guessing/knowing its uuid. This was flagged as a real follow-up
in both `auth-login-flow.md` and `conversation-continuation.md`.

It was acceptable as a "memory survives" demo in README Step 7 (before identity
existed), but a genuine leak once real users arrived in Step 10.

## The fix (MVP)

Require a passport and confirm the conversation belongs to the caller — the same
guard the write path already uses. Factor that check into one helper so both
paths share it.

## Changes

### `main.py`
- New helper `assert_conversation_owner(conversation_id, user_id)`: looks up the
  conversation's `user_id` and raises `403 "That conversation isn't yours."` if it
  is missing or not the caller's. (Done in code because service_role bypasses RLS.)
- `resolve_conversation` refactored to call the helper (no behaviour change).
- `get_messages` now takes `user_id: str = Depends(require_user_id)` (→ `401` with
  no token) and calls `assert_conversation_owner` before reading (→ `403` for a
  foreign/unknown id).

### README
- Extended the Step 11 security paragraph: the read endpoint is now closed the
  same way as the write path, both via the one `assert_conversation_owner` guard.

No `.env` / `requirements.txt` / schema changes.

## Out of scope
- Pagination on the read endpoint; logout; token refresh.

## DONE — implementation log

Implemented and verified against the live project.

### Tests run (all passed)
1. `GET /conversations/{my_id}/messages` with **no token** → **401** "Please log
   in first." ✓
2. With a valid token but a **foreign** id (NULL-owned demo row) → **403** "That
   conversation isn't yours." ✓
3. With a valid token and **my own** conversation id → **200**, messages returned. ✓

### Notes
- Both the read and write paths now funnel conversation-id ownership through the
  single `assert_conversation_owner` helper — one place to get right.
- Also cleared the `events` table (per the teaching-cleanliness request) so the
  `/admin` dashboard starts at zero.
