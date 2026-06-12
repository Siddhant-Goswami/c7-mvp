-- ============================================================================
--  Step 2: The schema  —  the domain model, turned into real tables
-- ============================================================================
--
--  Run this in the Supabase dashboard:  SQL Editor  ->  paste  ->  Run.
--  (Or split it: create `conversations` in the Table Editor by hand to
--   demystify it, then run the `messages` block here to own the SQL.)
--
--  Every line below is a promise from DOMAIN_MODEL.md. A spreadsheet accepts
--  anything; these tables REFUSE rows that break the promise. A database is a
--  spreadsheet with a bouncer.
-- ============================================================================


-- ----------------------------------------------------------------------------
--  conversations  —  one diagnosis session
-- ----------------------------------------------------------------------------
create table if not exists conversations (
    id          uuid        primary key default gen_random_uuid(),  -- identity: meaningless + permanent
    title       text,                                               -- nullable label, e.g. first 60 chars
    created_at  timestamptz not null default now()                  -- when it started
    -- user_id is added later, in the Auth step (02_auth.sql). One thing at a time.
);


-- ----------------------------------------------------------------------------
--  messages  —  one line in a conversation (from the user or the assistant)
-- ----------------------------------------------------------------------------
create table if not exists messages (
    id               uuid        primary key default gen_random_uuid(),
    conversation_id  uuid        not null references conversations(id),  -- the THREAD, now with a bouncer
    role             text        not null check (role in ('user', 'assistant')),  -- a promise a sheet can't keep
    content          text        not null,
    created_at       timestamptz not null default now()
);

--  Read the two important lines out loud:
--
--    references conversations(id)
--        -> "this message MUST point at a real conversation."
--           You cannot insert a message for a conversation that doesn't exist.
--
--    check (role in ('user', 'assistant'))
--        -> "role can ONLY be one of these two words." Nothing else gets in.


-- ============================================================================
--  Watch the database refuse you (the moment of the night)
-- ============================================================================
--  Try to insert a "ghost message" — one that points at a conversation that
--  does not exist. Uncomment and run it. It SHOULD fail:
--
--    insert into messages (conversation_id, role, content)
--    values (gen_random_uuid(), 'user', 'ghost message');
--
--    -- ERROR:  insert or update on table "messages" violates foreign key
--    --         constraint "messages_conversation_id_fkey"
--
--  That error is the system WORKING, not breaking. The foreign key just
--  defended the model we designed. Now do it the right way:
--
--    insert into conversations (title) values ('Aarav: first diagnosis');
--    select id from conversations;                    -- copy the uuid
--    insert into messages (conversation_id, role, content)
--    values ('<paste-uuid-here>', 'user', 'My team ships late every sprint.');
-- ============================================================================
