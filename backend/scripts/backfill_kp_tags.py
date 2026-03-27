from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.session import engine  # noqa: E402
from app.services.kp_tagging import auto_tag_knowledge_points  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill knowledge/ability/literacy tags for knowledge points.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--grade", default="通用")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    with Session(engine) as session:
        res = auto_tag_knowledge_points(session, subject=args.subject, grade=args.grade, overwrite=bool(args.overwrite))
        print(res)


if __name__ == "__main__":
    main()

