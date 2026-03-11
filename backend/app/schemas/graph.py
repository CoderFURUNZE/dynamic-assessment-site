from pydantic import BaseModel


class KnowledgePointOut(BaseModel):
    id: int
    subject: str
    grade: str
    code: str
    title: str
    description: str
    chapter: str = ""
    ability_tag: str = ""
    literacy_tag: str = ""
    importance: float = 0.5
    difficulty: float = 0.5
    practice_total: int | None = None


class GraphRelationNodeOut(BaseModel):
    id: int
    code: str
    title: str


class KnowledgeEdgeOut(BaseModel):
    prereq_id: int
    next_id: int
    relation_type: str = "prerequisite"


class GraphPathOut(BaseModel):
    kp_id: int
    prereq_chain: list[int]
    blocked_prereqs: list[int]
    next_candidates: list[int]


class GraphOverlayNodeOut(BaseModel):
    kp_id: int
    mastery: float
    status: str
    recommended: bool = False
    blocked_reason: str | None = None


class GraphBaseOut(BaseModel):
    course: dict | None = None
    kps: list[KnowledgePointOut]
    edges: list[KnowledgeEdgeOut]


class GraphMapOut(BaseModel):
    base: GraphBaseOut
    overlay: list[GraphOverlayNodeOut]


class GraphResourceOut(BaseModel):
    id: int
    kp_id: int
    type: str
    title: str
    url: str


class GraphTaskOut(BaseModel):
    id: int
    kp_id: int
    type: str
    title: str
    description: str = ""
    link_url: str = ""
    sort_order: int = 0


class GraphPracticeOut(BaseModel):
    id: int
    kp_id: int
    type: str
    prompt: str
    difficulty: float = 0.5


class GraphQuizExamOut(BaseModel):
    kind: str
    id: int
    title: str
    item_count: int = 0
    pass_accuracy: float | None = None
    description: str = ""
    link_url: str = ""


class GraphNodeDetailOut(BaseModel):
    kp: KnowledgePointOut
    overlay: GraphOverlayNodeOut | None = None
    prerequisites: list[GraphRelationNodeOut] = []
    downstream: list[GraphRelationNodeOut] = []
    related: list[GraphRelationNodeOut] = []
    resource_list: list[GraphResourceOut] = []
    task_list: list[GraphTaskOut] = []
    practice_list: list[GraphPracticeOut] = []
    quiz_or_exam_list: list[GraphQuizExamOut] = []
