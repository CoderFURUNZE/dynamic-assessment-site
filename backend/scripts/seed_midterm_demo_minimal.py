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

from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    Course,
    CourseCompletionRecord,
    CourseEnrollStatus,
    CourseLifecycleStatus,
    CourseTeacherActivation,
    Enrollment,
    EnrollmentStatus,
    KpQuestionAssignment,
    KnowledgeEdge,
    KnowledgePoint,
    Mastery,
    Question,
    RelationType,
    TeacherCourseStatus,
    User,
    UserRole,
)
from app.db.session import engine, init_db  # noqa: E402


SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM-MIDTERM"
PASSWORD = "123456"
NOW = datetime(2026, 4, 25, 16, 0, 0)

TEACHER = ("teacher_demo", "演示教师")
STUDENTS = [
    ("student_demo_1", "学生A-基础薄弱", "2026001", "演示班"),
    ("student_demo_2", "学生B-进度正常", "2026002", "演示班"),
    ("student_demo_3", "学生C-分支提升", "2026003", "演示班"),
]

KPS = [
    ("HM-MID-01", "函数基础", "第一章 函数与极限", 0.25, False, 260, 100),
    ("HM-MID-02", "极限直观", "第一章 函数与极限", 0.35, False, 260, 250),
    ("HM-MID-03", "极限运算", "第一章 函数与极限", 0.45, False, 260, 400),
    ("HM-MID-04", "连续性判断", "第一章 函数与极限", 0.50, False, 260, 550),
    ("HM-MID-A1", "导数概念", "第二章 导数与微分", 0.56, False, 70, 700),
    ("HM-MID-A2", "求导法则", "第二章 导数与微分", 0.62, False, 70, 850),
    ("HM-MID-A3", "导数应用达标", "第二章 导数与微分", 0.70, False, 70, 1020),
    ("HM-MID-B1", "积分概念", "第三章 积分", 0.58, False, 300, 700),
    ("HM-MID-B2", "积分计算", "第三章 积分", 0.66, False, 300, 850),
    ("HM-MID-B3", "积分应用达标", "第三章 积分", 0.74, False, 300, 1020),
    ("HM-MID-C1", "综合建模准备", "期中综合挑战", 0.64, False, 540, 770),
    ("HM-MID-C2", "期中综合达标", "期中综合挑战", 0.80, True, 540, 1020),
]

EDGES = [
    ("HM-MID-01", "HM-MID-02"),
    ("HM-MID-02", "HM-MID-03"),
    ("HM-MID-03", "HM-MID-04"),
    ("HM-MID-04", "HM-MID-A1"),
    ("HM-MID-A1", "HM-MID-A2"),
    ("HM-MID-A2", "HM-MID-A3"),
    ("HM-MID-04", "HM-MID-B1"),
    ("HM-MID-B1", "HM-MID-B2"),
    ("HM-MID-B2", "HM-MID-B3"),
    ("HM-MID-03", "HM-MID-C1"),
    ("HM-MID-03", "HM-MID-C2"),
    ("HM-MID-A2", "HM-MID-C2"),
    ("HM-MID-A3", "HM-MID-C2"),
    ("HM-MID-B2", "HM-MID-C2"),
    ("HM-MID-B3", "HM-MID-C2"),
    ("HM-MID-C1", "HM-MID-C2"),
]

STUDENT_MASTERY = {
    "student_demo_1": {
        "HM-MID-01": 0.20,
    },
    "student_demo_2": {
        "HM-MID-01": 0.88,
        "HM-MID-02": 0.76,
        "HM-MID-03": 0.32,
    },
    "student_demo_3": {
        "HM-MID-01": 0.90,
        "HM-MID-02": 0.84,
        "HM-MID-03": 0.80,
        "HM-MID-04": 0.78,
        "HM-MID-A1": 0.82,
        "HM-MID-A2": 0.76,
        "HM-MID-A3": 0.72,
    },
}


def ensure_user(
    session: Session,
    username: str,
    full_name: str,
    role: UserRole,
    *,
    student_no: str = "",
    class_name: str = "",
) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        user = User(username=username, password_hash=hash_password(PASSWORD), role=role)
    user.password_hash = hash_password(PASSWORD)
    user.role = role
    user.active = True
    user.full_name = full_name
    user.student_no = student_no
    user.class_name = class_name
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def ensure_course(session: Session, teacher: User) -> Course:
    course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
    if course is None:
        course = Course(code=COURSE_CODE, title=SUBJECT)
    course.title = SUBJECT
    course.description = "期中演示课程：展示教师知识图谱、学生逐关解锁和个性化路径推荐。"
    course.active = True
    course.lifecycle_status = CourseLifecycleStatus.active
    course.teacher_id = int(teacher.id)
    course.target_class = "演示班"
    course.max_students = 60
    course.enroll_status = CourseEnrollStatus.open
    session.add(course)
    session.commit()
    session.refresh(course)

    activation = session.exec(
        select(CourseTeacherActivation).where(
            CourseTeacherActivation.course_id == int(course.id),
            CourseTeacherActivation.teacher_id == int(teacher.id),
        )
    ).first()
    if activation is None:
        activation = CourseTeacherActivation(course_id=int(course.id), teacher_id=int(teacher.id))
    activation.teaching_status = TeacherCourseStatus.teaching
    session.add(activation)
    session.commit()
    return course


def ensure_kp(session: Session, row: tuple[str, str, str, float, bool, int, int]) -> KnowledgePoint:
    code, title, chapter, difficulty, is_terminal, x, y = row
    kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if kp is None:
        kp = KnowledgePoint(subject=SUBJECT, grade=GRADE, code=code, title=title)
    kp.subject = SUBJECT
    kp.grade = GRADE
    kp.title = title
    kp.chapter = chapter
    kp.description = f"{title} 的期中演示知识点。"
    kp.knowledge_tag = title
    kp.ability_tag = ""
    kp.literacy_tag = ""
    kp.importance = 0.72 if is_terminal else 0.55
    kp.difficulty = difficulty
    kp.pos_x = float(x)
    kp.pos_y = float(y)
    kp.practice_total = 3
    kp.is_terminal = is_terminal
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


def ensure_question(session: Session, kp: KnowledgePoint, order: int) -> None:
    prompt = f"{kp.title}：本关通过后可继续推进学习路径。"
    question = session.exec(select(Question).where(Question.kp_id == int(kp.id), Question.prompt == prompt)).first()
    if question is None:
        question = Question(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), type="mcq", prompt=prompt)
    question.options_json = json.dumps(["正确", "错误"], ensure_ascii=False)
    question.answer = "正确"
    question.explanation = f"这是 {kp.title} 的演示题，用于产生学习记录和掌握度。"
    question.difficulty = kp.difficulty
    question.source = "midterm_demo"
    question.tags = "midterm_demo"
    question.version = "midterm-demo-v2"
    question.cognitive_level = "understand"
    session.add(question)
    session.commit()
    session.refresh(question)

    assignment = session.exec(
        select(KpQuestionAssignment).where(
            KpQuestionAssignment.kp_id == int(kp.id),
            KpQuestionAssignment.question_id == int(question.id),
        )
    ).first()
    if assignment is None:
        session.add(KpQuestionAssignment(kp_id=int(kp.id), question_id=int(question.id), order=order))
        session.commit()


def ensure_edge(session: Session, kp_map: dict[str, KnowledgePoint], prereq_code: str, next_code: str) -> None:
    prereq = kp_map[prereq_code]
    nxt = kp_map[next_code]
    edge = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.prereq_id == int(prereq.id),
            KnowledgeEdge.next_id == int(nxt.id),
        )
    ).first()
    if edge is None:
        edge = KnowledgeEdge(subject=SUBJECT, grade=GRADE, prereq_id=int(prereq.id), next_id=int(nxt.id))
    edge.subject = SUBJECT
    edge.grade = GRADE
    edge.relation_type = RelationType.prerequisite
    session.add(edge)


def enroll_student(session: Session, course: Course, student: User) -> None:
    enrollment = session.exec(
        select(Enrollment).where(
            Enrollment.course_id == int(course.id),
            Enrollment.student_id == int(student.id),
        )
    ).first()
    if enrollment is None:
        enrollment = Enrollment(course_id=int(course.id), student_id=int(student.id))
    enrollment.status = EnrollmentStatus.active
    session.add(enrollment)


def seed_mastery(session: Session, kp_map: dict[str, KnowledgePoint], student: User) -> None:
    profile = STUDENT_MASTERY.get(student.username, {})
    for code, value in profile.items():
        kp = kp_map[code]
        mastery = session.exec(
            select(Mastery).where(Mastery.user_id == int(student.id), Mastery.kp_id == int(kp.id))
        ).first()
        if mastery is None:
            mastery = Mastery(user_id=int(student.id), kp_id=int(kp.id))
        mastery.value = value
        mastery.direct_value = value
        mastery.status = "mastered" if value >= 0.7 else "learning"
        mastery.reason_summary = "期中演示数据：不同学生掌握度不同，推荐路径不同。"
        mastery.updated_at = NOW
        session.add(mastery)


def reset_existing_midterm_graph(session: Session) -> None:
    hm_mid_kps = session.exec(select(KnowledgePoint).where(KnowledgePoint.code.startswith("HM-MID-"))).all()
    hm_mid_ids = [int(kp.id) for kp in hm_mid_kps if kp.id is not None]
    if not hm_mid_ids:
        return

    session.exec(
        delete(KnowledgeEdge).where(
            KnowledgeEdge.subject == SUBJECT,
            KnowledgeEdge.grade == GRADE,
            KnowledgeEdge.prereq_id.in_(hm_mid_ids),
            KnowledgeEdge.next_id.in_(hm_mid_ids),
        )
    )
    for kp in hm_mid_kps:
        kp.is_terminal = False
        session.add(kp)
    session.commit()


def seed() -> None:
    init_db()
    with Session(engine) as session:
        teacher = ensure_user(session, TEACHER[0], TEACHER[1], UserRole.teacher)
        students = [
            ensure_user(session, username, full_name, UserRole.student, student_no=student_no, class_name=class_name)
            for username, full_name, student_no, class_name in STUDENTS
        ]
        course = ensure_course(session, teacher)
        reset_existing_midterm_graph(session)

        kp_map = {row[0]: ensure_kp(session, row) for row in KPS}
        for index, kp in enumerate(kp_map.values(), start=1):
            ensure_question(session, kp, index)
        for prereq_code, next_code in EDGES:
            ensure_edge(session, kp_map, prereq_code, next_code)

        session.exec(delete(CourseCompletionRecord).where(CourseCompletionRecord.course_id == int(course.id)))
        for student in students:
            enroll_student(session, course, student)
            seed_mastery(session, kp_map, student)

        session.commit()
        print("seeded midterm demo")
        print(f"teacher: {TEACHER[0]} / {PASSWORD}")
        for username, *_ in STUDENTS:
            print(f"student: {username} / {PASSWORD}")
        print(
            f"course: {SUBJECT}, knowledge_points={len(kp_map)}, "
            f"edges={len(EDGES)}, terminals=3, students={len(students)}"
        )


if __name__ == "__main__":
    seed()
