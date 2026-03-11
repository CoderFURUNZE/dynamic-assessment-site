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
    _ensure_question_meta_columns()
    _ensure_practice_attempt_columns()
    _ensure_course_columns()
    _ensure_legacy_course_teacher_assignment()
    _ensure_knowledgepoint_columns()
    _ensure_knowledgeedge_columns()
    _ensure_mastery_columns()
    _ensure_stage_snapshot_columns()
    _ensure_profile_snapshot_columns()


def _ensure_columns(table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    try:
        existing = {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return
    missing = {name: ddl for name, ddl in columns.items() if name not in existing}
    if not missing:
        return
    try:
        with engine.begin() as conn:
            for ddl in missing.values():
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
    except Exception:
        pass


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


def _ensure_question_meta_columns() -> None:
    inspector = inspect(engine)
    try:
        cols = {c["name"] for c in inspector.get_columns("question")}
    except Exception:
        return
    needed = ["source", "tags", "version"]
    missing = [c for c in needed if c not in cols]
    if not missing:
        return
    try:
        with engine.begin() as conn:
            for col in missing:
                conn.execute(text(f"ALTER TABLE question ADD COLUMN {col} TEXT"))
    except Exception:
        pass


def _ensure_practice_attempt_columns() -> None:
    inspector = inspect(engine)
    try:
        cols = {c["name"] for c in inspector.get_columns("practiceattempt")}
    except Exception:
        return
    if "self_report" in cols:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE practiceattempt ADD COLUMN self_report TEXT"))
    except Exception:
        pass


def _ensure_course_columns() -> None:
    _ensure_columns(
        "course",
        {
            "teacher_id": "teacher_id INTEGER",
        },
    )


def _ensure_legacy_course_teacher_assignment() -> None:
    # Legacy seed data predates teacher ownership. If there is exactly one
    # teacher user, assign any unowned courses to that teacher so teacher-side
    # course management remains usable after schema upgrades.
    try:
        with engine.begin() as conn:
            teachers = conn.execute(text("SELECT id FROM \"user\" WHERE role='teacher' ORDER BY id")).fetchall()
            if len(teachers) != 1:
                return
            teacher_id = int(teachers[0][0])
            conn.execute(text("UPDATE course SET teacher_id=:teacher_id WHERE teacher_id IS NULL"), {"teacher_id": teacher_id})
    except Exception:
        pass


def _ensure_knowledgepoint_columns() -> None:
    _ensure_columns(
        "knowledgepoint",
        {
            "chapter": "chapter TEXT DEFAULT ''",
            "ability_tag": "ability_tag TEXT DEFAULT ''",
            "literacy_tag": "literacy_tag TEXT DEFAULT ''",
            "importance": "importance FLOAT DEFAULT 0.5",
            "difficulty": "difficulty FLOAT DEFAULT 0.5",
        },
    )


def _ensure_knowledgeedge_columns() -> None:
    _ensure_columns(
        "knowledgeedge",
        {
            "relation_type": "relation_type TEXT DEFAULT 'prerequisite'",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE knowledgeedge SET relation_type='prerequisite' WHERE relation_type IS NULL"))
    except Exception:
        pass


def _ensure_mastery_columns() -> None:
    _ensure_columns(
        "mastery",
        {
            "direct_value": "direct_value FLOAT DEFAULT 0.0",
            "status": "status TEXT DEFAULT 'not_started'",
            "reason_summary": "reason_summary TEXT DEFAULT ''",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE mastery SET status='not_started' WHERE status IS NULL"))
            conn.execute(text("UPDATE mastery SET reason_summary='' WHERE reason_summary IS NULL"))
            conn.execute(text("UPDATE mastery SET direct_value=0.0 WHERE direct_value IS NULL"))
    except Exception:
        pass


def _ensure_stage_snapshot_columns() -> None:
    _ensure_columns(
        "stageevaluationsnapshot",
        {
            "trend_label": "trend_label TEXT DEFAULT '持平'",
            "dimension_summary_json": "dimension_summary_json TEXT DEFAULT '{}'",
            "indicator_summary_json": "indicator_summary_json TEXT DEFAULT '{}'",
            "enabled_dimensions_json": "enabled_dimensions_json TEXT DEFAULT '{}'",
        },
    )


def _ensure_profile_snapshot_columns() -> None:
    _ensure_columns(
        "learnerprofilesnapshot",
        {
            "portrait_summary_json": "portrait_summary_json TEXT DEFAULT '{}'",
        },
    )


def get_session():
    with Session(engine) as session:
        yield session
