from pydantic import BaseModel


class NoteCreateIn(BaseModel):
    kp_id: int
    content: str


class NoteOut(BaseModel):
    id: int
    kp_id: int
    author: str
    content: str
    created_at: str

