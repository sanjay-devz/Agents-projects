"""Local Ollama-powered study helper."""

import json
import os
import re
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", f"{OLLAMA_HOST}/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:latest")


def _extract_json(content: str) -> dict[str, Any]:
    """Parse a JSON object, allowing a model to wrap it in a markdown fence."""
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Ollama returned text instead of a JSON quiz. Try generating again.")
        try:
            result = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Ollama response must be a JSON object.")
    return result


def _validate_quiz(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("error"):
        raise RuntimeError(f"Gemma could not generate a quiz: {result['error']}")
    for field in ("explanation", "example"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise RuntimeError(f"Gemma response is missing a valid '{field}' string.")

    questions = result.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        raise RuntimeError("Gemma must return exactly five questions.")

    ids: set[str] = set()
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise RuntimeError(f"Question {index} must be a JSON object.")
        for field in ("id", "question", "explanation"):
            if not isinstance(question.get(field), str) or not question[field].strip():
                raise RuntimeError(f"Question {index} is missing a valid '{field}' string.")
        question_id = question["id"]
        if question_id in ids:
            raise RuntimeError("Gemma returned duplicate question IDs.")
        ids.add(question_id)
        options = question.get("options")
        if (
            not isinstance(options, list)
            or len(options) != 4
            or any(not isinstance(option, str) or not option.strip() for option in options)
        ):
            raise RuntimeError(f"Question {index} must have four non-empty text options.")
        answer = question.get("answer")
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < 4:
            raise RuntimeError(f"Question {index} has an invalid answer index (expected 0–3).")
    return result


def call_ollama(subject: str, topic: str, material: str) -> dict[str, Any]:
    """Generate and validate a five-question quiz through local Ollama."""
    system_prompt = (
        "You are a careful study tutor. Use only the supplied study material. "
        "Return one JSON object with explanation (string), example (string), and "
        "questions (an array of exactly five objects). Each question must have "
        "id (unique string), question (string), options (exactly four strings), "
        "answer (zero-based integer from 0 to 3), and explanation (string). "
        "If the material is insufficient, return {\"error\":\"...\"}. "
        "Do not include markdown or text outside the JSON object."
    )
    user_prompt = (
        f"Subject: {subject.strip()}\nTopic: {topic.strip()}\n\n"
        f"Study material:\n{material.strip()}\n\nGenerate the explanation, example, and quiz now."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        response = httpx.post(OLLAMA_CHAT_URL, json=payload, timeout=300.0)
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Start Ollama locally, then try again."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError("Ollama took too long to respond. Check that the local model is running and try again.") from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        if exc.response.status_code == 404:
            raise RuntimeError(
                f"Ollama could not find model '{OLLAMA_MODEL}'. Pull it with `ollama pull {OLLAMA_MODEL}`."
            ) from exc
        raise RuntimeError(f"Ollama returned HTTP {exc.response.status_code}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc

    try:
        response_data = response.json()
        content = response_data["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Ollama returned an unexpected response. Check the local Ollama server.") from exc
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned an empty or invalid message.")
    return _validate_quiz(_extract_json(content))


st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="centered")
st.title("Study Buddy")
st.caption(f"DevSphere AI Study Bot · {OLLAMA_MODEL}")

st.session_state.setdefault("study_result", None)
st.session_state.setdefault("quiz_submitted", False)
st.session_state.setdefault("quiz_score", None)

with st.form("study_form"):
    subject = st.text_input("Subject", value="Physics", max_chars=100)
    topic = st.text_input("Topic", value="Newton's Laws", max_chars=150)
    material = st.text_area("Study material", height=200, max_chars=20000)
    generate = st.form_submit_button("Generate study guide")

if generate:
    if not subject.strip() or not topic.strip() or not material.strip():
        st.error("Enter a subject, topic, and study material before generating a quiz.")
    else:
        with st.spinner(f"Asking local Gemma model ({OLLAMA_MODEL}) to prepare your study guide…"):
            try:
                result = call_ollama(subject, topic, material)
                old_result = st.session_state.get("study_result")
                if old_result:
                    for question in old_result["questions"]:
                        st.session_state.pop(f"answer_{question['id']}", None)
                st.session_state.study_result = result
                st.session_state.quiz_submitted = False
                st.session_state.quiz_score = None
            except RuntimeError as exc:
                st.error(str(exc))

result = st.session_state.study_result
if result:
    st.subheader("Explanation")
    st.write(result["explanation"])
    st.subheader("Example")
    st.write(result["example"])
    st.subheader("Quiz")
    with st.form("quiz_form"):
        for index, question in enumerate(result["questions"], start=1):
            st.markdown(f"**{index}. {question['question']}**")
            st.radio(
                f"Answer to question {index}",
                question["options"],
                index=None,
                key=f"answer_{question['id']}",
                label_visibility="collapsed",
            )
        submitted = st.form_submit_button("Submit answers")

    if submitted:
        missing = [
            index
            for index, question in enumerate(result["questions"], start=1)
            if st.session_state.get(f"answer_{question['id']}") is None
        ]
        if missing:
            st.warning("Answer all five questions before submitting.")
        else:
            score = sum(
                st.session_state[f"answer_{question['id']}"] == question["options"][question["answer"]]
                for question in result["questions"]
            )
            st.session_state.quiz_score = score
            st.session_state.quiz_submitted = True

    if st.session_state.quiz_submitted:
        st.success(f"You scored {st.session_state.quiz_score}/5")
        st.subheader("Answer review")
        for index, question in enumerate(result["questions"], start=1):
            selected = st.session_state[f"answer_{question['id']}"]
            correct = question["options"][question["answer"]]
            st.markdown(f"**{index}. {question['question']}**")
            st.write(f"Your answer: {selected}")
            if selected != correct:
                st.write(f"Correct answer: {correct}")
            st.caption(question["explanation"])
