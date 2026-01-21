from pydantic import BaseModel


class VisionFrameIn(BaseModel):
    type: str = "frame"
    image_b64: str
    kp_id: int
    ts: int | None = None


class VisionAnalysisOut(BaseModel):
    type: str = "analysis"
    kp_id: int
    label: str
    confidence: float
    difficulty: float

