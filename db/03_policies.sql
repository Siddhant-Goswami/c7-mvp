-- ============================================================================
--  Step 7: Row-Level Security (RLS)  —  the rule lives WITH the data
-- ============================================================================
--
--  The parked question from earlier: "Why is a public key safe?"
--  We now have something we didn't before: IDENTITY. Every request can carry a
--  passport (JWT). And the database can read that passport itself.
--
--  In L06, rules lived in the backend because that was the only machine we
--  controlled. The database is ALSO a machine we control. RLS is a rule that
--  lives WITH the data: a guard at every shelf, checking each row against the
--  passport. The public `anon` key is safe because it only opens the door to a
--  room where every shelf has its own guard.
--
--  `auth.uid()` = "the user id in the passport." The SQL below is just plain
--  English, compressed.
-- ============================================================================


-- ----------------------------------------------------------------------------
--  1. Turn RLS on  (break everything on purpose)
-- ----------------------------------------------------------------------------
--  In Supabase, RLS is usually ON by default for new tables. Make it explicit.
alter table conversations enable row level security;
alter table messages      enable row level security;

--  Right now there are NO policies. Re-run the anon-key query and you get back
--  ZERO rows — an empty array. That is DENY BY DEFAULT, and it is correct:
--  if RLS defaulted to "allow", every forgotten policy would be a data breach.
--  The scary default is the safe default. (Your service_role backend still
--  works, because service_role BYPASSES RLS — which is exactly why that key
--  must never leave the server.)


-- ----------------------------------------------------------------------------
--  2. conversations  —  you may only touch your own
-- ----------------------------------------------------------------------------

-- English: "A user may READ a conversation only if its user_id is theirs."
create policy "read own conversations"
on conversations for select
to authenticated
using (auth.uid() = user_id);

-- English: "A user may CREATE a conversation only stamped with their own id."
create policy "create own conversations"
on conversations for insert
to authenticated
with check (auth.uid() = user_id);

--  using       = the rule for rows that already EXIST (reading).
--  with check  = the rule for rows TRYING TO GET IN (writing).


-- ----------------------------------------------------------------------------
--  3. messages  —  you may only touch messages in your own conversations
-- ----------------------------------------------------------------------------
--  A message has no user_id of its own. Its owner is decided by the
--  conversation it belongs to — and the FOREIGN KEY from Step 2 is what makes
--  this sentence possible. The thread became a security boundary.

-- English: "Read a message only if its conversation belongs to you."
create policy "read messages in own conversations"
on messages for select
to authenticated
using (
    exists (
        select 1 from conversations c
        where c.id = messages.conversation_id
          and c.user_id = auth.uid()
    )
);

-- English: "Write a message only into a conversation that belongs to you."
create policy "write messages in own conversations"
on messages for insert
to authenticated
with check (
    exists (
        select 1 from conversations c
        where c.id = messages.conversation_id
          and c.user_id = auth.uid()
    )
);


-- ============================================================================
--  4. The two-user test  (prove the walls hold)
-- ============================================================================
--  With Aarav's JWT -> only Aarav's rows.
--  With Meera's JWT -> only Meera's rows.
--  With the bare anon key (no passport) -> empty array.
--
--    curl 'https://<project-ref>.supabase.co/rest/v1/conversations?select=*' \
--      -H "apikey: <anon-key>" \
--      -H "Authorization: Bearer <a-user-JWT-or-the-anon-key>"
--
--  Common gotcha: rows created earlier by the backend have user_id = NULL, so
--  even your own JWT call returns empty. Claim them once:
--
--    update conversations set user_id = '<your-sub-from-jwt.io>'
--    where user_id is null;
-- ============================================================================
