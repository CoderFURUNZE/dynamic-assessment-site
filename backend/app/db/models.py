from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.student)
    full_name: str = ""
    student_no: str = ""
    class_name: str = ""
    phone: Optional[str] = Field(default=None, index=True)
    wechat_openid: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (UniqueConstraint("username"), UniqueConstraint("phone"), UniqueConstraint("wechat_openid"))


class KnowledgePoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    code: str = Field(index=True)
    title: str
    description: str = ""
    practice_total: Optional[int] = Field(default=None)

    __table_args__ = (UniqueConstraint("code"),)


class KnowledgeEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    prereq_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    next_id: int = Field(foreign_key="knowledgepoint.id", index=True)

    __table_args__ = (UniqueConstraint("prereq_id", "next_id"),)


class ResourceType(str, Enum):
    video = "video"
    note = "note"
    example = "example"


class LearningResource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    title: str
    url: str
    type: ResourceType = Field(default=ResourceType.video)


class Quiz(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    pass_accuracy: float = 0.8
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuizItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(foreign_key="quiz.id", index=True)
    type: str  # "mcq" | "blank"
    prompt: str
    options_json: str = "[]"
    answer: str
    explanation: str = ""
    key_item: bool = False


class QuizAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    quiz_id: int = Field(foreign_key="quiz.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    score: float
    passed: bool
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Question(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    type: str  # "mcq" | "blank"
    prompt: str
    options_json: str = "[]"
    answer: str
    explanation: str = ""
    difficulty: float = 0.5
    source: str = ""
    tags: str = ""
    version: str = "v1"


class PracticeAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    correct: bool
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ReviewSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    interval_days: int = Field(default=1)
    due_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_result: str = "wrong"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "question_id"),)


class ExpressionEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    label: str
    confidence: float
    difficulty: float
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Mastery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    value: float = Field(default=0.0, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "kp_id"),)


class EvalConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    weights_json: str = (
        '{"quiz_accuracy":0.2,"practice_accuracy":0.65,"expression_ease":0.1,"video_completion":0.05,"duration_penalty":0.0}'
    )
    thresholds_json: str = '{"unlock_accuracy":0.9,"unlock_max_difficulty":0.35}'
    window_json: str = (
        '{"practice_attempts":10,"expressions":20,"practice_total":10,'
        '"difficulty_step":0.1,"expression_conf_threshold":0.2,"expression_influence":1.0,'
        '"video_complete_ratio":0.8,"video_min_ratio":0.0,'
        '"max_difficulty_jump":0.2,"stability_strength":0.4}'
    )

    __table_args__ = (UniqueConstraint("subject", "grade"),)


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class VideoProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    resource_id: int = Field(foreign_key="learningresource.id", index=True)

    watched_seconds: float = 0.0
    duration_seconds: float = 0.0
    last_position_seconds: float = 0.0
    completed: bool = False

    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "resource_id"),)


class KpQuestionAssignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    order: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("kp_id", "question_id"),)


class InterviewSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    duration_minutes: int = 15
    total_questions: int = 0
    question_ids_json: str = "[]"
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = Field(default=None, index=True)


class InterviewAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interviewsession.id", index=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    answer: str
    correct: bool
    rationale: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
