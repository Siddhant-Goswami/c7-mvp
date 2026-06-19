# The Workflow Diagnoser — A Teaching Walkthrough

A single, logical chain you can teach front-to-back. Each step exists **only to
close the gap the previous step left open.** Nobody adds a database "because apps
have databases" — we add it the moment the app forgets something it shouldn't.
That cause-and-effect is the whole lesson. The architecture never really changes;
we just keep answering the next honest question.

> **What we're building:** a chat box where a person describes a task they repeat
> at work, and an AI replies with the repeatable steps, the automation
> opportunities, and a suggested MVP. Two small Python files grow, one honest
> question at a time, into a real, deployed, multi-user AI product.

---

## The one idea everything hangs on

```
  Browser (a person types)
        │
        ▼
  app_frontend.py   ← the UI            (runs where the USER is — assume the world can see it)
        │  POST /diagnose
        ▼
  main.py           ← the backend       (runs where WE are — the only place secrets live)
        │  ├── calls ─────────────────► Groq        (the AI model)
        │  └── reads/writes ──────────► Supabase     (Postgres database)
```

Say this once and keep returning to it:

> **The frontend runs on a machine the user controls, so anything it knows, the
> world knows. The backend runs on a machine we control, so the secret key lives
> there and only there.**

Every later step is a variation on this one sentence. When in doubt during the
class, point back at this diagram and ask: *"which machine is this running on,
and what is it therefore allowed to know?"*

---

## Step 0 — The setup (5 minutes, do it together)

- **Python 3.9+**, a terminal, an editor.
- A **virtual environment** — an isolated sandbox so this project's packages
  don't collide with anything else:
  ```bash
  python -m venv .venv
  source .venv/bin/activate      # Windows: .venv\Scripts\activate
  ```
- A **shopping list** of packages in `requirements.txt`, installed with
  `pip install -r requirements.txt`:

  | Package    | Its job                                         |
  | ---------- | ----------------------------------------------- |
  | `fastapi`  | builds the backend API (holds the secret key)   |
  | `uvicorn`  | the web server that runs FastAPI                |
  | `groq`     | client for talking to the Groq AI models        |
  | `gradio`   | builds the chat UI with almost no code          |
  | `requests` | lets the frontend call the backend              |
  | `supabase` | client for the database (added later)           |
  | `python-dotenv` | loads secrets from a `.env` file            |

**Teaching note:** a virtual environment isn't ceremony — it's the same
"isolate things so they don't interfere" instinct that later makes us split
frontend from backend. Same idea, different scale.

---

## Step 1 — The backend brain (`main.py`)

**The question:** *how does a chat message become an AI answer?*

The backend exposes one endpoint, `/diagnose`. It takes a workflow description
and returns the model's analysis. The shape of an LLM call is just a list of
**messages**:

- a **system** message that sets the AI's job ("you are a workflow diagnosis
  assistant…"),
- a **user** message that is whatever the person typed.

```python
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))   # key comes from the environment, never hard-coded

completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a workflow diagnosis assistant..."},
        {"role": "user",   "content": user_content},
    ],
)
return completion.choices[0].message.content
```

**The one thing to land:** `os.environ.get("GROQ_API_KEY")` reads the key from
the *environment*, not from the code. The secret never gets typed into a file
that could end up on GitHub. This is the safe sentence from the diagram, in code.

**Run and prove it with no UI at all.** FastAPI gives you a free interactive
page — open `http://127.0.0.1:8000/docs`, click `POST /diagnose` → **Try it
out**, and send:
```json
{ "workflow_description": "Every Monday I copy sales numbers from email into a spreadsheet and send a summary." }
```
You get a plain-text diagnosis back. *The brain works before any chat box exists.*

---

## Step 2 — The chat box (`app_frontend.py`)

**The gap Step 1 left:** a `/docs` page is not a product. People need a chat box.

Gradio builds a full chat UI from a single function. That function does one
thing: forward the message to the backend and show the reply.

```python
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/diagnose")

def diagnose(message, history):
    response = requests.post(BACKEND_URL, json={"workflow_description": message}, timeout=60)
    return response.text

gr.ChatInterface(diagnose, title="Workflow Diagnoser").launch()
```

**The one thing to land:** notice what is *not* here — **no API key.** The
frontend never sees the secret. It only knows the backend's address. If a curious
user opens the browser dev tools, there is nothing to steal.

---

## Step 3 — Why two files? (the split, stated out loud)

**The question a sharp student will ask:** *"this is more work — why not one file?"*

- The **frontend** runs where users are. Anything it knows, the world can see.
- The **backend** runs on a server we control. The key lives only here.

So the secret stays safe, and either half can be swapped or redeployed
independently. **This frontend/backend split is how almost every real AI product
is built.** It's not an optimization; it's the security boundary.

---

## Step 4 — Ship it, but *right-sized* (find the real bottleneck)

**The gap:** it's perfect on localhost and useless to the world.

The interesting question isn't *how* to ship — it's *how big* to build. This is
where people over-engineer: Kubernetes, autoscaling, Redis, queues… for an app
nobody uses yet. Instead, **do the napkin math first.** Say ~250 users, a few
diagnoses each:

| Layer | Free-tier ceiling | Our load | Verdict |
| --- | --- | --- | --- |
| Supabase Postgres | ~500 MB | a few MB | a rounding error |
| Supabase Auth | 50,000 monthly users | 250 | 0.5% of the ceiling |
| **Groq LLM** | **~30 requests/min** | 250 clicking at once | **this is the one** |

**Conclusion, derived not asserted:** we need *none* of the things people reach
for. The limit that breaks you first lives **outside your own code** — it's the
LLM rate cap, not your server. (Second tripwire: free databases fall asleep after
~7 idle days and take ~30s to wake — fix with a daily ping, not a bigger plan.)

Then deploy the two halves separately:
- **Backend → Render** (a web service; set `GROQ_API_KEY` and the Supabase keys
  as environment variables in the dashboard).
- **Frontend → Hugging Face Spaces** (a Gradio space; set `BACKEND_URL` to the
  Render URL + `/diagnose`).

The key never leaves the server. **The lesson is the table, not the deploy
buttons:** scale the one tier that actually bites.

---

## Step 5 — Give it a memory (`db/01_schema.sql`)

**The gap:** close the tab and the plan is gone. It only ever lived in RAM. We
move it onto **disk** in a real Postgres database (via Supabase).

First **model it, then store it** — two entities with a one-to-many relationship:

```
conversation (one diagnosis session)  ──< has many >──  message (one line: user OR assistant)
```

Turned into tables, with two promises a spreadsheet can't keep:

```sql
create table messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id),          -- FOREIGN KEY: must point at a real conversation
    role            text not null check (role in ('user','assistant')),  -- CHECK: role can only be these two words
    content         text not null,
    created_at      timestamptz not null default now()
);
```

**The moment of the lesson:** try to insert a "ghost message" pointing at a
conversation that doesn't exist — the database **refuses it.** That error is the
system *working*. A spreadsheet accepts anything; a database is a spreadsheet
with a bouncer.

The backend now wraps memory around the same brain — open a conversation, store
the question, think, store the answer:

```python
convo = supabase.table("conversations").insert({"title": user_content[:60]}).execute()
supabase.table("messages").insert({"conversation_id": ..., "role": "user", "content": user_content}).execute()
plan = call_groq(user_content)
supabase.table("messages").insert({"conversation_id": ..., "role": "assistant", "content": plan}).execute()
```

**Prove memory survives:** run one diagnosis, **restart the server**, then call
`GET /conversations/{id}/messages` — the messages are still there, because they
live on disk, not in the process.

> **The two keys (say this slowly):** `service_role` is the **master key** — it
> bypasses every rule and lives **only** in the backend. `anon` is the **public**
> key meant for browsers; it's safe *only because* of Step 7's RLS. Never let
> `service_role` near a browser.

---

## Step 6 — Who is asking? (`db/02_auth.sql`)

**The gap:** Aarav isn't our only user. Meera signs up tomorrow. Whose
conversations are whose?

We do **not** build a users table or hash passwords. **Supabase Auth** already
runs `auth.users` and issues a **JWT** on login — a *passport*: signed,
unforgeable, carried on every request. We just add a `user_id` so we know who
**owns** each conversation:

```sql
alter table conversations add column user_id uuid references auth.users(id);
```

In the backend, identity comes from the passport, **never** from a claim in the
request body (the frontend can lie about who it is; the JWT can't be forged):

```python
def get_user_id(authorization):
    token = authorization.replace("Bearer ", "")
    res = supabase.auth.get_user(token)   # hand the token to Supabase; trust only what it says
    return res.user.id
```

---

## Step 7 — The rule lives *with* the data (`db/03_policies.sql`)

**The parked question from Step 5:** *"why is a public key safe to put in a
browser?"* Now we can answer it, because we finally have **identity.**

In the early steps, rules lived in the backend because that was the only machine
we controlled. **The database is also a machine we control.** Row-Level Security
(RLS) is a rule that lives *with the data* — a guard at every shelf, checking
each row against the passport:

```sql
alter table conversations enable row level security;     -- turn it on: now NOBODY can read, deny-by-default

create policy "read own conversations" on conversations
  for select to authenticated using (auth.uid() = user_id);   -- "only rows whose user_id is yours"
```

- `auth.uid()` = "the user id in the passport."
- Turn RLS on with no policies and you get back **zero rows** — *deny by
  default.* The scary default is the safe default: a forgotten policy is a closed
  door, never an open one.
- `service_role` **bypasses RLS** — which is exactly why it stays on the server.

**Now the answer:** the public `anon` key is safe in a browser because it only
opens the door to a building **where every shelf has its own guard.**

---

## Step 8 — See it working (`db/04_events.sql`)

**The gap:** it's live. Is it working? For whom? How fast? When it breaks at 2am,
what do you even look at? Right now: nothing. **Only ship what you can observe.**

And it needs **no new infrastructure** — the same Postgres is our analytics
warehouse. One more table; every `/diagnose` logs a row:

```sql
create table events (
    route text, status int, latency_ms int,
    input_tokens int, output_tokens int,
    groq_remaining_rpm int,                  -- requests left this minute, read from Groq's response header
    user_id uuid references auth.users(id)
);
alter table events enable row level security;   -- and NO read policy: analytics is ours, not the users'
```

Two routes turn rows into a live view:
- **`GET /metrics`** — one SELECT over the last 500 events → four numbers: total
  diagnoses, how many got rate-limited (429), average latency, Groq requests left.
- **`GET /admin`** — a tiny HTML page that polls `/metrics` every 2 seconds.
  **Put it on a projector and watch the numbers tick.**

**The payoff, live:** under load Groq's ~30 req/min cap returns a `429`; the
backend catches it and returns a graceful *"you are in line"* instead of crashing;
the 429 count climbs on the dashboard. You can **see** the exact bottleneck Step 4
predicted on the napkin — and turn the one right knob.

```python
try:
    plan, meta = call_groq(user_content)
except RateLimitError:                       # the predicted tripwire, handled gracefully
    log_event("/diagnose", 429, latency_ms, user_id)
    return PlainTextResponse("You are in line. Try again in a few seconds.", status_code=429)
```

---

## Step 9 — One product, one keystroke (the reveal)

**The realization:** the architecture never moves — only what the product is
*for*. The backend ships **two** system prompts and a flag:

- `WORKFLOW_PROMPT` — diagnose a task you repeat at work (where we started).
- `JOURNEY_PROMPT` — diagnose where a builder is, the gap to where they want to
  go, and their single current bottleneck.

`PROMPT_MODE` picks one. Its boot default comes from an env var, but you flip it
**live, in memory, with no redeploy** (a redeploy risks a cold start at the worst
moment):

```bash
curl -X POST 'http://127.0.0.1:8000/admin/mode?mode=journey'
```

Same auth, same RLS, same deploy, same dashboard. **Only the prompt changed.**
That is the whole lesson: once you own the shape, changing what a product *does*
is a one-line change.

---

## Step 10 — Lock the door (the login flow)

**The last gap:** until now the frontend sent no passport, so `/diagnose` served
*anyone*. The database was private (RLS guarded every row), but the API in front
of it was wide open.

Two moving parts:

1. **The frontend grows a login gate** (`app_frontend.py`). Before the chat
   appears, the user logs in or signs up using the **public anon key**. Supabase
   hands back a JWT; we keep it for the session and attach it to every backend
   call as `Authorization: Bearer <token>`.

   ```python
   supabase.auth.sign_in_with_password({"email": email, "password": password})
   # ...then on every chat call:
   requests.post(BACKEND_URL, json=..., headers={"Authorization": f"Bearer {token}"})
   ```

2. **The backend now *requires* the passport** (`main.py`). The old `get_user_id`
   was optional (no token → no user) — that optionality *was* the open door. A new
   `require_user_id` closes it: no token → `401`, full stop.

   ```python
   def require_user_id(user_id = Depends(get_user_id)):
       if user_id is None:
           raise HTTPException(status_code=401, detail="Please log in first.")
       return user_id
   ```

```bash
# No passport now bounces:
curl -i -X POST http://127.0.0.1:8000/diagnose -d '{"workflow_description":"..."}'
# -> HTTP/1.1 401 Unauthorized   {"detail":"Please log in first."}
```

The anon key being safe in the browser is the **payoff of the entire RLS lesson**:
it opens the door to a building where every shelf has its own guard.

---

## The chain, in one breath

> A **brain** that answers (Step 1) needs a **face** people can use (Step 2),
> kept separate so the **secret stays safe** (Step 3). To reach the world we
> **right-size** the deploy and find the real bottleneck (Step 4). It **forgets**,
> so we give it a **database** (Step 5). With many users we must know **who is
> asking** (Step 6) and let the **data guard itself** (Step 7). Live, we must be
> able to **see it work** (Step 8). Owning the shape, we can **change what it does
> in one keystroke** (Step 9). Finally we **lock the front door** (Step 10).

Every step was forced by the gap the last one left. That's the thing to teach:
not the libraries, but the *sequence of honest questions.*

---

## Running it live (the demo runbook)

Confirmed working end-to-end against the live Groq + Supabase project.

**Prep (`.env` in the project root — gitignored, never committed):**
```
GROQ_API_KEY=...                 # from console.groq.com
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...    # Settings → API → service_role (master key, server-only)
SUPABASE_ANON_KEY=...            # Settings → API → anon (public, safe for the browser)
```

**Database:** in the Supabase SQL Editor run, in order:
`db/01_schema.sql` → `db/02_auth.sql` → `db/03_policies.sql` → `db/04_events.sql`.

**Run the two halves** (two terminals, venv active):
```bash
uvicorn main:app --reload          # terminal 1 → backend on :8000
python app_frontend.py             # terminal 2 → UI on :7860
```

**The demo sequence that lands every beat:**

| Beat | Do this | What the room sees |
| --- | --- | --- |
| Brain works | `POST /diagnose` from `/docs` (or curl with a token) | a real diagnosis, no UI |
| Door is locked | `curl -X POST /diagnose` with **no** token | `401 Please log in first.` |
| Full product | log in → ask a question in the chat | answer appears |
| Memory is real | restart backend → `GET /conversations/{id}/messages` | the messages survived |
| Observability | open `/admin` on the projector | numbers tick every 2s |
| **The reveal** | `curl -X POST '/admin/mode?mode=journey'` then ask again | same app, different product |

**Two gotchas learned the hard way — pre-empt them before class:**
- **Cold start.** Free hosts and the free database sleep on idle; the first
  request after a quiet spell is slow. **Hit the URL once to wake it before you
  demo.**
- **Email rate limit.** Supabase's built-in SMTP rate-limits signups
  (`429 email rate limit exceeded`). For a live class, **pre-create confirmed
  accounts** (insert into `auth.users` via SQL with `email_confirmed_at` set)
  rather than having 30 students sign up at once. Ironically, this is the same
  "external infra is your real tripwire" lesson from Step 4 — hitting you for real.

---

## Where to take it next

- Change the **system prompt** to make the AI an expert in something else.
- Try a different Groq **model** in the `model=` line.
- Add input validation, a logout button, or a Gradio theme.

You've learned the core shape of an AI app: **a thin UI, a backend that guards
the secret, a model that thinks, and a database that remembers.** Everything else
is a variation on this.
