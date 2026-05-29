"""
The Workflow Diagnoser. The system, in plain Python.

Step 3: make it survive a real user. We add the input filter (validate)
and designed failure states (the try/except shell), so diagnose() always
returns a predictable shape — the caller never has to guess.

A beginner's program crashes on bad input. A builder's program has a
designed answer for it. The states are outputs too.
"""

import json
import os
from groq import Groq

MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

PROMPT = """You are a workflow diagnosis assistant.
The user will describe one repeated task they do at work.
Return ONLY a JSON object. No prose. No markdown fences. Use exactly these keys:

- "trigger": what starts this task
- "inputs": a list of things needed before the task can start
- "steps": a list of the main steps, in order
- "bottleneck": the single slowest or most painful step
- "output": what is produced at the end
- "recipient": who receives or uses the output
- "success_metric": one measurable way to tell the task was done well
- "ai_can_help": a list of steps an AI could speed up
- "keep_human": a list of steps that still need human judgment
- "verdict": one sentence on whether this is worth automating, and why

Task description:
{description}
"""


def validate(description):
    """Reject input too thin to diagnose. The contract's rejection rule, in code."""
    text = (description or "").strip()
    if len(text) < 20:
        return "Please describe the task in a sentence or two, not just a few words."
    return None


def _clean(raw):
    # Models sometimes wrap JSON in code fences. Strip them defensively.
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[len("json"):]
    return text.strip()


def diagnose(description):
    """Always returns one of two shapes:
        success -> {"ok": True, "diagnosis": {...}}
        failure -> {"ok": False, "error": "..."}
    """
    error = validate(description)
    if error:
        return {"ok": False, "error": error}

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "user", "content": PROMPT.format(description=description)}
            ],
        )
        raw = completion.choices[0].message.content
        data = json.loads(_clean(raw))
        return {"ok": True, "diagnosis": data}
    except json.JSONDecodeError:
        return {"ok": False, "error": "The model did not return clean data. Try running it again."}
    except Exception as e:
        return {"ok": False, "error": "Something went wrong talking to the model: " + str(e)}


def format_diagnosis(result):
    """Turn the diagnosis into readable text. Both interfaces use this."""
    if not result["ok"]:
        return "Could not diagnose this yet.\n\n" + result["error"]

    d = result["diagnosis"]

    def as_list(value):
        if isinstance(value, list):
            return "\n".join("  - " + str(item) for item in value)
        return "  - " + str(value)

    lines = [
        "WORKFLOW DIAGNOSIS",
        "",
        "Trigger: " + str(d.get("trigger", "")),
        "",
        "Inputs needed:",
        as_list(d.get("inputs", [])),
        "",
        "Steps:",
        as_list(d.get("steps", [])),
        "",
        "Bottleneck: " + str(d.get("bottleneck", "")),
        "",
        "Output: " + str(d.get("output", "")),
        "Goes to: " + str(d.get("recipient", "")),
        "Success metric: " + str(d.get("success_metric", "")),
        "",
        "Where AI can help:",
        as_list(d.get("ai_can_help", [])),
        "",
        "Keep a human in the loop for:",
        as_list(d.get("keep_human", [])),
        "",
        "Verdict: " + str(d.get("verdict", "")),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sample = (
        "Every Monday morning I open three different dashboards, copy the weekly "
        "numbers into a spreadsheet, write a short summary, and paste it into a "
        "slide that I send to my manager before the 10am review."
    )
    print(format_diagnosis(diagnose(sample)))
