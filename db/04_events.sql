-- ============================================================================
--  Step 9: Observability  —  the same database is your first analytics warehouse
-- ============================================================================
--
--  The Verifier's Rule, one level up: only SHIP what you can OBSERVE. A product
--  you cannot see is a product you cannot trust. When it breaks at 2am, "what do
--  I even look at?" should have an answer.
--
--  And the answer needs NO new infrastructure. No Mixpanel, no Datadog, no
--  Grafana. Every diagnosis already writes rows to Postgres, so analytics is
--  mostly a SELECT away. We add ONE more table next to the data we already keep:
--  a structured record of every request — how long it took, what it cost in
--  tokens, whether it succeeded, and how much of our LLM budget is left.
--
--  When a SELECT stops being enough, you graduate to PostHog or Sentry — the
--  same "know your tripwire, upgrade the one thing" move you make for the
--  database. Not before.
-- ============================================================================


-- ----------------------------------------------------------------------------
--  1. The events table  —  one row per request
-- ----------------------------------------------------------------------------
create table if not exists events (
    id                 uuid        primary key default gen_random_uuid(),
    created_at         timestamptz not null default now(),
    user_id            uuid        references auth.users(id),  -- who made the call (may be null)
    route              text        not null,                  -- e.g. '/diagnose'
    status             int         not null,                  -- 200, 429, 500
    latency_ms         int,                                   -- how long it took
    input_tokens       int,                                   -- prompt size
    output_tokens      int,                                   -- answer size
    groq_remaining_rpm int,                                   -- requests left this minute (from Groq's header)
    bottleneck         text                                   -- optional category from the diagnosis
);


-- ----------------------------------------------------------------------------
--  2. Lock it down  —  deny by default does the work for us
-- ----------------------------------------------------------------------------
--  Same lesson as Step 7: turn RLS on, write NO select policy for ordinary
--  users. With no policy, `authenticated` reads back an empty array — ordinary
--  users can NEVER read the metrics table. That's correct: analytics is yours,
--  not theirs.
--
--  Your service_role backend (and the /admin dashboard it serves) BYPASSES RLS,
--  so it reads everything. We get a private metrics table for free, with one
--  fewer thing to get wrong.
alter table events enable row level security;
-- (Deliberately no `create policy ... for select to authenticated` here.)
