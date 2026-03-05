from pydantic import BaseModel


class PracticeQuestionOut(BaseModel):
    id: int
    kp_id: int
    type: str
    prompt: str
    options: list[str]
    difficulty: float


class PracticeSubmitIn(BaseModel):
    question_id: int
    kp_id: int
    answer: str
    self_report: str = "unknown"
    duration_ms: int = 0


class PracticeNextOut(BaseModel):
    done: bool
    total_questions: int
    attempted_questions: int
    difficulty_range: str | None = None
    question: PracticeQuestionOut | None = None
    model_used: bool = False
    predicted_correct: float | None = None
    reason: str | None = None
    recent_predictions: list[float] = []


class PracticeStatsOut(BaseModel):
    kp_id: int
    total: int
    correct: int
    incorrect: int
    accuracy: float
    daily: list[dict] = []


class PracticeWrongOut(BaseModel):
    id: int
    question_id: int
    kp_id: int
    prompt: str
    type: str
    difficulty: float
    created_at: str
    options: list[str] = []
    tags: list[str] = []


class ReviewItemOut(BaseModel):
    id: int
    question_id: int
    kp_id: int
    prompt: str
    type: str
    difficulty: float
    due_at: str
    interval_days: int
    last_result: str
    overdue: bool = False


class ReviewQueueOut(BaseModel):
    total: int
    due: int
    items: list[ReviewItemOut]
