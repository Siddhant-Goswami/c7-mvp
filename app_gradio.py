"""
The Gradio interface. A thin layer over the system in diagnoser.py.

Run it:
    python app_gradio.py
Then open the local URL it prints in the terminal.
"""

import gradio as gr
from diagnoser import diagnose, format_diagnosis


def run(description):
    # Take the input, hand it to the system, show the output.
    # All the real work lives in diagnoser.py.
    return format_diagnosis(diagnose(description))


demo = gr.Interface(
    fn=run,
    inputs=gr.Textbox(
        lines=5,
        label="Describe one repeated task you do at work",
        placeholder="Every Monday I pull numbers from three dashboards and ...",
    ),
    outputs=gr.Textbox(label="Diagnosis", lines=20),
    title="Workflow Diagnoser",
    description="Describe a task. Get it mapped, with where AI can help and where a human should stay.",
)

if __name__ == "__main__":
    demo.launch()
