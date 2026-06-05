# Lecture 05 — Building APIs with FastAPI: A Step-by-Step Code Guide

> *You wrote the contract. Today you become the machine that answers it.*

This guide turns Lecture 05 into something you **build with your hands**. Each section
below maps to a section of the lecture. For each concept there is:

1. **The idea** — one paragraph, the "why."
2. **The code** — what to type, and where it lives in this repo.
3. **An exercise** — something you do, run, or break, so the concept lands in your fingers, not just your notes.

Work top to bottom. Do not skip the exercises. *If you cannot explain it, you have not built it.*

The finished code for every step already lives in this repo, so you can check yourself:

| File | What it is |
|------|------------|
| `main.py` | The FastAPI backend. The thing at the address that answers the call. |
| `app_frontend.py` | The thin Gradio frontend that calls your backend over the internet. |
| `diagnoser.py` | The system from L04 — still here, still the asset. |
| `Dockerfile` | The recipe Hugging Face uses to run your backend Space. |
| `requirements.txt` | Everything to install. |

---

## Setup (once, before you start)

```bash
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here        # macOS / Linux
# setx GROQ_API_KEY "your_key_here"      # Windows PowerShell, then open a new terminal
```

Get a key at https://console.groq.com/keys. **Do not paste it into any file.** You will
feel *why* in Section 1.

---

## Section 1 — The Problem That Forces a Backend

**The idea.** A frontend is public: the browser downloads it, View Source shows
everything. A key is a secret: whoever holds it can spend your money. A secret cannot
live in a public place — so it must live on a machine you control that the user never
sees. That machine is the **backend**. The backend is not a design choice; it is a
*consequence* of needing a secret.

**Exercise 1.1 — Find the secret you must hide.**
Open `diagnoser.py` and find this line:

```python
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
```

Now answer in writing (one sentence each):
- If you pasted your real key in place of `os.environ.get(...)` and deployed, who could read it?
- Where does the key come from *instead*, and why is that safe?

**Exercise 1.2 — Prove the frontend is public.**
Run the L04 Gradio app (`python app_gradio.py`), open it in a browser, and use
**View Source** / DevTools. Confirm you can read the frontend code. Write one sentence:
*"A secret in this file would be visible because ______."*

> ✅ **Checkpoint:** You can say, out loud, why a secret can never live in the frontend.

---

## Section 2 — What Has To Exist Behind an Address

**The idea.** Anything that answers an API call does six jobs, every time:

| # | Job | Contract word |
|---|-----|---------------|
| 1 | **Listen** at an address + path | WHERE |
| 2 | **Route** the call by method + path | ACTION |
| 3 | **Read** the incoming request | SEND (input) |
| 4 | **Run** the logic | — |
| 5 | **Return** an answer in the agreed shape | BACK (output) |
| 6 | **Reject** anything that does not match | — |

A bundle that does these six jobs is a **web framework**. FastAPI is one.

**Exercise 2.1 — Label the six jobs.**
Open `main.py`. For each of the six jobs above, write down the **line number** in `main.py`
that does it. (Hint: some live in one line, like `@app.post("/diagnose", ...)`.)

> ✅ **Checkpoint:** You can point at the line for each of the six jobs.

---

## Section 3 — CRUD: The Four Verbs of Any System

**The idea.** Anything that holds information supports exactly four operations:
**C**reate, **R**ead, **U**pdate, **D**elete. They map onto HTTP methods you already know.

| Verb | HTTP method | Where you've met it |
|------|-------------|---------------------|
| Read | GET | Open-Meteo weather call |
| Create | POST | Your LLM call with a JSON body |
| Update | PUT / PATCH | Not yet (Lecture 07) |
| Delete | DELETE | Not yet (Lecture 07) |

**Exercise 3.1 — Classify your endpoints.**
`main.py` has two endpoints. For each, name (a) the HTTP method, (b) the CRUD verb,
(c) why it is that verb. Then answer: *Why does your app use only two of the four verbs today?*

> ✅ **Checkpoint:** You can name all four CRUD verbs and explain which two are silent and why.

---

## Section 4 — FastAPI Hello World: The Contract Made Runnable

**The idea.** The smallest possible API. Four lines that *listen* and *answer*.

**The code** (already at the top of `main.py`):

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, builder"}
```

**Exercise 4.1 — Run it.**
```bash
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/ . You should see the JSON message.

**Exercise 4.2 — Map every line to the contract.**
Write the contract word next to each line:
- `app = FastAPI()` → ______
- `@app.get("/")` → ______ + ______
- `def read_root():` → ______
- `return {...}` → ______

**Exercise 4.3 — Publish your contract.**
Open http://127.0.0.1:8000/docs . This is the auto-generated Swagger UI — *you publishing a
contract* other engineers and tools can read and call. Click `GET /` → **Try it out** →
**Execute**. Read the response.

> ✅ **Checkpoint:** You crossed from *consumer* of contracts to *provider* of one.

---

## Section 5 — Pydantic: Enforcing the Shape

**The idea.** Right now nothing stops a caller from sending garbage. Pydantic turns your
paper contract into a **gatekeeper**: FastAPI rejects any request that doesn't match the
declared shape, *before your logic runs*.

**The code** (in `main.py`):

```python
from pydantic import BaseModel

class DiagnoseRequest(BaseModel):
    workflow_description: str
    tools_used: list[str] = []
    biggest_pain: str = ""

class DiagnoseResponse(BaseModel):
    repeatable_steps: list[str]
    automation_opportunities: list[str]
    suggested_mvp: str
```

**Exercise 5.1 — Trigger a 422 on purpose.**
With the server running, go to `/docs`, open `POST /diagnose`, **Try it out**, and send a
body that is *missing* `workflow_description`:

```json
{ "tools_used": ["Jira"], "biggest_pain": "too slow" }
```

Read the error. What status code came back? Which field does the error name? Write down,
in one sentence, *who* is at fault for a 422 — the caller or the server.

**Exercise 5.2 — Make the contract stricter.**
Add a fourth field to `DiagnoseRequest`, e.g. `team_size: int`. Restart, and send a request
with `"team_size": "lots"` (a string, not an int). What happens? Then remove your change.

> ✅ **Checkpoint:** You have seen the spec *reject* a request before any logic ran.

---

## Section 6 — Implementing /diagnose (Stub First)

**The idea.** Prove the deterministic skeleton works **before** adding the unpredictable LLM.
Hardcode a golden output. If this works, you know the plumbing is sound — so when the LLM
later misbehaves, the problem is the model, not the pipes.

**The code** lives in `main.py`. The real version calls the LLM, but you can study the
stub shape in the guide below:

```python
@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest):
    return DiagnoseResponse(
        repeatable_steps=["check Jira", "build the report", "send it on Slack"],
        automation_opportunities=["auto-draft the daily report from Jira"],
        suggested_mvp="a Jira to Slack summary drafter",
    )
```

**Exercise 6.1 — Run the stub path.**
In `main.py` there is a constant `USE_LLM = True` near the top. Set it to `False`,
restart, and call `POST /diagnose` from `/docs` with Aarav's golden input:

```json
{
  "workflow_description": "Every morning I read Jira tickets, write a status report, and post it to Slack.",
  "tools_used": ["Jira", "Slack"],
  "biggest_pain": "writing the report by hand every day"
}
```

Confirm the golden output comes back — *with no AI in the loop at all*. Set `USE_LLM` back to `True`.

> ✅ **Checkpoint:** You have a real, running API that honors its contract with zero AI.

---

## Section 7 — Adding the Brain: GroqCloud

**The idea.** A client library is a **wrapper** around the raw API you called by hand in
the lab. `Groq(...)` does the boring six jobs (build request, set headers, parse response)
so you don't. And one line is the whole reason the backend exists:

```python
client = Groq(api_key=os.environ["GROQ_API_KEY"])
```

The key comes from an **environment variable** — never the code, never the frontend. This
is the secret living in the private place we derived in Section 1.

**The code** is the `run_diagnosis(...)` function in `main.py`. It sends a system prompt +
the user's workflow, gets text back, and shapes it into a `DiagnoseResponse`. The golden
output is kept as a **fallback** so the contract never breaks even if the model is weird.

**Exercise 7.1 — Point at the line.**
Open `main.py`, find the `Groq(api_key=...)` line, and write its line number here: ______.
This is the line where the backend justifies its own existence.

**Exercise 7.2 — Make the model misbehave, watch the fallback hold.**
Temporarily change the model name to a fake one (e.g. `"not-a-real-model"`) and call
`/diagnose`. Observe that the API still returns a valid `DiagnoseResponse` shape (the
fallback), not a crash. Restore the real model name. *The contract survived the model failing.*

**Exercise 7.3 — Feed it context.**
Change the system prompt to ask for *exactly two* automation opportunities. Re-run with the
golden input. Did the output change? This is you "feeding context into the probabilistic
core through a deterministic interface."

> ✅ **Checkpoint:** You can point at the exact line where the backend earns its existence.

---

## Section 8 — Connecting Frontend to Backend

**The idea.** The Gradio app stops holding logic. It becomes a *thin* frontend that calls
your backend over the internet. The frontend never sees the key.

**The code** is `app_frontend.py`:

```python
import os
import gradio as gr
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/diagnose")

def diagnose(message, history):
    response = requests.post(
        BACKEND_URL,
        json={"workflow_description": message, "tools_used": [], "biggest_pain": ""},
    )
    data = response.json()
    return data["suggested_mvp"]

demo = gr.ChatInterface(diagnose, type="messages")
demo.launch()
```

**Exercise 8.1 — Close the loop locally.**
In **terminal 1**: `uvicorn main:app --reload` (backend on :8000).
In **terminal 2**: `python app_frontend.py` (frontend).
Open the Gradio URL, type a workflow, and watch the answer come back **through your own backend**.

**Exercise 8.2 — Trace the stack.**
Draw or write the path a single message takes:

```
You → Gradio (public) → HTTP → FastAPI (private, holds key) → Groq (probabilistic)
   → back through FastAPI → back to Gradio → back to You
```

Then `grep` `app_frontend.py` for the word "key". Confirm there is none. *That is the design, not an accident.*

> ✅ **Checkpoint:** You built the ChatGPT stack from Lecture 03 — and the frontend never sees the key.

---

## Section 9 — Deploy the Whole Thing on Hugging Face

**The idea.** Two Spaces, because the separation *is* the point.

**Backend Space (the private brain):**
- New Space → **Docker** SDK.
- Push `main.py`, `requirements.txt`, and the `Dockerfile` in this repo.
- **Settings → Secrets** → add `GROQ_API_KEY`.
- You get a public URL ending in `.hf.space`.

**Frontend Space (the public face):**
- Your Gradio Space (`app_frontend.py`).
- Set `BACKEND_URL` to your backend's `/diagnose` URL.
- Commit, open the **App** tab.

**Exercise 9.1 — Read the Dockerfile.**
Open `Dockerfile`. Answer: (a) what port does the backend listen on? (b) which line installs
your dependencies? (c) which line actually starts the server?

**Exercise 9.2 — Predict the three classic errors.**
Match each symptom to its cause (answers in Section 10 of the lecture):
- `401` from Groq → ______
- `422` from your own API → ______
- connection error from Gradio → ______

> ✅ **Checkpoint:** The key lives only in the backend Space's Secrets — never in a repo, never in the frontend.

---

## Section 10 — Self-Test (Do This Before The Next Lecture)

Answer out loud, then check yourself against the code.

1. In one sentence, why can a secret never live in the frontend?
2. What are the six jobs anything behind an API address must do? Map each to WHERE, ACTION, SEND, or BACK.
3. Your API returns a 422. Whose fault is it — the caller's or yours — and how do you know?
4. Your API returns a 401 from Groq. Where do you look first?
5. Name the four CRUD verbs. Which two does your app use today, and why are the other two silent?
6. Point at the exact line in `main.py` where the backend justifies its own existence.
7. If you deleted the backend and put the Groq call back in Gradio, what would still work, and what would break the moment you deployed it?

---

## Stretch Exercises (Optional)

- **S1.** Add a second endpoint `GET /health` that returns `{"status": "ok"}`. Which CRUD verb is it?
- **S2.** Re-shape `DiagnoseResponse` to also return the rich diagnosis from `diagnoser.py`
  (trigger, steps, bottleneck…). Notice how changing the Pydantic model changes `/docs` automatically.
- **S3.** Make `app_frontend.py` show *all* of the response, not just `suggested_mvp`.
- **S4.** Add a deliberately broken request to a `tests.http` file and use it to trigger a 422 on demand.

---

*You are no longer only the thing that calls APIs. You are now the thing at the address that answers them.*
