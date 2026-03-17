from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class CourseEnrollStatus(str, Enum):
    open = "open"
    full = "full"
    closed = "closed"
    expired = "expired"


class ApplicationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EnrollmentStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"


class NotificationStatus(str, Enum):
    unread = "unread"
    read = "read"


class PortraitIndicatorSourceType(str, Enum):
    auto = "auto"
    imported = "imported"
    teacher = "teacher"
    questionnaire = "questionnaire"


class PersonaType(str, Enum):
    smart = "smart_capable"
    diligent = "diligent"
    struggling = "struggling_persistent"
    procrastinating = "procrastinating_risk"
    steady = "steady_progress"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.student)
    active: bool = Field(default=True, index=True)
    full_name: str = ""
    student_no: str = ""
    class_name: str = ""
    phone: Optional[str] = Field(default=None, index=True)
    wechat_openid: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (UniqueConstraint("username"), UniqueConstraint("phone"), UniqueConstraint("wechat_openid"))


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    title: str
    description: str = ""
    active: bool = True
    teacher_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    max_students: int = Field(default=200)
    apply_deadline: Optional[datetime] = Field(default=None, index=True)
    enroll_status: CourseEnrollStatus = Field(default=CourseEnrollStatus.open, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("code"),)


class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    application_id: Optional[int] = Field(default=None, foreign_key="courseapplication.id", index=True)
    status: EnrollmentStatus = Field(default=EnrollmentStatus.active, index=True)
    enrolled_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("student_id", "course_id"),)


class CoursePrerequisite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    prerequisite_course_id: int = Field(foreign_key="course.id", index=True)

    __table_args__ = (UniqueConstraint("course_id", "prerequisite_course_id"),)


class CourseApplication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    apply_reason: str = ""
    status: ApplicationStatus = Field(default=ApplicationStatus.pending, index=True)
    review_remark: str = ""
    reject_reason: str = ""
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    reviewed_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("student_id", "course_id"),)


class CourseNotification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    type: str = Field(default="COURSE")
    title: str
    content: str
    status: NotificationStatus = Field(default=NotificationStatus.unread, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class CourseCompletionRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    student_id: int = Field(foreign_key="user.id", index=True)
    completed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    note: str = ""

    __table_args__ = (UniqueConstraint("course_id", "student_id"),)


class KnowledgePoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    code: str = Field(index=True)
    title: str
    description: str = ""
    chapter: str = ""
    ability_tag: str = ""
    literacy_tag: str = ""
    importance: float = 0.5
    difficulty: float = 0.5
    pos_x: Optional[float] = Field(default=None)
    pos_y: Optional[float] = Field(default=None)
    practice_total: Optional[int] = Field(default=None)

    __table_args__ = (UniqueConstraint("code"),)


class RelationType(str, Enum):
    prerequisite = "prerequisite"
    related = "related"


class KnowledgeEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    prereq_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    next_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    relation_type: RelationType = Field(default=RelationType.prerequisite, index=True)

    __table_args__ = (UniqueConstraint("prereq_id", "next_id"),)


class ChapterEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    source_chapter: str = Field(index=True)
    target_chapter: str = Field(index=True)
    relation_type: RelationType = Field(default=RelationType.related, index=True)

    __table_args__ = (UniqueConstraint("subject", "grade", "source_chapter", "target_chapter"),)


class ResourceType(str, Enum):
    video = "video"
    pdf = "pdf"
    note = "note"
    doc = "doc"
    docx = "docx"
    ppt = "ppt"
    pptx = "pptx"
    image = "image"
    link = "link"
    example = "example"
    book = "book"
    recommend_book = "recommend_book"


class LearningResource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    title: str
    url: str
    type: ResourceType = Field(default=ResourceType.video)
    category: str = Field(default="learning", index=True)
    description: str = ""
    tags: str = ""
    original_file_name: str = ""
    file_extension: str = ""
    detected_mime_type: str = ""
    detected_resource_type: str = ""
    preview_type: str = ""
    preview_status: str = Field(default="ready", index=True)
    preview_error: str = ""
    converted_preview_url: str = ""
    original_file_url: str = ""
    file_size_bytes: int = 0
    extension_mismatch: bool = False
    source_kind: str = Field(default="external", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class KpTaskType(str, Enum):
    task = "task"
    exam = "exam"


class KpTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    title: str
    description: str = ""
    link_url: str = ""
    type: KpTaskType = Field(default=KpTaskType.task, index=True)
    sort_order: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class StageMetricType(str, Enum):
    video = "video"
    assignment = "assignment"
    quiz = "quiz"
    attendance = "attendance"
    task = "task"
    participation = "participation"


class CourseStage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    title: str
    stage_order: int = Field(default=1, index=True)
    starts_at: Optional[datetime] = Field(default=None, index=True)
    ends_at: Optional[datetime] = Field(default=None, index=True)
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("course_id", "stage_order"),)


class StageImportBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    stage_id: int = Field(foreign_key="coursestage.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    metric_type: StageMetricType = Field(index=True)
    file_name: str = ""
    uploaded_by: str = ""
    total_rows: int = 0
    success_rows: int = 0
    failed_rows: int = 0
    error_json: str = "[]"
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class StageImportRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="stageimportbatch.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    stage_id: int = Field(foreign_key="coursestage.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kp_id: Optional[int] = Field(default=None, foreign_key="knowledgepoint.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    metric_type: StageMetricType = Field(index=True)
    score_value: float = 0.0
    completion_value: float = 0.0
    duration_minutes: float = 0.0
    attendance_value: float = 0.0
    submitted_on_time: bool = False
    status: str = ""
    note: str = ""
    happened_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    raw_json: str = "{}"


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
    self_report: str = Field(default="unknown")
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
    direct_value: float = 0.0
    status: str = "not_started"
    reason_summary: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "kp_id"),)


class EvalConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    weights_json: str = (
        '{"quiz_accuracy":0.2,"practice_accuracy":0.65,"video_completion":0.05,"duration_penalty":0.0}'
    )
    thresholds_json: str = '{"unlock_accuracy":0.9,"unlock_max_difficulty":0.35}'
    window_json: str = (
        '{"practice_attempts":10,"practice_total":10,'
        '"evidence_sure_ratio":0.5,'
        '"video_complete_ratio":0.8,"video_min_ratio":0.0,'
        '"max_difficulty_jump":0.2,"stability_strength":0.4}'
    )

    __table_args__ = (UniqueConstraint("subject", "grade"),)


class PortraitDimension(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    title: str
    description: str = ""
    sort_order: int = Field(default=0, index=True)
    active: bool = True

    __table_args__ = (UniqueConstraint("code"),)


class PortraitIndicator(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dimension_id: int = Field(foreign_key="portraitdimension.id", index=True)
    code: str = Field(index=True)
    title: str
    description: str = ""
    source_type: PortraitIndicatorSourceType = Field(default=PortraitIndicatorSourceType.auto, index=True)
    default_weight: float = 1.0
    sort_order: int = Field(default=0, index=True)
    active: bool = True

    __table_args__ = (UniqueConstraint("dimension_id", "code"),)


class CoursePortraitIndicatorSelection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    dimension_id: int = Field(foreign_key="portraitdimension.id", index=True)
    indicator_id: int = Field(foreign_key="portraitindicator.id", index=True)
    enabled: bool = True
    weight: float = 1.0
    selected_by: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("course_id", "indicator_id"),)


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


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str = Field(index=True)
    role: str = Field(index=True)
    action: str = Field(index=True)
    detail: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class LearnerPersonaRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    thresholds_json: str = (
        '{"procrastinating_e":0.4,"smart_a":0.75,"smart_f":0.75,'
        '"diligent_e":0.75,"diligent_a":0.6,"struggling_e":0.6,"struggling_a":0.6}'
    )
    weights_json: str = (
        '{"engagement":{"learning_frequency":0.35,"study_duration":0.35,"resource_completion":0.2,"streak":0.1},'
        '"achievement":{"practice_accuracy":0.5,"quiz_accuracy":0.3,"mastery_growth":0.2},'
        '"efficiency":{"unit_time_accuracy":0.6,"task_completion":0.4},'
        '"risk":{"overdue_rate":0.4,"wrong_streak":0.3,"abandonment_rate":0.3},'
        '"dynamic":{"engagement":0.25,"achievement":0.3,"course_mastery":0.35,"stability":0.1},'
        '"stage_dimensions":{"engagement":{"enabled":true,"weight":0.3,"metrics":{"activity_frequency":0.25,"study_duration":0.35,"completion":0.25,"attendance_participation":0.15}},'
        '"achievement":{"enabled":true,"weight":0.35,"metrics":{"assignment_score":0.35,"quiz_score":0.35,"task_score":0.15,"stage_mastery":0.15}},'
        '"habit":{"enabled":true,"weight":0.2,"metrics":{"on_time_rate":0.4,"attendance_rate":0.35,"continuity":0.25}},'
        '"characteristic":{"enabled":true,"weight":0.15,"metrics":{"participation":0.35,"task_completion":0.35,"resource_initiative":0.3}}}}'
    )
    strategy_json: str = (
        '{"smart_capable":"更高难度+精讲提要","diligent":"结构化路径+阶段反馈",'
        '"struggling_persistent":"补救前置点+低阶练习","procrastinating_risk":"最短任务链+提醒",'
        '"steady_progress":"标准推荐"}'
    )

    __table_args__ = (UniqueConstraint("subject", "grade"),)


class LearnerPersonaOverride(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    persona_type: PersonaType = Field(index=True)
    note: str = ""
    updated_by: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "subject", "grade"),)


class LearnerProfileSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    persona_type: PersonaType = Field(index=True)
    engagement: float = 0.0
    achievement: float = 0.0
    efficiency: float = 0.0
    risk: float = 0.0
    course_mastery: float = 0.0
    dynamic_score: float = 0.0
    stability: float = 0.0
    risk_level: str = "warning"
    override_source: str = "auto"
    reason_summary: str = ""
    portrait_summary_json: str = "{}"
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class StageEvaluationSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    stage_id: int = Field(foreign_key="coursestage.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    stage_title: str = ""
    stage_order: int = Field(default=1, index=True)
    persona_type: PersonaType = Field(index=True)
    engagement: float = 0.0
    achievement: float = 0.0
    habit: float = 0.0
    characteristic: float = 0.0
    efficiency: float = 0.0
    risk: float = 0.0
    course_mastery: float = 0.0
    dynamic_score: float = 0.0
    trend_label: str = "持平"
    risk_level: str = "预警"
    reason_summary: str = ""
    dimension_summary_json: str = "{}"
    indicator_summary_json: str = "{}"
    enabled_dimensions_json: str = "{}"
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "stage_id"),)


class StageTeacherFeedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    stage_id: int = Field(foreign_key="coursestage.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    feedback_tag: str = ""
    comment: str = ""
    updated_by: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "stage_id"),)


class TeacherFinalScoreConfirmation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    suggested_score: float = 0.0
    confirmed_score: float = 0.0
    confirmed_level: str = ""
    comment: str = ""
    recommendation_summary: str = ""
    confirmed_by: str = ""
    confirmed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "course_id"),)


class TeacherPortraitIndicatorInput(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    stage_id: int = Field(foreign_key="coursestage.id", index=True)
    dimension_id: int = Field(foreign_key="portraitdimension.id", index=True)
    indicator_id: int = Field(foreign_key="portraitindicator.id", index=True)
    score: float = 0.0
    note: str = ""
    updated_by: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "stage_id", "indicator_id"),)


class QuestionnairePortraitIndicatorInput(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    dimension_id: int = Field(foreign_key="portraitdimension.id", index=True)
    indicator_id: int = Field(foreign_key="portraitindicator.id", index=True)
    score: float = 0.0
    note: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("user_id", "course_id", "indicator_id"),)


class LearningBehaviorEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: Optional[int] = Field(default=None, foreign_key="course.id", index=True)
    kp_id: Optional[int] = Field(default=None, foreign_key="knowledgepoint.id", index=True)
    event_type: str = Field(index=True)
    value_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RecommendationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    subject: str = Field(index=True)
    grade: str = Field(index=True)
    source_kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    target_kp_id: int = Field(foreign_key="knowledgepoint.id", index=True)
    persona_type: PersonaType = Field(index=True)
    reason_summary: str = ""
    payload_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
