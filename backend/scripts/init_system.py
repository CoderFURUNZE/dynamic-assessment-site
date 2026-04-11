from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session, SQLModel

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.api.routers.admin import seed_full_system  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402
from scripts.repair_display_text_data import repair_display_text_data  # noqa: E402


def _drop_all() -> None:
    try:
        SQLModel.metadata.drop_all(engine)
        print("Dropped all tables.")
    except Exception as exc:  # pragma: no cover
        print(f"Drop all failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize MySQL database tables and optional demo data.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables before init.")
    parser.add_argument("--no-seed", action="store_true", help="Skip seeding demo data.")
    args = parser.parse_args()

    if args.reset:
        _drop_all()

    init_db()
    print("Initialized database tables.")

    if args.no_seed:
        print("Skip seeding as requested.")
        return

    with Session(engine) as session:
        res = seed_full_system(session=session, _admin=None)  # type: ignore[arg-type]
        print(f"Seeded: {res}")
    print(f"Repaired display text: {repair_display_text_data()}")


if __name__ == "__main__":
    main()
