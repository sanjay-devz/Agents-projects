import os
import json
import uuid
import httpx
from typing import List, Dict
from pydantic import ValidationError
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

# In‑memory vector store per session
# {session_id: [{"id": str, "text": str, "embedding": List[float]}]}
chunk_store: Dict[str, List[Dict]] = {}

async def _embed_text(text: str) -> List[float]:
    """Create an embedding for *text* using the configured embedding model."""
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": EMBEDDING_MODEL, "input": text}
    resp = await client.post(f"{AI_API_URL.rstrip('/')}/embeddings", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b + 1e-9)

async def _retrieve_relevant_chunks(session_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """Return the *top_k* most similar chunks for *query* within *session_id*."""
    chunks = chunk_store.get(session_id, [])
    if not chunks:
        return []
    query_emb = await _embed_text(query)
    scored = [
        {"id": ch["id"], "text": ch["text"], "score": _cosine_similarity(query_emb, ch["embedding"]) }
        for ch in chunks
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

async def _call_model(messages: List[Dict]) -> str:
    """Call the LLM and return the raw content string (JSON)."""
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
    return data["choices"][0]["message"]["content"]

async def generate_study_content(session_id: str, subject: str, topic: str, material: str) -> models.AIResponse:
    """Chunk *material*, store embeddings under *session_id*, retrieve relevant passages,
    and ask the LLM to produce an explanation, an example, and exactly five MCQs.
    Returns a validated ``models.AIResponse`` instance.
    """
    # 1️⃣ Chunk the material (200 chars with 50 char overlap)
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
    chunk_store[session_id] = chunks

    # 2️⃣ Retrieve relevant chunks using the subject + topic as query
    query = f"{subject} {topic}"
    relevant = await _retrieve_relevant_chunks(session_id, query, top_k=5)
    retrieved_texts = "\n---\n".join([c["text"] for c in relevant]) or material

    # 3️⃣ Prompt the LLM
    system_prompt = (
        "You are an AI tutor that must generate a concise explanation, a concrete example, "
        "and exactly five multiple‑choice questions (four options each, one correct). "
        "All content must be derived **only** from the provided material. "
        "If the material is insufficient, respond with a JSON object containing an ``error`` field."
    )
    user_prompt = (
        f"Subject: {subject}\nTopic: {topic}\n\nMaterial excerpts:\n{retrieved_texts}\n\nGenerate JSON with the following schema:\n"
        "{\n  \"explanation\": string,\n  \"example\": string,\n  \"questions\": [\n    {\n      \"id\": string,\n      \"question\": string,\n      \"options\": [string, string, string, string],\n      \"answer\": integer (0‑3)\n    }\n  ]\n}\n"
    )
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    raw = await _call_model(messages)
    try:
        parsed = json.loads(raw)
        ai_resp = models.AIResponse(**parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise RuntimeError(f"Invalid model output: {e}")
    return ai_resp
