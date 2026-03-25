from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import inspect, text

from app.core.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_portrait_indicator_source_values()
    _ensure_resource_type_values()
    _ensure_relation_type_values()
    _ensure_user_columns()
    _ensure_kp_practice_total_column()
    _ensure_question_meta_columns()
    _ensure_practice_attempt_columns()
    _ensure_course_columns()
    _ensure_legacy_course_teacher_assignment()
    _ensure_knowledgepoint_columns()
    _ensure_knowledgeedge_columns()
    _ensure_mastery_columns()
    _ensure_learning_resource_columns()
    _ensure_stage_snapshot_columns()
    _ensure_profile_snapshot_columns()
    _ensure_enrollment_columns()
    _ensure_final_score_confirmation_columns()
    _normalize_legacy_status_values()


def _is_postgres() -> bool:
    return engine.dialect.name.lower().startswith("postgres")


def _ensure_columns(table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    try:
        existing = {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return
    missing = {name: ddl for name, ddl in columns.items() if name not in existing}
    if not missing:
        return
    for ddl in missing.values():
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
        except Exception:
            # Best-effort compatibility migration: keep progressing even if a
            # single column DDL fails, so other missing columns can still be added.
            pass


def _ensure_portrait_indicator_source_values() -> None:
    if not _is_postgres():
        return
    statements = [
        "ALTER TYPE portraitindicatorsourcetype ADD VALUE IF NOT EXISTS 'imported'",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass


def _ensure_resource_type_values() -> None:
    if not _is_postgres():
        return
    statements = [
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'pdf'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'doc'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'docx'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'ppt'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'pptx'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'image'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'link'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'book'",
        "ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'recommend_book'",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass


def _ensure_relation_type_values() -> None:
    if not _is_postgres():
        return
    statements = [
        "ALTER TYPE relationtype ADD VALUE IF NOT EXISTS 'support'",
        "ALTER TYPE relationtype ADD VALUE IF NOT EXISTS 'contains'",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass


def _ensure_user_columns() -> None:
    _ensure_columns(
        "user",
        {
            "active": "active BOOLEAN DEFAULT 1",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE \"user\" SET active=1 WHERE active IS NULL"))
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
    apply_deadline_type = "TIMESTAMP" if _is_postgres() else "DATETIME"
    _ensure_columns(
        "course",
        {
            "lifecycle_status": "lifecycle_status TEXT DEFAULT 'draft'",
            "teacher_id": "teacher_id INTEGER",
            "target_class": "target_class TEXT DEFAULT ''",
            "max_students": "max_students INTEGER DEFAULT 200",
            "start_at": f"start_at {apply_deadline_type}",
            "end_at": f"end_at {apply_deadline_type}",
            "archived_at": f"archived_at {apply_deadline_type}",
            "apply_deadline": f"apply_deadline {apply_deadline_type}",
            "enroll_status": "enroll_status TEXT DEFAULT 'open'",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE course SET lifecycle_status='draft' WHERE lifecycle_status IS NULL"))
            conn.execute(text("UPDATE course SET target_class='' WHERE target_class IS NULL"))
    except Exception:
        pass


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
            "knowledge_tag": "knowledge_tag TEXT DEFAULT ''",
            "ability_tag": "ability_tag TEXT DEFAULT ''",
            "literacy_tag": "literacy_tag TEXT DEFAULT ''",
            "importance": "importance FLOAT DEFAULT 0.5",
            "difficulty": "difficulty FLOAT DEFAULT 0.5",
            "pos_x": "pos_x FLOAT",
            "pos_y": "pos_y FLOAT",
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
            conn.execute(text("UPDATE knowledgeedge SET relation_type='prerequisite' WHERE relation_type='forward'"))
            conn.execute(text("UPDATE knowledgeedge SET relation_type='support' WHERE relation_type='backward'"))
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


def _ensure_learning_resource_columns() -> None:
    timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if _is_postgres() else "DATETIME"
    bool_default = "extension_mismatch BOOLEAN DEFAULT FALSE" if _is_postgres() else "extension_mismatch BOOLEAN DEFAULT 0"
    _ensure_columns(
        "learningresource",
        {
            "category": "category TEXT DEFAULT 'learning'",
            "description": "description TEXT DEFAULT ''",
            "tags": "tags TEXT DEFAULT ''",
            "original_file_name": "original_file_name TEXT DEFAULT ''",
            "file_extension": "file_extension TEXT DEFAULT ''",
            "detected_mime_type": "detected_mime_type TEXT DEFAULT ''",
            "detected_resource_type": "detected_resource_type TEXT DEFAULT ''",
            "preview_type": "preview_type TEXT DEFAULT ''",
            "preview_status": "preview_status TEXT DEFAULT 'ready'",
            "preview_error": "preview_error TEXT DEFAULT ''",
            "converted_preview_url": "converted_preview_url TEXT DEFAULT ''",
            "original_file_url": "original_file_url TEXT DEFAULT ''",
            "file_size_bytes": "file_size_bytes INTEGER DEFAULT 0",
            "extension_mismatch": bool_default,
            "source_kind": "source_kind TEXT DEFAULT 'external'",
            "created_at": f"created_at {timestamp_type}",
            "updated_at": f"updated_at {timestamp_type}",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE learningresource SET category='recommend' WHERE category IS NULL AND type IN ('book', 'recommend_book')"))
            conn.execute(text("UPDATE learningresource SET category='learning' WHERE category IS NULL"))
            conn.execute(text("UPDATE learningresource SET preview_status='ready' WHERE preview_status IS NULL"))
            conn.execute(text("UPDATE learningresource SET source_kind='external' WHERE source_kind IS NULL"))
            conn.execute(text("UPDATE learningresource SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
        if not _is_postgres():
            with engine.begin() as conn:
                conn.execute(text("UPDATE learningresource SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL"))
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


def _ensure_enrollment_columns() -> None:
    _ensure_columns(
        "enrollment",
        {
            "application_id": "application_id INTEGER",
            "status": "status TEXT DEFAULT 'active'",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE enrollment SET status='active' WHERE status IS NULL OR status='enrolled'"))
    except Exception:
        pass


def _ensure_final_score_confirmation_columns() -> None:
    _ensure_columns(
        "teacherfinalscoreconfirmation",
        {
            "recommendation_summary": "recommendation_summary TEXT DEFAULT ''",
            "updated_at": "updated_at DATETIME",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE teacherfinalscoreconfirmation SET recommendation_summary='' WHERE recommendation_summary IS NULL"))
            conn.execute(text("UPDATE teacherfinalscoreconfirmation SET updated_at=confirmed_at WHERE updated_at IS NULL"))
    except Exception:
        pass


def _normalize_legacy_status_values() -> None:
    # Compatibility migration for legacy uppercase status values.
    # Existing DB may store OPEN/ACTIVE/UNREAD..., while current enums use lowercase.
    statements = [
        # course.enroll_status is TEXT in legacy DBs.
        "UPDATE course SET enroll_status = LOWER(enroll_status::text) "
        "WHERE enroll_status::text IN ('OPEN','FULL','CLOSED','EXPIRED')",
        # enrollment.status may be enum or text depending on historical schema.
        "UPDATE enrollment SET status = 'active' "
        "WHERE status::text IN ('ACTIVE','enrolled')",
        "UPDATE enrollment SET status = 'cancelled' "
        "WHERE status::text IN ('CANCELLED')",
        # coursenotification.status may be enum or text depending on historical schema.
        "UPDATE coursenotification SET status = 'unread' "
        "WHERE status::text IN ('UNREAD')",
        "UPDATE coursenotification SET status = 'read' "
        "WHERE status::text IN ('READ')",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            # Best-effort compatibility fix.
            pass


def get_session():
    with Session(engine) as session:
        yield session
