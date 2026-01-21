from pydantic import BaseModel


class KnowledgePointOut(BaseModel):
    id: int
    subject: str
    grade: str
    code: str
    title: str
    description: str


class KnowledgeEdgeOut(BaseModel):
    prereq_id: int
    next_id: int


class GraphPathOut(BaseModel):
    kp_id: int
    prereq_chain: list[int]
    blocked_prereqs: list[int]
    next_candidates: list[int]

