import os
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
    "AI_API_URL", "https://api.openai.com/v1/chat/completions"
)
# Model to use for generation (default works with OpenAI and Gemini style)
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Helper: call the LLM and ask for JSON output
# ---------------------------------------------------------------------------
def call_llm(subject: str, topic: str, material: str) -> dict:
    """Ask the LLM for an explanation, an example and exactly five MCQs.
    Returns the parsed JSON dict or raises a RuntimeError with a helpful message.
    """
    system_prompt = (
        "You are an AI tutor that must produce a concise explanation of a topic, "
        "one concrete example, and exactly five multiple‑choice questions (four options each, one correct). "
        "All content must be derived **only** from the supplied material. "
        "If the material is insufficient, respond with a JSON object containing an "
        "`error` field describing what is missing."
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
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(AI_API_URL, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"API request failed: {exc}")

    try:
        data = response.json()
        # OpenAI‑style response; for other providers adapt accordingly
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid response format from LLM: {exc}")

    # Basic validation of required fields
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
st.set_page_config(page_title="StudyMate – AI Study Buddy", layout="centered")
st.title("📚 StudyMate – AI Study Buddy")

if not AI_API_KEY:
    st.warning(
        "🚨 No API key detected. Add `AI_API_KEY=your_key_here` to a `.env` file in the project root."
    )
    st.stop()

# ---------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "input"  # other values: "quiz", "result"
if "generation" not in st.session_state:
    st.session_state.generation = {}
if "answers" not in st.session_state:
    st.session_state.answers = {}

# ---------------------------------------------------------------
# Stage: Input form
# ---------------------------------------------------------------
if st.session_state.stage == "input":
    with st.form(key="study_form"):
        subject = st.text_input("Subject", max_chars=100)
        topic = st.text_input("Topic", max_chars=150)
        material = st.text_area(
            "Course notes / syllabus material",
            height=200,
            max_chars=5000,
        )
        submit = st.form_submit_button("Start study session")
        if submit:
            if not subject or not topic or not material:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Generating explanation and quiz…"):
                    try:
                        result = call_llm(subject, topic, material)
                        st.session_state.generation = result
                        # Build a simple answer key dict for later scoring
                        st.session_state.answer_key = {
                            q["id"]: q["answer"] for q in result["questions"]
                        }
                        st.session_state.stage = "quiz"
                    except RuntimeError as err:
                        st.error(str(err))

# ---------------------------------------------------------------
# Stage: Quiz
# ---------------------------------------------------------------
elif st.session_state.stage == "quiz":
    gen = st.session_state.generation
    st.subheader("Explanation")
    st.write(gen["explanation"])
    st.subheader("Example")
    st.write(gen["example"])
    st.subheader("Quiz – answer the five questions")
    with st.form(key="quiz_form"):
        for idx, q in enumerate(gen["questions"]):
            st.write(f"**Q{idx + 1}: {q['question']}**")
            choice = st.radio(
                f"options_{q['id']}",
                options=[f"{i + 1}. {opt}" for i, opt in enumerate(q["options"])],
                index=None,
                key=f"radio_{q['id']}",
            )
            # Store the selected index (0‑based) when the form is submitted
            st.session_state.answers[q["id"]] = (
                int(choice.split(".")[0]) - 1 if choice else None
            )
        quiz_submit = st.form_submit_button("Submit answers")
        if quiz_submit:
            # Validate that all questions were answered
            if any(v is None for v in st.session_state.answers.values()):
                st.error("Please answer every question before submitting.")
            else:
                st.session_state.stage = "result"

# ---------------------------------------------------------------
# Stage: Result
# ---------------------------------------------------------------
elif st.session_state.stage == "result":
    gen = st.session_state.generation
    key = st.session_state.answer_key
    user_ans = st.session_state.answers
    total = len(key)
    correct = sum(1 for qid, ans in user_ans.items() if ans == key[qid])
    st.subheader(f"Score: {correct} / {total}")
    st.write("---")
    for q in gen["questions"]:
        qid = q["id"]
        user_choice = user_ans[qid]
        correct_choice = key[qid]
        is_correct = user_choice == correct_choice
        st.write(f"**{q['question']}**")
        st.write(f"Your answer: {q['options'][user_choice]}")
        if not is_correct:
            st.write(f"**Correct answer:** {q['options'][correct_choice]}")
            st.write(f"Explanation: {q['explanation']}")
        st.write("---")
    if st.button("Start a new session"):
        # Reset everything
        for k in ["stage", "generation", "answers", "answer_key"]:
            if k in st.session_state:
                del st.session_state[k]
        st.experimental_rerun()
