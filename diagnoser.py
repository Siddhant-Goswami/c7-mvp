"""
The Workflow Diagnoser. The system, in plain Python.

Step 2: the function now calls the model. Signature is unchanged. The
prompt states the exact output shape as JSON — asking for a fixed shape
is how you get a usable output instead of a paragraph.
"""

import json
from anthropic import Anthropic

# Swap this one line to change models. Nothing else has to change.
# That is the contract doing its job.
MODEL = "claude-haiku-4-5"

# Reads ANTHROPIC_API_KEY from the environment. Never paste the key in code.
client = Anthropic()

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


def diagnose(description):
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": PROMPT.format(description=description)}],
    )
    raw = message.content[0].text
    return json.loads(raw)


if __name__ == "__main__":
    sample = (
        "Every Monday morning I open three different dashboards, copy the weekly "
        "numbers into a spreadsheet, write a short summary, and paste it into a "
        "slide that I send to my manager before the 10am review."
    )
    print(diagnose(sample))
