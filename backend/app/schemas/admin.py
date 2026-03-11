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
    type: str
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
    chapter: str = ""
    ability_tag: str = ""
    literacy_tag: str = ""
    importance: float = 0.5
    difficulty: float = 0.5


class KnowledgePointUpdateIn(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    chapter: str | None = None
    ability_tag: str | None = None
    literacy_tag: str | None = None
    importance: float | None = None
    difficulty: float | None = None


class KpResourceIn(BaseModel):
    kp_id: int
    title: str
    url: str
    type: str = "note"


class KpResourceUpdateIn(BaseModel):
    title: str | None = None
    url: str | None = None
    type: str | None = None


class KpTaskIn(BaseModel):
    kp_id: int
    title: str
    description: str = ""
    link_url: str = ""
    type: str = "task"
    sort_order: int = 0


class KpTaskUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    link_url: str | None = None
    type: str | None = None
    sort_order: int | None = None


class KnowledgeEdgeIn(BaseModel):
    subject: str
    grade: str
    prereq_id: int
    next_id: int
    relation_type: str = "prerequisite"


class KnowledgeEdgeOut(BaseModel):
    id: int
    prereq_id: int
    next_id: int
    relation_type: str = "prerequisite"


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    description: str = ""
    active: bool
    teacher_id: int | None = None


class CourseIn(BaseModel):
    code: str
    title: str
    description: str = ""
    active: bool = True
    teacher_id: int | None = None


class CourseUpdateIn(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    active: bool | None = None
    teacher_id: int | None = None


class PersonaRuleOut(BaseModel):
    subject: str
    grade: str
    thresholds: dict
    weights: dict
    strategies: dict


class PortraitDimensionIn(BaseModel):
    code: str
    title: str
    description: str = ""
    sort_order: int = 0
    active: bool = True


class PortraitDimensionUpdateIn(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class PortraitIndicatorIn(BaseModel):
    dimension_id: int
    code: str
    title: str
    description: str = ""
    source_type: str = "auto"
    default_weight: float = 1.0
    sort_order: int = 0
    active: bool = True


class PortraitIndicatorUpdateIn(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    source_type: str | None = None
    default_weight: float | None = None
    sort_order: int | None = None
    active: bool | None = None


class CourseIndicatorSelectionIn(BaseModel):
    selections: list[dict] = []


class TeacherPortraitIndicatorInputIn(BaseModel):
    stage_id: int
    user_id: int
    inputs: list[dict] = []
    indicator_scores: list[dict] = []


class QuestionnairePortraitIndicatorInputIn(BaseModel):
    user_id: int | None = None
    inputs: list[dict] = []
    indicator_scores: list[dict] = []


class PersonaOverrideIn(BaseModel):
    user_id: int
    subject: str
    grade: str
    persona_type: str
    note: str = ""


class PersonaOverrideOut(BaseModel):
    user_id: int
    subject: str
    grade: str
    persona_type: str
    note: str = ""
    updated_by: str = ""
    updated_at: str


class AdminAnalyticsOut(BaseModel):
    subject: str
    grade: str
    total_students: int
    persona_distribution: list[dict] = []
    stage_summary: list[dict] = []
    latest_stage: dict | None = None
    risk_students: list[dict] = []
    weak_kps: list[dict] = []
    progress_ranking: list[dict] = []


class AdminPracticeReportOut(BaseModel):
    user_id: int
    kp_id: int | None = None
    total: int
    correct: int
    incorrect: int
    accuracy: float
    daily: list[dict] = []
    by_kp: list[dict] = []


class AuditLogOut(BaseModel):
    id: int
    actor: str
    role: str
    action: str
    detail: str
    created_at: str
