from pydantic import BaseModel


class RecommendationOut(BaseModel):
    diagnosis: dict
    remedy_path: dict
    resources: list[dict]
    practice: list[dict]
    unlock: dict

