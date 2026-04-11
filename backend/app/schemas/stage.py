from typing import Any

from pydantic import BaseModel, Field


class CourseStageIn(BaseModel):
    grade: str = Field(default="通用", description="阶段所属年级")
    title: str
    stage_order: int = Field(default=1, ge=1)
    starts_at: str | None = None
    ends_at: str | None = None
    description: str = ""


class CourseStageUpdateIn(BaseModel):
    grade: str | None = None
    title: str | None = None
    stage_order: int | None = Field(default=None, ge=1)
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
    error_preview: list[str] = Field(default_factory=list)
    created_at: str


class StageMetricGuideOut(BaseModel):
    metric_type: str
    label: str
    summary: str
    template_fields: list[str] = Field(default_factory=list)
    affected_dimensions: list[str] = Field(default_factory=list)
    affected_indicators: list[str] = Field(default_factory=list)
    next_action: str = ""


class StageImportResultOut(BaseModel):
    batch_id: int
    metric_type: str
    total_rows: int
    success_rows: int
    failed_rows: int
    errors: list[str] = Field(default_factory=list)
    affected_dimensions: list[str] = Field(default_factory=list)
    affected_indicators: list[str] = Field(default_factory=list)
    recalculated_users: int = 0
    next_action: str = ""
    import_summary: dict[str, Any] = Field(default_factory=dict)
