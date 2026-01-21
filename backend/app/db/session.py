from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import inspect, text

from app.core.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_kp_practice_total_column()


def _ensure_kp_practice_total_column() -> None:
    inspector = inspect(engine)
    try:
        cols = {c["name"] for c in inspector.get_columns("knowledgepoint")}
    except Exception:
        return
    if "practice_total" in cols:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE knowledgepoint ADD COLUMN practice_total INTEGER"))
    except Exception:
        # Best-effort; ignore if the column was added by another process.
        pass


def get_session():
    with Session(engine) as session:
        yield session
