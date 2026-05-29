"""
The Streamlit interface. A different thin layer over the SAME system.

Run it:
    streamlit run app_streamlit.py
Then open the local URL it prints in the terminal.

We import the exact same diagnose and format_diagnosis from diagnoser.py.
The system did not change. Only the interface did.
"""

import streamlit as st
from diagnoser import diagnose, format_diagnosis

st.title("Workflow Diagnoser")
st.write(
    "Describe a task. Get it mapped, with where AI can help and where a human should stay."
)

description = st.text_area(
    "Describe one repeated task you do at work",
    placeholder="Every Monday I pull numbers from three dashboards and ...",
    height=150,
)

if st.button("Diagnose"):
    with st.spinner("Diagnosing..."):
        result = diagnose(description)
    st.text(format_diagnosis(result))
