from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db import models  # noqa: F401,E402 - import registers SQLModel metadata
from app.db.session import engine, init_db  # noqa: E402


def purge() -> None:
    init_db()
    preparer = engine.dialect.identifier_preparer
    table_names = [table.name for table in SQLModel.metadata.sorted_tables]

    with engine.begin() as conn:
        if engine.dialect.name.startswith("mysql"):
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))

        for table_name in table_names:
            quoted = preparer.quote(table_name)
            if table_name == "user":
                conn.execute(text(f"DELETE FROM {quoted} WHERE role <> :admin_role"), {"admin_role": "admin"})
            else:
                conn.execute(text(f"DELETE FROM {quoted}"))

        if engine.dialect.name.startswith("mysql"):
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    print("purged all non-admin data; only admin users remain")


if __name__ == "__main__":
    purge()
