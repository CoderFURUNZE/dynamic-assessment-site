from pydantic import BaseModel


class MasteryOut(BaseModel):
    kp_id: int
    value: float
    label: str


class ProfileOut(BaseModel):
    user_id: int
    subject: str
    grade: str
    mastery_map: list[dict]
    weak_points: list[int]


class MasteryMapItem(BaseModel):
    kp_id: int
    code: str
    title: str
    mastery: float


class OverviewSummaryOut(BaseModel):
    total_kps: int
    mastered: int
    in_progress: int
    not_mastered: int
    avg_mastery: float


class OverviewRecentOut(BaseModel):
    last_practice_at: str | None = None
    last_quiz_at: str | None = None
    last_video_at: str | None = None
    last_expression_at: str | None = None


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
