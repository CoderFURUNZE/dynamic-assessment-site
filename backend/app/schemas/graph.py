from pydantic import BaseModel, Field


class KnowledgePointOut(BaseModel):
    id: int
    subject: str
    grade: str
    code: str
    title: str
    description: str
    chapter: str = ""
    knowledge_tag: str = ""
    ability_tag: str = ""
    literacy_tag: str = ""
    importance: float = 0.5
    difficulty: float = 0.5
    pos_x: float | None = None
    pos_y: float | None = None
    practice_total: int | None = None


class GraphRelationNodeOut(BaseModel):
    id: int
    code: str
    title: str


class GraphNodeNavOut(BaseModel):
    previous: GraphRelationNodeOut | None = None
    next: GraphRelationNodeOut | None = None
    chapter_nodes: list[GraphRelationNodeOut] = []


class KnowledgeEdgeOut(BaseModel):
    prereq_id: int
    next_id: int
    relation_type: str = "prerequisite"


class ChapterEdgeOut(BaseModel):
    id: int
    source_chapter: str
    target_chapter: str
    relation_type: str = "related"


class GraphPathOut(BaseModel):
    kp_id: int
    prereq_chain: list[int]
    blocked_prereqs: list[int]
    blocked_titles: list[str] = []
    next_candidates: list[int]
    next_titles: list[str] = []
    can_unlock_next: bool = False
    path_summary: str = ""


class GraphOverlayNodeOut(BaseModel):
    kp_id: int
    mastery: float
    status: str
    recommended: bool = False
    blocked_reason: str | None = None
    knowledge_enabled: bool = True
    ability_enabled: bool = False
    literacy_enabled: bool = False
    knowledge_status: str = "not_started"
    ability_status: str = "not_started"
    literacy_status: str = "not_started"
    knowledge_label: str = ""
    ability_labels: list[str] = []
    literacy_labels: list[str] = []
    evidence: dict = {}


class GraphBaseOut(BaseModel):
    course: dict | None = None
    kps: list[KnowledgePointOut]
    edges: list[KnowledgeEdgeOut]
    chapter_layout: dict[str, dict[str, float]] = Field(default_factory=dict)


class GraphMapOut(BaseModel):
    base: GraphBaseOut
    overlay: list[GraphOverlayNodeOut]


class GraphResourceOut(BaseModel):
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
    navigation: GraphNodeNavOut | None = None
    prerequisites: list[GraphRelationNodeOut] = []
    downstream: list[GraphRelationNodeOut] = []
    related: list[GraphRelationNodeOut] = []
    resource_list: list[GraphResourceOut] = []
    task_list: list[GraphTaskOut] = []
    practice_list: list[GraphPracticeOut] = []
    quiz_or_exam_list: list[GraphQuizExamOut] = []
