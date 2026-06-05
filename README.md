# Workflow Diagnoser

The live-build artifact from **100xEngineers Cohort 7, Lecture 05 — Your First System**.

Describe one repeated task you do at work. Get back a structured diagnosis: trigger, inputs, steps, bottleneck, output, recipient, success metric, where AI can help, where a human should stay, and a one-line verdict on whether it's worth automating.

> The system is a function. The interface is a wrapper around it. You write the system once, in plain Python, and then any interface you like sits on top.

## The shape

```
diagnoser.py        ← the system, written once, plain Python
   /        \
Gradio    Streamlit  ← two interchangeable interfaces
```

- **`diagnoser.py`** — the system. No web framework. Run it alone to test in the terminal.
- **`app_gradio.py`** — the Gradio interface over the system.
- **`app_streamlit.py`** — the Streamlit interface over the same system.
- **`requirements.txt`** — what to install.

The interface is replaceable. The system is the asset.

## Setup (once)

1. Install the packages:

   ```
   pip install -r requirements.txt
   ```

2. Set your GroqCloud API key as an environment variable. Never paste the key into the code. Get one at https://console.groq.com/keys.

   macOS / Linux:
   ```
   export GROQ_API_KEY=your_key_here
   ```

   Windows PowerShell:
   ```
   setx GROQ_API_KEY "your_key_here"
   ```
   (Open a new terminal after `setx` so it picks up the value.)

## Run

Test the system with no interface at all:

```
python diagnoser.py
```

Run the Gradio interface:

```
python app_gradio.py
```

Run the Streamlit interface:

```
streamlit run app_streamlit.py
```

Each app prints a local URL. Open it in your browser.

## How the system survives a real user

`diagnose()` always returns one of two shapes:

```python
{"ok": True,  "diagnosis": {...}}   # success
{"ok": False, "error": "..."}       # designed failure
```

`validate()` rejects inputs that are too thin to diagnose. The model call is wrapped in `try/except`, so the program never crashes — it returns a clean message. A beginner's program crashes on bad input. A builder's program has a designed answer for it.

## Swapping the model

Change one line in `diagnoser.py`:

```python
MODEL = "llama-3.3-70b-versatile"
```

Nothing else has to change. That is the contract doing its job.

## Lecture 05 — the backend (FastAPI)

L04 left the logic and the interface in the same process. L05 splits them: a
private **backend** holds the key and the brain, and a thin **frontend** calls it
over the internet.

```
app_frontend.py  ← thin Gradio, public, no secret in it
      |  HTTP POST /diagnose
      v
main.py          ← FastAPI backend, private, holds GROQ_API_KEY, calls Groq
```

- **`main.py`** — the FastAPI backend. `GET /` is a Hello World; `POST /diagnose`
  enforces the contract with Pydantic and runs the diagnosis. Open `/docs` for the
  auto-generated, clickable contract.
- **`app_frontend.py`** — the thin Gradio frontend. Reads `BACKEND_URL` from the
  environment and calls your backend. No key anywhere in it.
- **`Dockerfile`** — runs the backend on a Hugging Face Docker Space (port 7860).
- **`LECTURE_05_GUIDE.md`** — a step-by-step, exercise-driven walkthrough of every
  concept in the lecture, mapped to the code in this repo.

Run it locally (two terminals):

```
uvicorn main:app --reload     # terminal 1: backend on http://127.0.0.1:8000
python app_frontend.py        # terminal 2: frontend, calls the backend
```

Open `http://127.0.0.1:8000/docs` to read and call the contract directly.

## The build, commit by commit

| Step | What happens |
|------|--------------|
| Step 0 | One empty file. |
| Step 1 | `diagnose()` as a stub that returns the shape of the output. |
| Step 2 | Put the model inside the function — same signature, real output. |
| Step 3 | Input filter, designed failure states, `format_diagnosis()`. |
| Step 4 | Wrap the system in Gradio. |
| Step 5 | Same system, Streamlit interface. |

Use `git log --oneline` to walk the steps, and `git show <step>` to see the diff each one introduces.
