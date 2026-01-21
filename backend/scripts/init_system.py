from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel

# Allow running this script directly from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.api.routers.admin import seed_full_system  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402


def _resolve_sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw = database_url.removeprefix("sqlite:///")
    base = Path(__file__).resolve().parents[1]  # backend/
    p = Path(raw)
    return (p if p.is_absolute() else (base / p)).resolve()


def _drop_all() -> None:
    try:
        SQLModel.metadata.drop_all(engine)
        print("Dropped all tables.")
    except Exception as exc:  # pragma: no cover - guardrail
        print(f"Drop all failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize (and optionally seed) the database.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables (or delete sqlite file) before init.")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding demo data.")
    args = parser.parse_args()

    db_path = _resolve_sqlite_path(settings.database_url)
    if args.reset:
        if db_path and db_path.exists():
            os.remove(db_path)
            print(f"Deleted sqlite db: {db_path}")
        elif db_path is None:
            _drop_all()
    else:
        if db_path is None:
            print("Non-sqlite database configured; skipping file deletion.")

    init_db()
    print("Initialized database tables.")

    if args.no_seed:
        print("Skip seeding as requested.")
        return

    with Session(engine) as session:
        res = seed_full_system(session=session, _admin=None)  # type: ignore[arg-type]
        print(f"Seeded: {res}")


if __name__ == "__main__":
    main()
