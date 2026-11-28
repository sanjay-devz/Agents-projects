from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import os

# Import local modules
from . import models, ai

app = FastAPI()

# Allow all origins for simplicity (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in‑memory store for sessions (keyed by uuid)
session_store: dict[str, dict] = {}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/start_session", response_model=models.StartSessionResponse)
async def start_session(req: models.StartSessionRequest):
    """Create a new study session, ingest material, and generate explanation + questions.
    Returns a session ID that the frontend must send back for answer submission.
    """
    # Basic length validation
    if len(req.subject) > 100 or len(req.topic) > 150:
        raise HTTPException(status_code=400, detail="Subject or topic too long")
    if len(req.material) > 5000:
        raise HTTPException(status_code=400, detail="Material too large (max 5 KB)")

    session_id = str(uuid4())

    # Call AI to generate content, passing the session_id so chunks are stored against it
    try:
        ai_response = await ai.generate_study_content(session_id, req.subject, req.topic, req.material)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Store answer key for later evaluation
    session_store[session_id] = {"answer_key": {q.id: q.answer for q in ai_response.questions}}

    return models.StartSessionResponse(
        session_id=session_id,
        explanation=ai_response.explanation,
        example=ai_response.example,
        questions=[models.QuestionPublic(id=q.id, question=q.question, options=q.options) for q in ai_response.questions],
    )

@app.post("/api/submit_answers", response_model=models.SubmitAnswersResponse)
async def submit_answers(req: models.SubmitAnswersRequest):
    store = session_store.get(req.session_id)
    if not store:
        raise HTTPException(status_code=404, detail="Session not found")

    answer_key: dict[str, int] = store["answer_key"]
    total = len(answer_key)
    correct = 0
    feedback = []
    for ans in req.answers:
        correct_opt = answer_key.get(ans.question_id)
        if correct_opt is None:
            raise HTTPException(status_code=400, detail="Invalid question ID")
        is_correct = ans.selected_option == correct_opt
        if is_correct:
            correct += 1
        feedback.append(models.FeedbackItem(
            question_id=ans.question_id,
            correct=is_correct,
            correct_option=correct_opt if not is_correct else None,
            explanation=None if is_correct else "See explanation in material.",
        ))
    score = f"{correct}/{total}"
    return models.SubmitAnswersResponse(score=score, feedback=feedback)
