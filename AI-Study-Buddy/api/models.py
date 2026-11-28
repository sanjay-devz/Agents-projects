from pydantic import BaseModel, Field
from typing import List, Optional

class StartSessionRequest(BaseModel):
    subject: str = Field(..., max_length=100)
    topic: str = Field(..., max_length=150)
    material: str = Field(..., max_length=5000)

class Question(BaseModel):
    id: str
    question: str
    options: List[str]
    answer: int  # index of correct option (0‑based)

class AIResponse(BaseModel):
    explanation: str
    example: str
    questions: List[Question]

class QuestionPublic(BaseModel):
    id: str
    question: str
    options: List[str]

class StartSessionResponse(BaseModel):
    session_id: str
    explanation: str
    example: str
    questions: List[QuestionPublic]

class AnswerItem(BaseModel):
    question_id: str
    selected_option: int

class SubmitAnswersRequest(BaseModel):
    session_id: str
    answers: List[AnswerItem]

class FeedbackItem(BaseModel):
    question_id: str
    correct: bool
    correct_option: Optional[int] = None
    explanation: Optional[str] = None

class SubmitAnswersResponse(BaseModel):
    score: str  # e.g., "4/5"
    feedback: List[FeedbackItem]
