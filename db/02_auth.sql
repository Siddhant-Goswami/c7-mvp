-- ============================================================================
--  Step 6: Auth  —  "who is asking?"
-- ============================================================================
--
--  Aarav is no longer our only user. Meera signs up tomorrow. Whose
--  conversations are whose? We need to (a) know who is asking, and (b) record
--  who owns each conversation.
--
--  (a) WHO IS ASKING is handled by Supabase Auth. When a user signs up / logs
--      in, Supabase issues a JWT — a passport: signed, unforgeable, carried on
--      every request. Supabase also runs the users table for you, at
--      `auth.users` (hashed passwords and all). You do NOT build your own.
--
--      Create a test user from the terminal (mechanics laid bare, no UI):
--
--        curl -X POST 'https://<project-ref>.supabase.co/auth/v1/signup' \
--          -H "apikey: <anon-key>" \
--          -H "Content-Type: application/json" \
--          -d '{"email": "aarav@demo.100x", "password": "a-strong-password"}'
--
--      The response contains an `access_token`. Paste it into jwt.io: `sub` is
--      the user's uuid, `exp` is when the passport expires. It is SIGNED, not
--      encrypted — anyone can read it, nobody can forge it.
-- ============================================================================


-- (b) WHO OWNS IT. Schemas aren't carved in stone; we AMEND them with ALTER.
--     Add a user_id to conversations that points at the managed users table.
alter table conversations
    add column if not exists user_id uuid references auth.users(id);

--  references auth.users(id)  ->  the second relationship from the domain model:
--  one user owns many conversations. This column is what lets us later say
--  "only show me MY rows."


-- ============================================================================
--  Forgot-password is just a template + an endpoint (shown, never built):
--
--    curl -X POST 'https://<project-ref>.supabase.co/auth/v1/recover' \
--      -H "apikey: <anon-key>" \
--      -H "Content-Type: application/json" \
--      -d '{"email": "aarav@demo.100x"}'
--
--  Edit the email itself under  Authentication -> Email Templates.
-- ============================================================================
