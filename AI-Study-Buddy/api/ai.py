import os
import json
import uuid
import httpx
from typing import List, Dict
from pydantic import BaseModel, ValidationError
from . import models
from dotenv import load_dotenv

load_dotenv()

AI_API_KEY = os.getenv("AI_API_KEY")
AI_API_URL = os.getenv("AI_API_URL")  # e.g., https://api.openai.com/v1/chat/completions
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "gpt-4o-mini")

if not AI_API_KEY or not AI_API_URL:
    raise RuntimeError("AI_API_KEY and AI_API_URL must be set in environment variables")

client = httpx.AsyncClient(timeout=30.0)

# Simple in‑memory store for chunk embeddings per session
# {session_id: [{"id": str, "text": str, "embedding": List[float]}]}
chunk_store: Dict[str, List[Dict]] = {}

async def _embed_text(text: str) -> List[float]:
    """Create an embedding for *text* using the configured embedding model.
    The request payload follows the OpenAI embeddings endpoint format.
    """
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }
    resp = await client.post(f"{AI_API_URL.rstrip('/')}/embeddings", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # OpenAI returns a list under 'data' -> first element -> 'embedding'
    return data["data"][0]["embedding"]

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b + 1e-9)

async def _retrieve_relevant_chunks(session_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """Return *top_k* chunks most similar to *query* for the given *session_id*.
    If no chunks exist, returns an empty list.
    """
    chunks = chunk_store.get(session_id, [])
    if not chunks:
        return []
    query_emb = await _embed_text(query)
    # Compute similarity scores
    scored = [
        {"id": ch["id"], "text": ch["text"], "score": _cosine_similarity(query_emb, ch["embedding"]) }
        for ch in chunks
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

async def _call_model(messages: List[Dict]) -> str:
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GENERATION_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    resp = await client.post(AI_API_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # OpenAI returns choices[0].message.content
    return data["choices"][0]["message"]["content"]

async def generate_study_content(session_id: str, subject: str, topic: str, material: str) -> models.AIResponse:
    """Ingest *material*, store chunk embeddings under *session_id*, retrieve relevant passages, and ask the LLM to produce an explanation, an example, and five multiple‑choice questions.
    The caller provides *session_id* so that later retrievals can use the same stored chunks.
    """
    # 1️⃣ Chunk the material – 200‑character chunks with 50‑char overlap
    chunk_size = 200
    overlap = 50
    chunks: List[Dict] = []
    idx = 0
    while idx < len(material):
        chunk_text = material[idx : idx + chunk_size]
        chunk_id = str(uuid.uuid4())
        embedding = await _embed_text(chunk_text)
        chunks.append({"id": chunk_id, "text": chunk_text, "embedding": embedding})
        idx += chunk_size - overlap
    # Store chunks for later retrieval (session scoped)
    chunk_store[session_id] = chunks

    # 2️⃣ Retrieve relevant chunks using the subject+topic as the query
    query = f"{subject} {topic}"  # simple query
    relevant = await _retrieve_relevant_chunks(session_id, query, top_k=5)
    retrieved_texts = "\n---\n".join([c["text"] for c in relevant]) or material

    # 3️⃣ Build the system/user prompt for the LLM
    system_prompt = (
        "You are an AI tutor that must generate a concise explanation, a concrete example, "
        "and exactly five multiple‑choice questions (four options each, one correct) for a student. "
        "All content must be derived **only** from the provided material. "
        "If the material is insufficient, respond with a JSON object containing an "
        "`error` field describing what is missing."
    )
    user_prompt = (
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial excerpts:\n{retrieved_texts}\n\nGenerate JSON with the following schema:"
        " {\n  \"explanation\": string,\n  \"example\": string,\n  \"questions\": [\n    {\n      \"id\": string,\n      \"question\": string,\n      \"options\": [string, string, string, string],\n      \"answer\": integer (0‑3)\n    }\n  ]\n}\n"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = await _call_model(messages)
    try:
        parsed = json.loads(raw)
        ai_resp = models.AIResponse(**parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise RuntimeError(f"Invalid model output: {e}")
    return ai_resp
    """Ingest *material*, retrieve relevant passages, and ask the LLM to produce
    an explanation, an example, and five multiple‑choice questions.
    The function stores the chunk embeddings in *chunk_store* keyed by a temporary
    *session_id* which the caller creates.
    """
    # 1️⃣ Chunk the material – 200‑character chunks with 50‑char overlap
    chunk_size = 200
    overlap = 50
    chunks: List[Dict] = []
    idx = 0
    while idx < len(material):
        chunk_text = material[idx : idx + chunk_size]
        chunk_id = str(uuid.uuid4())
        embedding = await _embed_text(chunk_text)
        chunks.append({"id": chunk_id, "text": chunk_text, "embedding": embedding})
        idx += chunk_size - overlap
    # Store chunks for later retrieval (session scoped)
    # The caller will pass a generated session_id; we generate a temporary one here and return it via models.AIResponse
    # For simplicity we embed the chunks under a *temp* session key that the caller will later replace.
    temp_session_id = str(uuid.uuid4())
    chunk_store[temp_session_id] = chunks

    # 2️⃣ Retrieve relevant chunks using the subject+topic as the query
    query = f"{subject} {topic}"  # simple query
    relevant = await _retrieve_relevant_chunks(temp_session_id, query, top_k=5)
    retrieved_texts = "\n---\n".join([c["text"] for c in relevant]) or material

    # 3️⃣ Build the system/user prompt for the LLM
    system_prompt = (
        "You are an AI tutor that must generate a concise explanation, a concrete example, "
        "and exactly five multiple‑choice questions (four options each, one correct) for a student. "
        "All content must be derived **only** from the provided material. "
        "If the material is insufficient, respond with a JSON object containing an "
        "`error` field describing what is missing."
    )
    user_prompt = (
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial excerpts:\n{retrieved_texts}\n\nGenerate JSON with the following schema:"
        " {\n  \"explanation\": string,\n  \"example\": string,\n  \"questions\": [\n    {\n      \"id\": string,\n      \"question\": string,\n      \"options\": [string, string, string, string],\n      \"answer\": integer (0‑3)\n    }\n  ]\n}\n"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = await _call_model(messages)
    try:
        parsed = json.loads(raw)
        # Validate against AIResponse model
        ai_resp = models.AIResponse(**parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise RuntimeError(f"Invalid model output: {e}")

    # Replace temporary session id with a permanent one that the caller can use.
    # The caller will store the answer key using the returned session_id.
    # We'll embed the temporary id into the response via a hidden field (not part of schema) – instead return it as part of a tuple and let caller set.
    # For simplicity, we attach it as an attribute not used by Pydantic.
    ai_resp.session_id = temp_session_id  # type: ignore
    return ai_resp
