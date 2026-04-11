from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings


try:
    engine = create_engine(settings.database_url, echo=False)
except ModuleNotFoundError as exc:
    if "pymysql" in str(exc) and settings.database_url.lower().startswith("mysql"):
        raise RuntimeError(
            "MySQL 连接依赖未安装：pymysql。\n"
            "请先在 backend 环境中执行：pip install -r requirements.txt"
        ) from exc
    raise


def init_db() -> None:
    _create_tables_safely()
    _drop_legacy_interview_tables()
    _ensure_user_columns()
    _ensure_kp_practice_total_column()
    _ensure_question_meta_columns()
    _ensure_practice_attempt_columns()
    _ensure_course_columns()
    _ensure_course_teacher_activation_columns()
    _ensure_knowledgepoint_columns()
    _ensure_knowledgeedge_columns()
    _ensure_mastery_columns()
    _ensure_learning_resource_columns()
    _ensure_stage_snapshot_columns()
    _ensure_profile_snapshot_columns()
    _ensure_enrollment_columns()
    _ensure_final_score_confirmation_columns()
    _ensure_evalconfig_graph_layout_column()
    _normalize_legacy_status_values()


def _create_tables_safely() -> None:
    for table in SQLModel.metadata.sorted_tables:
        try:
            table.create(bind=engine, checkfirst=True)
        except Exception:
            pass


def _quoted_table_name(table_name: str) -> str:
    return f"`{table_name}`"


def _text_cast(column_name: str) -> str:
    return f"CAST({column_name} AS CHAR)"


def _drop_legacy_interview_tables() -> None:
    for table_name in ("interviewanswer", "interviewsession"):
        try:
            with engine.begin() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        except Exception:
            pass


def _ensure_columns(table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    try:
        existing = {c["name"] for c in inspector.get_columns(table_name)}
    except Exception:
        return
    missing = {name: ddl for name, ddl in columns.items() if name not in existing}
    if not missing:
        return
    quoted_name = _quoted_table_name(table_name)
    for ddl in missing.values():
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {quoted_name} ADD COLUMN {ddl}"))
        except Exception:
            pass


def _ensure_user_columns() -> None:
    _ensure_columns("user", {"active": "active BOOLEAN DEFAULT 1"})
    try:
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE {_quoted_table_name('user')} SET active=1 WHERE active IS NULL"))
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
        pass


def _ensure_question_meta_columns() -> None:
    inspector = inspect(engine)
    try:
        cols = {c["name"] for c in inspector.get_columns("question")}
    except Exception:
        return
    needed = ["source", "tags", "version", "cognitive_level", "ability_subtags"]
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
            "lifecycle_status": "lifecycle_status TEXT DEFAULT 'draft'",
            "teacher_id": "teacher_id INTEGER",
            "target_class": "target_class TEXT DEFAULT ''",
            "max_students": "max_students INTEGER DEFAULT 200",
            "start_at": "start_at DATETIME",
            "end_at": "end_at DATETIME",
            "archived_at": "archived_at DATETIME",
            "apply_deadline": "apply_deadline DATETIME",
            "enroll_status": "enroll_status TEXT DEFAULT 'open'",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE course SET lifecycle_status='draft' WHERE lifecycle_status IS NULL"))
            conn.execute(text("UPDATE course SET target_class='' WHERE target_class IS NULL"))
        pass
    except Exception:
        pass


def _clear_legacy_course_teacher_assignment() -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE course SET teacher_id=NULL WHERE teacher_id IS NOT NULL"))
    except Exception:
        pass


def _ensure_course_teacher_activation_columns() -> None:
    _ensure_columns(
        "courseteacheractivation",
        {
            "teaching_status": "teaching_status VARCHAR(32) DEFAULT 'not_started'",
            "finished_at": "finished_at DATETIME",
            "updated_at": "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE courseteacheractivation SET teaching_status='teaching' WHERE teaching_status IS NULL OR teaching_status='' OR teaching_status='not_started'"))
            conn.execute(text("UPDATE courseteacheractivation SET updated_at=activated_at WHERE updated_at IS NULL"))
        pass
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
    _ensure_columns("knowledgeedge", {"relation_type": "relation_type TEXT DEFAULT 'prerequisite'"})
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
            "extension_mismatch": "extension_mismatch BOOLEAN DEFAULT 0",
            "source_kind": "source_kind TEXT DEFAULT 'external'",
            "created_at": "created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
    )
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE learningresource SET category='recommend' WHERE category IS NULL AND type IN ('book', 'recommend_book')"))
            conn.execute(text("UPDATE learningresource SET category='learning' WHERE category IS NULL"))
            conn.execute(text("UPDATE learningresource SET preview_status='ready' WHERE preview_status IS NULL"))
            conn.execute(text("UPDATE learningresource SET source_kind='external' WHERE source_kind IS NULL"))
            conn.execute(text("UPDATE learningresource SET updated_at=CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
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
    _ensure_columns("learnerprofilesnapshot", {"portrait_summary_json": "portrait_summary_json TEXT DEFAULT '{}'"})


def _ensure_enrollment_columns() -> None:
    _ensure_columns("enrollment", {"application_id": "application_id INTEGER", "status": "status TEXT DEFAULT 'active'"})
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE enrollment SET status='active' WHERE status IS NULL OR status='enrolled'"))
    except Exception:
        pass


def _ensure_evalconfig_graph_layout_column() -> None:
    _ensure_columns("evalconfig", {"graph_layout_json": "graph_layout_json TEXT DEFAULT ''"})


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
    enroll_status_expr = _text_cast("enroll_status")
    enrollment_status_expr = _text_cast("status")
    notification_status_expr = _text_cast("status")
    statements = [
        f"UPDATE course SET enroll_status = LOWER({enroll_status_expr}) WHERE {enroll_status_expr} IN ('OPEN','FULL','CLOSED','EXPIRED')",
        f"UPDATE enrollment SET status = 'active' WHERE {enrollment_status_expr} IN ('ACTIVE','enrolled')",
        f"UPDATE enrollment SET status = 'cancelled' WHERE {enrollment_status_expr} IN ('CANCELLED')",
        f"UPDATE coursenotification SET status = 'unread' WHERE {notification_status_expr} IN ('UNREAD')",
        f"UPDATE coursenotification SET status = 'read' WHERE {notification_status_expr} IN ('READ')",
    ]
    for stmt in statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            pass


def get_session():
    with Session(engine) as session:
        yield session
