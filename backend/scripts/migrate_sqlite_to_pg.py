from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy import text

# Allow running from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings  # noqa: E402
from app.db.models import (  # noqa: E402
    EvalConfig,
    ExpressionEvent,
    KnowledgeEdge,
    KnowledgePoint,
    KpQuestionAssignment,
    LearningResource,
    Mastery,
    Note,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    QuizItem,
    User,
    VideoProgress,
)


TABLES_IN_ORDER = [
    User,
    KnowledgePoint,
    KnowledgeEdge,
    LearningResource,
    Quiz,
    QuizItem,
    Question,
    KpQuestionAssignment,
    QuizAttempt,
    PracticeAttempt,
    ExpressionEvent,
    Mastery,
    Note,
    VideoProgress,
    EvalConfig,
]


def _resolve_sqlite_path(raw: str) -> Path:
    base = Path(__file__).resolve().parents[1]
    p = Path(raw)
    return (p if p.is_absolute() else (base / p)).resolve()


def _reset_sequences(engine, table_names: list[str]) -> None:
    with engine.begin() as conn:
        for name in table_names:
            sql = (
                "SELECT setval(pg_get_serial_sequence(:table, 'id'), "
                "COALESCE((SELECT MAX(id) FROM " + name + "), 1), true)"
            )
            conn.execute(text(sql), {"table": name})


def _copy_table(src: Session, dst: Session, model) -> int:
    rows = src.exec(select(model)).all()
    for row in rows:
        data = row.model_dump()
        dst.add(model(**data))
    dst.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL.")
    parser.add_argument("--sqlite", default="app.db", help="Path to sqlite db file (relative to backend/).")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL SQLAlchemy URL.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables in target DB before migrating.")
    args = parser.parse_args()

    sqlite_path = _resolve_sqlite_path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite db not found: {sqlite_path}")

    pg_url = args.pg_url or settings.database_url
    if not pg_url.startswith("postgresql"):
        raise SystemExit(f"Target DATABASE_URL must be PostgreSQL, got: {pg_url}")

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    pg_engine = create_engine(pg_url)

    if args.reset:
        SQLModel.metadata.drop_all(pg_engine)

    SQLModel.metadata.create_all(pg_engine)

    table_names = [m.__tablename__ for m in TABLES_IN_ORDER]
    with Session(sqlite_engine) as src, Session(pg_engine) as dst:
        total = 0
        for model in TABLES_IN_ORDER:
            count = _copy_table(src, dst, model)
            total += count
            print(f"Migrated {model.__tablename__}: {count}")

    _reset_sequences(pg_engine, table_names)
    print(f"Migration complete. Total rows: {total}")


if __name__ == "__main__":
    main()
