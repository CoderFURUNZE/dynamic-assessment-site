from pydantic import BaseModel


class CourseStageIn(BaseModel):
    grade: str = "通用"
    title: str
    stage_order: int = 1
    starts_at: str | None = None
    ends_at: str | None = None
    description: str = ""


class CourseStageUpdateIn(BaseModel):
    grade: str | None = None
    title: str | None = None
    stage_order: int | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    description: str | None = None


class CourseStageOut(BaseModel):
    id: int
    course_id: int
    subject: str
    grade: str
    title: str
    stage_order: int
    starts_at: str | None = None
    ends_at: str | None = None
    description: str = ""
    created_at: str


class StageImportBatchOut(BaseModel):
    id: int
    course_id: int
    stage_id: int
    stage_title: str
    subject: str
    grade: str
    metric_type: str
    file_name: str
    uploaded_by: str
    total_rows: int
    success_rows: int
    failed_rows: int
    error_preview: list[str] = []
    created_at: str


class StageMetricGuideOut(BaseModel):
    metric_type: str
    label: str
    summary: str
    template_fields: list[str] = []
    affected_dimensions: list[str] = []
    affected_indicators: list[str] = []
    next_action: str = ""


class StageImportResultOut(BaseModel):
    batch_id: int
    metric_type: str
    total_rows: int
    success_rows: int
    failed_rows: int
    errors: list[str] = []
    affected_dimensions: list[str] = []
    affected_indicators: list[str] = []
    recalculated_users: int = 0
    next_action: str = ""
    import_summary: dict = {}
