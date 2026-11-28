import os
import re

import json
import httpx
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration – read from environment variables
# ---------------------------------------------------------------------------
AI_API_KEY = os.getenv("AI_API_KEY")
# Default to OpenAI's chat completion endpoint if not overridden
AI_API_URL = os.getenv(
    "AI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
)
# Model to use for generation (default works with OpenAI and Gemini style)
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Helper: call the LLM and ask for JSON output
# ---------------------------------------------------------------------------
def call_llm(subject: str, topic: str, material: str) -> dict:
    """Call the local Ollama (or any OpenAI‑compatible) API to get a JSON response.
    The function builds a system prompt and a user prompt, sends them to the URL
    defined in ``AI_API_URL`` with the model name ``GENERATION_MODEL``.
    It expects the model to return a JSON object matching the required schema.
    """
    # Prompt construction – same as before
    system_prompt = (
        "You are an AI tutor that must produce a concise explanation of a topic, "
        "one concrete example, and exactly five multiple‑choice questions (four options each, one correct). "
        "All content must be derived **only** from the supplied material. "
        "If the material is insufficient, respond with a JSON object containing an `error` field describing what is missing."
    )
    user_prompt = (
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial:\n{material}\n\n"
        "Generate JSON with this exact schema:\n"
        "{\n"
        "  \"explanation\": string,\n"
        "  \"example\": string,\n"
        "  \"questions\": [\n"
        "    {\n"
        "      \"id\": string,\n"
        "      \"question\": string,\n"
        "      \"options\": [string, string, string, string],\n"
        "      \"answer\": integer (0-3),\n"
        "      \"explanation\": string\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "\nPlease reply ONLY with the JSON object, no additional text, explanations, or markdown."
    )
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial:\n{material}\n\n"
        "Generate JSON with this exact schema:\n"
        "{\n"
        "  \"explanation\": string,\n"
        "  \..."
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial:\n{material}\n\n"
        "Generate JSON with this exact schema:\n"
        "{\n"
        "  \"explanation\": string,\n"
        "  \"example\": string,\n"
        "  \"questions\": [\n"
        "    {\n"
        "      \"id\": string,\n"
        "      \"question\": string,\n"
        "      \"options\": [string, string, string, string],\n"
        "      \"answer\": integer (0‑3),\n"
        "      \"explanation\": string\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )
    payload = {
        "model": GENERATION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 1024,
        "temperature": 0.2,
        # frequency_penalty can help keep output concise
        "frequency_penalty": 0.5,
    }
    # Build headers – include Authorization only if an API key is provided
    headers = {"Content-Type": "application/json"}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"
    try:
        # Increase timeout to accommodate slower local models
        response = httpx.post(AI_API_URL, json=payload, headers=headers, timeout=300.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"API request failed: {exc}")
    # Parse the response – handle OpenAI‑compatible and Ollama formats
    try:
        data = response.json()
        if "choices" in data:  # OpenAI style
            content = data["choices"][0]["message"]["content"]
        elif "message" in data:  # Ollama style
            content = data["message"]["content"]
        else:
            raise RuntimeError(f"Unexpected response shape: {list(data.keys())}")
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid response format from LLM: {exc}")
    # Ensure the model actually returned JSON text
    if not isinstance(content, str) or not content.lstrip().startswith("{"):
        # Try to extract JSON object from the response using a regex fallback
        import re as _re
        match = _re.search(r"\{.*\}", content, _re.DOTALL)
        if match:
            content = match.group(0)
        else:
            raise RuntimeError(
                "LLM returned non‑JSON text. Make sure the model supports JSON output or explicitly ask for JSON in the prompt."
            )
    if not isinstance(content, str) or not content.lstrip().startswith("{"):
        raise RuntimeError(
            "LLM returned non‑JSON text. Make sure the model supports JSON output or explicitly ask for JSON in the prompt."
        )
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON from LLM output: {exc}")
    # Basic validation – same as before
    if not isinstance(result, dict):
        raise RuntimeError("LLM did not return a JSON object")
    if "error" in result:
        raise RuntimeError(f"LLM error: {result['error']}")
    required = {"explanation", "example", "questions"}
    if not required.issubset(result.keys()):
        raise RuntimeError("Missing one of explanation/example/questions in LLM response")
    if len(result["questions"]) != 5:
        raise RuntimeError("LLM returned a number of questions other than five")
    for q in result["questions"]:
        if not all(k in q for k in ("id", "question", "options", "answer", "explanation")):
            raise RuntimeError("A question is missing required keys")
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise RuntimeError("Each question must have exactly four options")
        if not (0 <= q["answer"] <= 3):
            raise RuntimeError("Answer index out of range (must be 0‑3)")
    return result

# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.title("Study Buddy – Instant Quiz Generator")

# Simple input form
with st.form("input_form"):
    subject = st.text_input("Subject", "Physics")
    topic = st.text_input("Topic", "Newton's Laws")
    material = st.text_area("Material (paste notes here)", height=200)
    submit = st.form_submit_button("Generate")

if submit:
    if not material.strip():
        st.error("Please provide some material for the model to work with.")
    else:
        with st.spinner("Generating explanation, example, and questions…"):
            try:
                result = call_llm(subject, topic, material)
                st.subheader("Explanation")
                st.write(result["explanation"])
                st.subheader("Example")
                st.write(result["example"])
                st.subheader("Quiz")
                # Store questions in session state for later scoring
                st.session_state["questions"] = result["questions"]
                for q in result["questions"]:
                    st.write(f"**{q['id']}**: {q['question']}")
                    st.radio(
                        f"options_{q['id']}",
                        options=q["options"],
                        index=None,
                        key=f"radio_{q['id']}"
                    )
                if st.button("Submit Answers"):
                    score = 0
                    for q in st.session_state.get("questions", []):
                        selected = st.session_state.get(f"radio_{q['id']}")
                        if selected is None:
                            continue
                        if q["options"][q["answer"]] == selected:
                            score += 1
                    st.success(f"You scored {score}/5")
                    st.write("**Answer explanations:**")
                    for q in st.session_state.get("questions", []):
                        st.write(f"- {q['id']}: {q['explanation']}")
            except Exception as e:
                st.error(f"Error: {e}")
