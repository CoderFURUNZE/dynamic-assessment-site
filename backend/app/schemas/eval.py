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

