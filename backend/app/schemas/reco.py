from pydantic import BaseModel


class RecommendationTargetOut(BaseModel):
    id: int
    code: str
    title: str
    chapter: str = ""
    mastery: float = 0.0


class RecommendationOut(BaseModel):
    target_kp: RecommendationTargetOut
    reason_summary: str
    recommendation_stage: str
    recommendation_stage_label: str
    resource_list: list[dict]
    practice_list: list[dict]
    advice_text: str
    persona_strategy_tag: str
    persona_type: str
    persona_label: str
    dynamic_score: float
    risk_level: str
    diagnosis: dict
    evidence: dict
    triple: dict = {}
    remedy: dict
    remedy_path: dict
    resources: list[dict]
    practice: list[dict]
    unlock: dict
