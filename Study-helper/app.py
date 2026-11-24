import os

import streamlit as st
from google import genai


st.set_page_config(page_title="Study Notes Helper", page_icon="📚")

st.title("📚 Study Notes Helper")
st.write("Paste your notes and choose how you want help studying.")

# Read the API key from an environment variable.
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("I can't find GEMINI_API_KEY. Set it in your terminal, then restart this app.")
    st.stop()

client = genai.Client(api_key=api_key)

notes = st.text_area(
    "Your notes",
    placeholder="Paste a paragraph or your class notes here...",
    height=220,
)

task = st.selectbox(
    "What should the AI do?",
    ["Summarize", "Explain simply", "Make a quiz"],
)

if st.button("Help me study"):
    if not notes.strip():
        st.warning("Paste some notes first.")
    else:
        instructions = {
            "Summarize": "Summarize these study notes in clear bullet points.",
            "Explain simply": (
                "Explain these study notes in simple language for a beginner. "
                "Define difficult terms."
            ),
            "Make a quiz": (
                "Create five quiz questions from these study notes. "
                "Put the answers in a separate answer key at the end."
            ),
        }

        prompt = f"""
You are a patient study assistant. Use the notes below as your source.
If something is unclear or missing, say so instead of making it up.

Task: {instructions[task]}

Notes:
{notes}
"""

        try:
            with st.spinner("Thinking..."):
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                )

            st.subheader("Study help")
            st.write(response.text or "The AI returned an empty response.")

        except Exception as error:
            st.error(f"Something went wrong: {error}")
            st.caption("Check your internet connection, API key, and current API limits.")