from pydantic import BaseModel


class ResourceOut(BaseModel):
    id: int
    kp_id: int
    type: str
    title: str
    url: str
    category: str = "learning"
    description: str = ""
    tags: str = ""
    original_file_name: str = ""
    file_extension: str = ""
    detected_mime_type: str = ""
    detected_resource_type: str = ""
    preview_type: str = ""
    preview_status: str = "ready"
    preview_error: str = ""
    converted_preview_url: str = ""
    original_file_url: str = ""
    file_size_bytes: int = 0
    extension_mismatch: bool = False
    source_kind: str = "external"


class QuizItemOut(BaseModel):
    id: int
    type: str
    prompt: str
    options: list[str]
    # Only returned for non-student roles (admin/teacher) for preview/edit convenience.
    answer: str | None = None
    explanation: str | None = None


class QuizOut(BaseModel):
    quiz_id: int
    kp_id: int
    items: list[QuizItemOut]


class QuizSubmitIn(BaseModel):
    quiz_id: int
    kp_id: int
    answers: list[dict]
    duration_ms: int = 0


class QuizSubmitOut(BaseModel):
    passed: bool
    accuracy: float
    details: list[dict]


class VideoProgressIn(BaseModel):
    kp_id: int
    resource_id: int
    position_seconds: float
    duration_seconds: float
    watched_delta_seconds: float = 0.0
    playback_rate: float = 1.0


class VideoProgressOut(BaseModel):
    kp_id: int
    resource_id: int
    watched_seconds: float
    duration_seconds: float
    completed: bool


class ResourceVisitIn(BaseModel):
    kp_id: int
    resource_id: int
    action: str = "visit"
