from __future__ import annotations

import sys
from pathlib import Path

from sqlmodel import Session, select
from sqlalchemy import text

# Allow running this script directly from repo root
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.models import (
    EvalConfig,
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    Question,
    Quiz,
)
from app.db.session import engine

GRADE = "\u901a\u7528"

SUBJECTS = {
    "DS": "\u6570\u636e\u7ed3\u6784",
    "CO": "\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406",
    "OS": "\u64cd\u4f5c\u7cfb\u7edf",
    "CN": "\u8ba1\u7b97\u673a\u7f51\u7edc",
}

KP_TITLES = {
    "DS-GEN-001": "\u7ebf\u6027\u8868\u57fa\u7840",
    "DS-GEN-002": "\u6808\u4e0e\u961f\u5217",
    "DS-GEN-003": "\u4e32",
    "DS-GEN-004": "\u6570\u7ec4\u4e0e\u77e9\u9635",
    "DS-GEN-005": "\u6811\u4e0e\u4e8c\u53c9\u6811",
    "DS-GEN-006": "\u56fe\u57fa\u7840",
    "DS-GEN-007": "\u67e5\u627e",
    "DS-GEN-008": "\u6392\u5e8f",
    "DS-GEN-009": "\u54c8\u5e0c\u8868",
    "DS-GEN-010": "\u5806\u4e0e\u4f18\u5148\u961f\u5217",
    "CO-GEN-001": "\u6570\u5236\u4e0e\u7f16\u7801",
    "CO-GEN-002": "\u903b\u8f91\u7535\u8def\u57fa\u7840",
    "CO-GEN-003": "\u6307\u4ee4\u7cfb\u7edf",
    "CO-GEN-004": "CPU\u7ed3\u6784\u4e0e\u63a7\u5236",
    "CO-GEN-005": "\u6d41\u6c34\u7ebf",
    "CO-GEN-006": "\u5b58\u50a8\u5c42\u6b21",
    "CO-GEN-007": "\u8f93\u5165\u8f93\u51fa",
    "CO-GEN-008": "\u603b\u7ebf\u4e0e\u63a5\u53e3",
    "CO-GEN-009": "\u4e2d\u65ad\u4e0e\u5f02\u5e38",
    "CO-GEN-010": "\u6027\u80fd\u4e0e\u5e76\u884c",
    "OS-GEN-001": "\u64cd\u4f5c\u7cfb\u7edf\u6982\u8ff0",
    "OS-GEN-002": "\u8fdb\u7a0b\u4e0e\u7ebf\u7a0b",
    "OS-GEN-003": "CPU\u8c03\u5ea6",
    "OS-GEN-004": "\u540c\u6b65\u4e0e\u4e92\u65a5",
    "OS-GEN-005": "\u6b7b\u9501",
    "OS-GEN-006": "\u5185\u5b58\u7ba1\u7406",
    "OS-GEN-007": "\u865a\u62df\u5185\u5b58",
    "OS-GEN-008": "\u6587\u4ef6\u7cfb\u7edf",
    "OS-GEN-009": "I/O\u4e0e\u8bbe\u5907",
    "OS-GEN-010": "\u5b89\u5168\u4e0e\u4fdd\u62a4",
    "CN-GEN-001": "\u7f51\u7edc\u4f53\u7cfb\u7ed3\u6784",
    "CN-GEN-002": "\u7269\u7406\u5c42",
    "CN-GEN-003": "\u6570\u636e\u94fe\u8def\u5c42",
    "CN-GEN-004": "\u4ecb\u8d28\u8bbf\u95ee\u63a7\u5236",
    "CN-GEN-005": "\u7f51\u7edc\u5c42",
    "CN-GEN-006": "\u8def\u7531\u4e0e\u8f6c\u53d1",
    "CN-GEN-007": "\u4f20\u8f93\u5c42",
    "CN-GEN-008": "\u5e94\u7528\u5c42",
    "CN-GEN-009": "\u7f51\u7edc\u5b89\u5168",
    "CN-GEN-010": "\u65e0\u7ebf\u4e0e\u79fb\u52a8\u7f51\u7edc",
}


def subject_from_code(code: str) -> str | None:
    for prefix, subject in SUBJECTS.items():
        if code.startswith(prefix + "-"):
            return subject
    return None


def main() -> None:
    with Session(engine) as session:
        kps = session.exec(select(KnowledgePoint)).all()
        kp_map: dict[int, KnowledgePoint] = {}
        for kp in kps:
            subject = subject_from_code(kp.code) or kp.subject
            title = KP_TITLES.get(kp.code, kp.title)
            kp.subject = subject
            kp.grade = GRADE
            kp.title = title
            kp.description = f"{title}\uff08\u793a\u4f8b\uff09"
            session.add(kp)
            kp_map[int(kp.id)] = kp
        session.commit()

        for row in session.exec(select(Question)).all():
            kp = kp_map.get(int(row.kp_id))
            if kp:
                row.subject = kp.subject
                row.grade = kp.grade
                session.add(row)
        session.commit()

        for row in session.exec(select(LearningResource)).all():
            kp = kp_map.get(int(row.kp_id))
            if kp:
                row.subject = kp.subject
                row.grade = kp.grade
                session.add(row)
        session.commit()

        for row in session.exec(select(Quiz)).all():
            kp = kp_map.get(int(row.kp_id))
            if kp:
                row.subject = kp.subject
                row.grade = kp.grade
                session.add(row)
        session.commit()

        for row in session.exec(select(KnowledgeEdge)).all():
            kp = kp_map.get(int(row.prereq_id))
            if kp:
                row.subject = kp.subject
                row.grade = kp.grade
                session.add(row)
        session.commit()

        session.exec(text("DELETE FROM evalconfig"))
        session.commit()
        for subject in SUBJECTS.values():
            session.add(EvalConfig(subject=subject, grade=GRADE))
        session.commit()

    print("CS seed normalization done.")


if __name__ == "__main__":
    main()
