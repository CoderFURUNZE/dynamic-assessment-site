from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.models import (  # noqa: E402
    Course,
    CourseCompletionRecord,
    CourseEnrollStatus,
    CourseLifecycleStatus,
    Enrollment,
    EnrollmentStatus,
    KpQuestionAssignment,
    KnowledgeEdge,
    KnowledgePoint,
    Mastery,
    Question,
    RelationType,
    User,
    UserRole,
)
from app.db.session import engine, init_db  # noqa: E402


SUBJECT = "高等数学"
HIDDEN_SUBJECT = "高等数学-答辩隐藏"
GRADE = "通用"
COURSE_CODE = "HM"
NOW = datetime(2026, 4, 25, 12, 0, 0)

KPS = [
    ("HM-DEMO-01", "函数基础", "第一章 函数与极限", 0.25, False, 130, 90),
    ("HM-DEMO-02", "极限直观", "第一章 函数与极限", 0.35, False, 330, 170),
    ("HM-DEMO-03", "极限运算", "第一章 函数与极限", 0.45, False, 560, 110),
    ("HM-DEMO-04", "连续性判断", "第一章 函数与极限", 0.50, False, 470, 290),
    ("HM-DEMO-A1", "导数概念", "第二章 导数与微分", 0.58, False, 220, 330),
    ("HM-DEMO-A2", "导数应用", "第二章 导数与微分", 0.68, True, 150, 490),
    ("HM-DEMO-B1", "积分概念", "第三章 不定积分", 0.60, False, 390, 550),
    ("HM-DEMO-B2", "积分应用", "第三章 不定积分", 0.72, True, 610, 470),
    ("HM-DEMO-C1", "综合建模", "课程挑战", 0.80, True, 520, 650),
]

EDGES = [
    ("HM-DEMO-01", "HM-DEMO-02"),
    ("HM-DEMO-02", "HM-DEMO-03"),
    ("HM-DEMO-03", "HM-DEMO-04"),
    ("HM-DEMO-04", "HM-DEMO-A1"),
    ("HM-DEMO-A1", "HM-DEMO-A2"),
    ("HM-DEMO-04", "HM-DEMO-B1"),
    ("HM-DEMO-B1", "HM-DEMO-B2"),
    ("HM-DEMO-A2", "HM-DEMO-C1"),
    ("HM-DEMO-B2", "HM-DEMO-C1"),
]

STUDENT_MASTERY = {
    "student_001": {"HM-DEMO-01": 0.85},
    "student_002": {"HM-DEMO-01": 0.88, "HM-DEMO-02": 0.82},
    "student_003": {"HM-DEMO-01": 0.9, "HM-DEMO-02": 0.86, "HM-DEMO-03": 0.84, "HM-DEMO-04": 0.8, "HM-DEMO-A1": 0.25, "HM-DEMO-B1": 0.76},
    "student_004": {"HM-DEMO-01": 0.9, "HM-DEMO-02": 0.86, "HM-DEMO-03": 0.84, "HM-DEMO-04": 0.8, "HM-DEMO-A1": 0.78, "HM-DEMO-B1": 0.22},
}


def _ensure_course(session: Session) -> Course:
    course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
    if course is None:
        course = Course(code=COURSE_CODE, title=SUBJECT)
    course.title = SUBJECT
    course.description = "个性化学习路线演示课程：同一张老师图谱，学生按掌握情况逐关解锁。"
    course.active = True
    course.lifecycle_status = CourseLifecycleStatus.active
    course.enroll_status = CourseEnrollStatus.open
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _ensure_kp(session: Session, row: tuple[str, str, str, float, bool, int, int]) -> KnowledgePoint:
    code, title, chapter, difficulty, is_terminal, x, y = row
    kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if kp is None:
        kp = KnowledgePoint(subject=SUBJECT, grade=GRADE, code=code, title=title)
    kp.subject = SUBJECT
    kp.grade = GRADE
    kp.title = title
    kp.chapter = chapter
    kp.description = f"{title}学习关卡"
    kp.knowledge_tag = title
    kp.ability_tag = ""
    kp.literacy_tag = ""
    kp.importance = 0.65 if is_terminal else 0.55
    kp.difficulty = difficulty
    kp.pos_x = float(x)
    kp.pos_y = float(y)
    kp.practice_total = 3
    kp.is_terminal = is_terminal
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


def _ensure_question(session: Session, kp: KnowledgePoint, order: int) -> None:
    prompt = f"{kp.title} 的核心判断题：完成本关后才能解锁后续路线。"
    question = session.exec(select(Question).where(Question.kp_id == kp.id, Question.prompt == prompt)).first()
    if question is None:
        question = Question(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), type="mcq", prompt=prompt)
    question.options_json = json.dumps(["正确", "错误"], ensure_ascii=False)
    question.answer = "正确"
    question.explanation = f"本题用于演示 {kp.title} 的基础掌握情况。"
    question.difficulty = kp.difficulty
    question.source = "simple_learning_path_demo"
    question.tags = "learning_path_demo"
    question.version = "simple-path-v1"
    question.cognitive_level = "understand"
    session.add(question)
    session.commit()
    session.refresh(question)
    assignment = session.exec(
        select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == int(kp.id), KpQuestionAssignment.question_id == int(question.id))
    ).first()
    if assignment is None:
        session.add(KpQuestionAssignment(kp_id=int(kp.id), question_id=int(question.id), order=order))


def seed() -> None:
    init_db()
    with Session(engine) as session:
        course = _ensure_course(session)
        demo_codes = {row[0] for row in KPS}
        old_kps = session.exec(
            select(KnowledgePoint).where(KnowledgePoint.subject == SUBJECT, ~KnowledgePoint.code.in_(demo_codes))
        ).all()
        for kp in old_kps:
            kp.subject = HIDDEN_SUBJECT
            kp.is_terminal = False
            session.add(kp)
        session.exec(delete(KnowledgeEdge).where(KnowledgeEdge.subject == SUBJECT))
        session.commit()

        kp_map = {row[0]: _ensure_kp(session, row) for row in KPS}
        for index, kp in enumerate(kp_map.values(), start=1):
            _ensure_question(session, kp, index)

        for prereq_code, next_code in EDGES:
            prereq = kp_map[prereq_code]
            nxt = kp_map[next_code]
            edge = session.exec(
                select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == int(prereq.id), KnowledgeEdge.next_id == int(nxt.id))
            ).first()
            if edge is None:
                edge = KnowledgeEdge(subject=SUBJECT, grade=GRADE, prereq_id=int(prereq.id), next_id=int(nxt.id))
            edge.subject = SUBJECT
            edge.grade = GRADE
            edge.relation_type = RelationType.prerequisite
            session.add(edge)

        students = session.exec(select(User).where(User.role == UserRole.student).order_by(User.id).limit(4)).all()
        for student in students:
            enrollment = session.exec(
                select(Enrollment).where(Enrollment.student_id == int(student.id), Enrollment.course_id == int(course.id))
            ).first()
            if enrollment is None:
                session.add(Enrollment(student_id=int(student.id), course_id=int(course.id), status=EnrollmentStatus.active))

        session.exec(delete(CourseCompletionRecord).where(CourseCompletionRecord.course_id == int(course.id)))
        demo_kp_ids = [int(kp.id) for kp in kp_map.values() if kp.id is not None]
        student_ids = [int(student.id) for student in students if student.id is not None]
        if demo_kp_ids and student_ids:
            session.exec(delete(Mastery).where(Mastery.user_id.in_(student_ids), Mastery.kp_id.in_(demo_kp_ids)))
        session.commit()

        for student in students:
            profile = STUDENT_MASTERY.get(student.username, {})
            for code, value in profile.items():
                kp = kp_map[code]
                status = "mastered" if value >= 0.7 else "learning"
                session.add(
                    Mastery(
                        user_id=int(student.id),
                        kp_id=int(kp.id),
                        value=value,
                        direct_value=value,
                        status=status,
                        reason_summary="演示数据：不同学生掌握度不同，因此下一关推荐不同。",
                        updated_at=NOW,
                    )
                )
        session.commit()
        print(f"seeded simple learning path: course={SUBJECT}, kps={len(kp_map)}, terminals=3, students={len(students)}")


if __name__ == "__main__":
    seed()
