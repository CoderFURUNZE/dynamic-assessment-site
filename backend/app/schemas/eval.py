from pydantic import BaseModel, ConfigDict


class MasteryOut(BaseModel):
    kp_id: int
    value: float
    label: str
    direct_value: float = 0.0
    status: str = "not_started"
    reason_summary: str = ""


class ProfileTrendPointOut(BaseModel):
    updated_at: str
    dynamic_score: float
    course_mastery: float
    persona_type: str
    stage_title: str | None = None
    trend_label: str | None = None


class PortraitTimelinePointOut(BaseModel):
    updated_at: str
    persona_label: str
    dynamic_score: float
    course_mastery: float
    risk_level: str = "预警"
    stage_title: str | None = None
    trend_label: str | None = None
    reason_summary: str = ""


class DynamicBreakdownOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    learning_frequency: float = 0.0
    study_duration: float = 0.0
    resource_completion: float = 0.0
    streak: float = 0.0
    practice_accuracy: float = 0.0
    quiz_accuracy: float = 0.0
    mastery_growth: float = 0.0
    unit_time_accuracy: float = 0.0
    task_completion: float = 0.0
    overdue_rate: float = 0.0
    wrong_streak: float = 0.0
    abandonment_rate: float = 0.0
    engagement_score: float = 0.0
    achievement_score: float = 0.0
    efficiency_score: float = 0.0
    risk_score: float = 0.0
    dynamic_score: float = 0.0
    stability: float = 0.0
    summary: str = ""


class PersonaSignalOut(BaseModel):
    """学生端可解释的画像信号（与 reason_summary 互补，偏结构化展示）。"""

    key: str
    label: str
    detail: str
    level: str = "neutral"  # positive | neutral | attention


class StageDimensionConfigOut(BaseModel):
    key: str
    label: str
    enabled: bool = True
    weight: float = 0.0


class TeacherFeedbackOut(BaseModel):
    stage_id: int
    feedback_tag: str = ""
    comment: str = ""
    updated_by: str = ""
    updated_at: str | None = None


class CurrentStageOut(BaseModel):
    course_id: int | None = None
    stage_id: int
    stage_title: str
    stage_order: int
    engagement: float = 0.0
    achievement: float = 0.0
    habit: float = 0.0
    characteristic: float = 0.0
    dynamic_score: float = 0.0
    course_mastery: float = 0.0
    trend_label: str = "持平"
    risk_level: str = "预警"
    reason_summary: str = ""
    portrait_dimensions: list[dict] = []
    portrait_indicators: list[dict] = []


class ProfileOut(BaseModel):
    user_id: int
    course_id: int | None = None
    subject: str
    grade: str
    mastery_map: list[dict]
    weak_points: list[int]
    persona_type: str = "steady_progress"
    persona_label: str = "平稳发展型"
    engagement: float = 0.0
    achievement: float = 0.0
    habit: float = 0.0
    characteristic: float = 0.0
    efficiency: float = 0.0
    risk: float = 0.0
    course_mastery: float = 0.0
    dynamic_score: float = 0.0
    stability: float = 0.0
    risk_level: str = "预警"
    override_source: str = "auto"
    reason_summary: str = ""
    trend: list[ProfileTrendPointOut] = []
    current_stage: CurrentStageOut | None = None
    stage_history: list[CurrentStageOut] = []
    dimension_config: list[StageDimensionConfigOut] = []
    teacher_feedback: TeacherFeedbackOut | None = None
    portrait_dimensions: list[dict] = []
    portrait_indicators: list[dict] = []
    final_portrait_dimensions: list[dict] = []
    final_portrait_indicators: list[dict] = []
    term_summary: dict = {}
    kp_dimension_summary: dict = {}
    ability_practice_stats: dict = {}
    portrait_timeline: list[PortraitTimelinePointOut] = []
    dynamic_breakdown: DynamicBreakdownOut | None = None
    persona_signals: list[PersonaSignalOut] = []
    persona_intro: str = ""
    learning_behavior_overview: dict = {}
    behavior_timeline: list[dict] = []
    recent_practice_records: list[dict] = []
    recent_quiz_records: list[dict] = []
    recent_video_records: list[dict] = []


class MasteryMapItem(BaseModel):
    kp_id: int
    code: str
    title: str
    chapter: str = ""
    mastery: float
    direct_value: float = 0.0
    status: str = "not_started"
    reason_summary: str = ""


class OverviewSummaryOut(BaseModel):
    total_kps: int
    mastered: int
    in_progress: int
    not_mastered: int
    avg_mastery: float
    dynamic_score: float = 0.0
    risk_level: str = "预警"


class OverviewRecentOut(BaseModel):
    last_practice_at: str | None = None
    last_quiz_at: str | None = None
    last_video_at: str | None = None


class OverviewPracticeOut(BaseModel):
    total: int
    correct: int
    accuracy: float


class OverviewOut(BaseModel):
    subject: str
    grade: str
    summary: OverviewSummaryOut
    mastery_map: list[MasteryMapItem]
    weak_points: list[MasteryMapItem]
    recent_activity: OverviewRecentOut
    practice_7d: OverviewPracticeOut
    review_due: int = 0
    profile: ProfileOut | None = None
