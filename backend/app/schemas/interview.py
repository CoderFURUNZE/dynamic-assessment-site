from pydantic import BaseModel


class InterviewStartIn(BaseModel):
    kp_id: int
    count: int = 5
    duration_minutes: int = 15


class InterviewQuestionOut(BaseModel):
    id: int
    kp_id: int
    type: str
    prompt: str
    options: list[str]
    difficulty: float


class InterviewStartOut(BaseModel):
    session_id: int
    total: int
    duration_minutes: int
    questions: list[InterviewQuestionOut]


class InterviewSubmitIn(BaseModel):
    session_id: int
    question_id: int
    answer: str
    rationale: str = ""


class InterviewSubmitOut(BaseModel):
    correct: bool
    explanation: str


class InterviewFinishIn(BaseModel):
    session_id: int


class InterviewFinishOut(BaseModel):
    total: int
    correct: int
    accuracy: float
