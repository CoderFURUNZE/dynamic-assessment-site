from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    full_name: str
    student_no: str
    class_name: str
    phone: str | None = None
    wechat_openid: str | None = None


class UserUpdateIn(BaseModel):
    role: str | None = None
    password: str | None = None
    full_name: str | None = None
    student_no: str | None = None
    class_name: str | None = None
    phone: str | None = None


class QuestionOut(BaseModel):
    id: int
    kp_id: int
    type: str
    prompt: str
    options: list[str]
    answer: str
    explanation: str
    difficulty: float
    source: str | None = None
    tags: str | None = None
    version: str | None = None
    attempts: int | None = None
    correct_rate: float | None = None


class QuestionIn(BaseModel):
    kp_id: int
    type: str  # "mcq" | "blank"
    prompt: str
    options: list[str] = []
    answer: str
    explanation: str = ""
    difficulty: float = 0.5
    source: str = ""
    tags: str = ""
    version: str = "v1"


class KnowledgePointIn(BaseModel):
    subject: str
    grade: str
    code: str
    title: str
    description: str = ""


class KnowledgePointUpdateIn(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None


class KnowledgeEdgeIn(BaseModel):
    subject: str
    grade: str
    prereq_id: int
    next_id: int


class KnowledgeEdgeOut(BaseModel):
    id: int
    prereq_id: int
    next_id: int


class AdminPracticeReportOut(BaseModel):
    user_id: int
    kp_id: int | None = None
    total: int
    correct: int
    incorrect: int
    accuracy: float
    daily: list[dict] = []
    by_kp: list[dict] = []


class AdminExpressionReportOut(BaseModel):
    user_id: int
    kp_id: int | None = None
    total: int
    avg_confidence: float
    avg_difficulty: float
    by_label: list[dict] = []
    daily: list[dict] = []
    items: list[dict] = []
