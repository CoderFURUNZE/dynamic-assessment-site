from pydantic import BaseModel


class PageOut(BaseModel):
    items: list
    total: int
    page: int
    page_size: int

