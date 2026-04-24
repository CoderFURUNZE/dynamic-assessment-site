from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.security import hash_password
from app.db.bootstrap import bootstrap_defaults
from app.db.models import (
    ApplicationStatus,
    Course,
    CourseApplication,
    CourseEnrollStatus,
    CourseLifecycleStatus,
    CourseNotification,
    CoursePortraitIndicatorSelection,
    CourseStage,
    CourseTeacherActivation,
    Enrollment,
    EnrollmentStatus,
    EvalConfig,
    KpQuestionAssignment,
    KnowledgePoint,
    LearnerProfileSnapshot,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    Note,
    PersonaType,
    PortraitIndicator,
    PortraitIndicatorSourceType,
    PracticeAttempt,
    Question,
    QuestionnairePortraitIndicatorInput,
    Quiz,
    QuizAttempt,
    QuizItem,
    RecommendationLog,
    ReviewSchedule,
    StageEvaluationSnapshot,
    StageImportBatch,
    StageImportRecord,
    StageMetricType,
    StageTeacherFeedback,
    TeacherCourseStatus,
    TeacherFinalScoreConfirmation,
    TeacherPortraitIndicatorInput,
    User,
    UserRole,
    VideoProgress,
)
from app.db.session import engine, init_db
from app.services.learner_profile import recalculate_profile_snapshot, recalculate_stage_snapshots_for_stage
from seed_high_math_graph_content import seed as seed_high_math_graph_content


SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM"
TEACHER_USERNAME = "teacher1"
NOW = datetime(2026, 4, 20, 12, 0, 0)
DEMO_STUDENT_USERNAMES = [f"hm_student{i}" for i in range(1, 9)]
DEMO_TAG = "high_math_midterm_demo"


STUDENT_PROFILES = [
    ("hm_student1", "许晨", "2026240101", "智能制造2401", 0.92, PersonaType.smart),
    ("hm_student2", "林雨桐", "2026240102", "智能制造2401", 0.86, PersonaType.diligent),
    ("hm_student3", "周启航", "2026240103", "智能制造2401", 0.78, PersonaType.steady),
    ("hm_student4", "陈思远", "2026240104", "智能制造2402", 0.70, PersonaType.steady),
    ("hm_student5", "王可欣", "2026240105", "智能制造2402", 0.62, PersonaType.struggling),
    ("hm_student6", "赵铭", "2026240106", "智能制造2402", 0.56, PersonaType.struggling),
    ("hm_student7", "刘子昂", "2026240107", "智能制造2403", 0.48, PersonaType.procrastinating),
    ("hm_student8", "马若涵", "2026240108", "智能制造2403", 0.74, PersonaType.diligent),
]


STAGES = [
    (
        1,
        "第1阶段：函数、极限与连续",
        datetime(2026, 2, 24, 8, 0, 0),
        datetime(2026, 3, 15, 18, 0, 0),
        "围绕函数建模、数列极限、函数极限、无穷小比较和连续性完成入门诊断。",
        ("HM-01",),
    ),
    (
        2,
        "第2阶段：导数与微分",
        datetime(2026, 3, 16, 8, 0, 0),
        datetime(2026, 4, 5, 18, 0, 0),
        "围绕导数定义、求导法则、高阶导数、隐函数求导和微分近似完成过程评价。",
        ("HM-02",),
    ),
    (
        3,
        "期中阶段：中值定理与导数应用",
        datetime(2026, 4, 6, 8, 0, 0),
        datetime(2026, 4, 20, 18, 0, 0),
        "围绕中值定理、洛必达法则、泰勒公式、单调凹凸、极值最值和图形分析形成期中画像。",
        ("HM-03",),
    ),
]


def _ensure_user(session: Session, username: str, *, role: UserRole, full_name: str, password: str, student_no: str = "", class_name: str = "") -> User:
    row = session.exec(select(User).where(User.username == username)).first()
    if row is None:
        row = User(username=username, password_hash=hash_password(password), role=role)
    row.password_hash = hash_password(password)
    row.role = role
    row.active = True
    row.full_name = full_name
    row.student_no = student_no
    row.class_name = class_name
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _ensure_course(session: Session, teacher: User) -> Course:
    course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
    if course is None:
        course = Course(code=COURSE_CODE, title=SUBJECT)
    course.title = SUBJECT
    course.description = "面向工科大一学生的高等数学期中演示课程，覆盖函数与极限、导数与微分、导数应用三个阶段。"
    course.teacher_id = int(teacher.id)
    course.active = True
    course.lifecycle_status = CourseLifecycleStatus.active
    course.target_class = "智能制造2401-2403"
    course.max_students = 120
    course.start_at = datetime(2026, 2, 24, 8, 0, 0)
    course.end_at = datetime(2026, 7, 5, 18, 0, 0)
    course.apply_deadline = datetime(2026, 3, 1, 18, 0, 0)
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
    activation.finished_at = None
    activation.updated_at = NOW
    session.add(activation)

    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == SUBJECT, EvalConfig.grade == GRADE)).first()
    if cfg is None:
        cfg = EvalConfig(subject=SUBJECT, grade=GRADE)
    cfg.window_json = json.dumps(
        {
            "practice_attempts": 20,
            "practice_total": 20,
            "evidence_sure_ratio": 0.5,
            "video_complete_ratio": 0.75,
            "difficulty_step": 0.1,
            "max_difficulty_jump": 0.2,
            "stability_strength": 0.35,
        },
        ensure_ascii=False,
    )
    session.add(cfg)
    session.commit()
    return course


def _ensure_stage(session: Session, course: Course, spec: tuple) -> CourseStage:
    order, title, starts_at, ends_at, description, _ = spec
    row = session.exec(select(CourseStage).where(CourseStage.course_id == int(course.id), CourseStage.stage_order == order)).first()
    if row is None:
        row = CourseStage(course_id=int(course.id), subject=SUBJECT, grade=GRADE, stage_order=order, title=title)
    row.subject = SUBJECT
    row.grade = GRADE
    row.title = title
    row.starts_at = starts_at
    row.ends_at = ends_at
    row.description = description
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _clear_seeded_student_data(session: Session, *, course: Course, students: list[User]) -> None:
    user_ids = [int(s.id) for s in students if s.id is not None]
    if not user_ids:
        return
    stage_ids = [int(s.id) for s in session.exec(select(CourseStage).where(CourseStage.course_id == int(course.id))).all() if s.id is not None]
    batch_ids = [int(b.id) for b in session.exec(select(StageImportBatch).where(StageImportBatch.course_id == int(course.id))).all() if b.id is not None]
    hm_kp_ids = [int(kp.id) for kp in session.exec(select(KnowledgePoint).where(KnowledgePoint.code.like("HM-%"))).all() if kp.id is not None]

    if hm_kp_ids:
        question_ids = [int(q.id) for q in session.exec(select(Question).where(Question.kp_id.in_(hm_kp_ids))).all() if q.id is not None]
        quiz_ids = [int(q.id) for q in session.exec(select(Quiz).where(Quiz.kp_id.in_(hm_kp_ids))).all() if q.id is not None]
        session.exec(delete(PracticeAttempt).where(PracticeAttempt.user_id.in_(user_ids), PracticeAttempt.kp_id.in_(hm_kp_ids)))
        session.exec(delete(ReviewSchedule).where(ReviewSchedule.user_id.in_(user_ids), ReviewSchedule.kp_id.in_(hm_kp_ids)))
        session.exec(delete(VideoProgress).where(VideoProgress.user_id.in_(user_ids), VideoProgress.kp_id.in_(hm_kp_ids)))
        session.exec(delete(Note).where(Note.user_id.in_(user_ids), Note.kp_id.in_(hm_kp_ids)))
        session.exec(delete(Mastery).where(Mastery.user_id.in_(user_ids), Mastery.kp_id.in_(hm_kp_ids)))
        if quiz_ids:
            session.exec(delete(QuizAttempt).where(QuizAttempt.user_id.in_(user_ids), QuizAttempt.quiz_id.in_(quiz_ids)))
    session.exec(delete(LearningBehaviorEvent).where(LearningBehaviorEvent.user_id.in_(user_ids), LearningBehaviorEvent.course_id == int(course.id)))
    session.exec(delete(RecommendationLog).where(RecommendationLog.user_id.in_(user_ids), RecommendationLog.subject == SUBJECT, RecommendationLog.grade == GRADE))
    session.exec(delete(CourseNotification).where(CourseNotification.user_id.in_(user_ids), CourseNotification.title.contains("高等数学")))
    session.exec(delete(QuestionnairePortraitIndicatorInput).where(QuestionnairePortraitIndicatorInput.user_id.in_(user_ids), QuestionnairePortraitIndicatorInput.course_id == int(course.id)))
    session.exec(delete(TeacherFinalScoreConfirmation).where(TeacherFinalScoreConfirmation.user_id.in_(user_ids), TeacherFinalScoreConfirmation.course_id == int(course.id)))
    if stage_ids:
        session.exec(delete(StageTeacherFeedback).where(StageTeacherFeedback.user_id.in_(user_ids), StageTeacherFeedback.stage_id.in_(stage_ids)))
        session.exec(delete(TeacherPortraitIndicatorInput).where(TeacherPortraitIndicatorInput.user_id.in_(user_ids), TeacherPortraitIndicatorInput.stage_id.in_(stage_ids)))
        session.exec(delete(StageEvaluationSnapshot).where(StageEvaluationSnapshot.user_id.in_(user_ids), StageEvaluationSnapshot.stage_id.in_(stage_ids)))
        session.exec(delete(StageImportRecord).where(StageImportRecord.user_id.in_(user_ids), StageImportRecord.stage_id.in_(stage_ids)))
    if batch_ids:
        session.exec(delete(StageImportRecord).where(StageImportRecord.batch_id.in_(batch_ids)))
        session.exec(delete(StageImportBatch).where(StageImportBatch.id.in_(batch_ids)))
    session.exec(delete(LearnerProfileSnapshot).where(LearnerProfileSnapshot.user_id.in_(user_ids), LearnerProfileSnapshot.subject == SUBJECT, LearnerProfileSnapshot.grade == GRADE))
    session.commit()


def _enroll_students(session: Session, *, course: Course, teacher: User, students: list[User]) -> None:
    for index, student in enumerate(students):
        app = session.exec(select(CourseApplication).where(CourseApplication.course_id == int(course.id), CourseApplication.student_id == int(student.id))).first()
        if app is None:
            app = CourseApplication(course_id=int(course.id), student_id=int(student.id))
        app.apply_reason = "参加高等数学过程性评价与知识图谱学习演示班。"
        app.status = ApplicationStatus.approved
        app.review_remark = "期中答辩演示数据：报名通过。"
        app.reviewed_by = int(teacher.id)
        app.reviewed_at = NOW - timedelta(days=45 - index)
        app.created_at = NOW - timedelta(days=50 - index)
        app.updated_at = NOW - timedelta(days=45 - index)
        session.add(app)
        session.commit()
        session.refresh(app)

        enrollment = session.exec(select(Enrollment).where(Enrollment.course_id == int(course.id), Enrollment.student_id == int(student.id))).first()
        if enrollment is None:
            enrollment = Enrollment(course_id=int(course.id), student_id=int(student.id))
        enrollment.application_id = int(app.id)
        enrollment.status = EnrollmentStatus.active
        enrollment.enrolled_at = NOW - timedelta(days=44 - index)
        session.add(enrollment)

        session.add(
            CourseNotification(
                user_id=int(student.id),
                title="高等数学课程报名已通过",
                content="你已加入高等数学期中演示课程，可在知识图谱中查看资源、练习、小测和阶段报告。",
                created_at=NOW - timedelta(days=44 - index),
            )
        )
    session.commit()


def _enable_indicators(session: Session, *, course: Course, teacher: User) -> tuple[list[PortraitIndicator], list[PortraitIndicator], list[PortraitIndicator]]:
    indicators = session.exec(select(PortraitIndicator).where(PortraitIndicator.active == True).order_by(PortraitIndicator.sort_order, PortraitIndicator.id)).all()  # noqa: E712
    for indicator in indicators:
        row = session.exec(
            select(CoursePortraitIndicatorSelection).where(
                CoursePortraitIndicatorSelection.course_id == int(course.id),
                CoursePortraitIndicatorSelection.indicator_id == int(indicator.id),
            )
        ).first()
        if row is None:
            row = CoursePortraitIndicatorSelection(
                course_id=int(course.id),
                dimension_id=int(indicator.dimension_id),
                indicator_id=int(indicator.id),
            )
        row.dimension_id = int(indicator.dimension_id)
        row.enabled = True
        row.weight = float(indicator.default_weight or 1.0)
        row.selected_by = teacher.username
        row.updated_at = NOW
        session.add(row)
    session.commit()
    teacher_indicators = [i for i in indicators if i.source_type == PortraitIndicatorSourceType.teacher]
    questionnaire_indicators = [i for i in indicators if i.source_type == PortraitIndicatorSourceType.questionnaire]
    return indicators, teacher_indicators, questionnaire_indicators


def _stage_kps(kps: list[KnowledgePoint], prefixes: tuple[str, ...]) -> list[KnowledgePoint]:
    rows = [kp for kp in kps if any(str(kp.code).startswith(prefix) for prefix in prefixes)]
    return rows or kps[:8]


def _make_batch(session: Session, *, course: Course, stage: CourseStage, metric_type: StageMetricType) -> StageImportBatch:
    batch = StageImportBatch(
        course_id=int(course.id),
        stage_id=int(stage.id),
        subject=SUBJECT,
        grade=GRADE,
        metric_type=metric_type,
        file_name=f"{stage.title}_{metric_type.value}_{DEMO_TAG}.csv",
        uploaded_by=TEACHER_USERNAME,
        total_rows=0,
        success_rows=0,
        failed_rows=0,
        error_json="[]",
        created_at=(stage.ends_at or NOW) - timedelta(hours=3),
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)
    return batch


def _add_stage_records(session: Session, *, course: Course, stages: list[CourseStage], students: list[User], kps: list[KnowledgePoint], profile_by_user: dict[int, dict]) -> None:
    for stage, spec in zip(stages, STAGES):
        stage_kps = _stage_kps(kps, spec[5])
        batches = {
            StageMetricType.video: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.video),
            StageMetricType.assignment: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.assignment),
            StageMetricType.quiz: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.quiz),
            StageMetricType.attendance: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.attendance),
            StageMetricType.task: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.task),
            StageMetricType.participation: _make_batch(session, course=course, stage=stage, metric_type=StageMetricType.participation),
        }
        for student_index, student in enumerate(students):
            profile = profile_by_user[int(student.id)]
            base = float(profile["base"])
            stage_delta = [-0.04, 0.0, 0.035][int(stage.stage_order) - 1]
            score_base = max(0.35, min(0.98, base + stage_delta))
            happened = (stage.ends_at or NOW) - timedelta(days=1, hours=student_index)
            values = {
                StageMetricType.video: (score_base + 0.03, score_base + 0.02, 70 + stage.stage_order * 15 + student_index * 3, False, "completed"),
                StageMetricType.assignment: (score_base - 0.01, 1.0, 45, True, "submitted"),
                StageMetricType.quiz: (score_base - 0.02, 1.0, 30, True, "submitted"),
                StageMetricType.attendance: (min(1.0, score_base + 0.08), min(1.0, score_base + 0.08), 0, False, "present"),
                StageMetricType.task: (score_base - 0.015, score_base, 50, True, "done"),
                StageMetricType.participation: (score_base - 0.03, score_base - 0.02, 0, False, "active"),
            }
            for m_index, (metric_type, (score, completion, duration, on_time, status)) in enumerate(values.items()):
                kp = stage_kps[(student_index + m_index) % len(stage_kps)]
                session.add(
                    StageImportRecord(
                        batch_id=int(batches[metric_type].id),
                        course_id=int(course.id),
                        stage_id=int(stage.id),
                        user_id=int(student.id),
                        kp_id=int(kp.id) if metric_type != StageMetricType.attendance else None,
                        subject=SUBJECT,
                        grade=GRADE,
                        metric_type=metric_type,
                        score_value=round(max(0.0, min(1.0, score)) * 100, 2),
                        completion_value=round(max(0.0, min(1.0, completion)), 4),
                        duration_minutes=float(duration),
                        attendance_value=round(max(0.0, min(1.0, completion)), 4) if metric_type == StageMetricType.attendance else 0.0,
                        submitted_on_time=on_time,
                        status=status,
                        note=f"{student.full_name} {stage.title} {metric_type.value} 演示记录",
                        happened_at=happened,
                        raw_json=json.dumps({"seed": DEMO_TAG, "stage": stage.stage_order, "metric": metric_type.value}, ensure_ascii=False),
                    )
                )
        for batch in batches.values():
            batch.total_rows = len(students)
            batch.success_rows = len(students)
            session.add(batch)
        session.commit()
        recalculate_stage_snapshots_for_stage(session, stage_id=int(stage.id), user_ids=[int(s.id) for s in students], persist=True)


def _add_learning_evidence(session: Session, *, course: Course, students: list[User], kps: list[KnowledgePoint], profile_by_user: dict[int, dict]) -> None:
    kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
    questions = session.exec(select(Question).where(Question.kp_id.in_(kp_ids), Question.version == "high_math-v1").order_by(Question.kp_id, Question.id)).all()
    resources = session.exec(select(LearningResource).where(LearningResource.kp_id.in_(kp_ids)).order_by(LearningResource.kp_id, LearningResource.id)).all()
    quizzes = session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids)).order_by(Quiz.kp_id)).all()
    resource_by_kp: dict[int, LearningResource] = {}
    for resource in resources:
        resource_by_kp.setdefault(int(resource.kp_id), resource)

    for student_index, student in enumerate(students):
        profile = profile_by_user[int(student.id)]
        base = float(profile["base"])
        attempt_count = int(80 + base * 80)
        for q_index, question in enumerate(questions[:attempt_count]):
            correctness_threshold = base - 0.08 + (0.12 if float(question.difficulty or 0.5) < 0.45 else 0.0)
            correct = ((q_index * 17 + student_index * 11) % 100) < int(max(0.25, min(0.95, correctness_threshold)) * 100)
            session.add(
                PracticeAttempt(
                    user_id=int(student.id),
                    question_id=int(question.id),
                    kp_id=int(question.kp_id),
                    correct=correct,
                    self_report="sure" if correct and base >= 0.65 else "unknown" if correct else "guess",
                    duration_ms=int(45000 + (1.0 - base) * 70000 + (q_index % 7) * 6000),
                    created_at=NOW - timedelta(days=25 - min(q_index // 8, 24), hours=q_index % 8),
                )
            )

        for kp_index, kp in enumerate(kps):
            decay = min(0.28, kp_index * 0.006)
            value = max(0.12, min(0.96, base + 0.08 - decay + ((student_index % 3) - 1) * 0.015))
            session.add(
                Mastery(
                    user_id=int(student.id),
                    kp_id=int(kp.id),
                    value=value,
                    direct_value=max(0.0, value - 0.04),
                    status="mastered" if value >= 0.72 else "learning" if value >= 0.35 else "weak",
                    reason_summary=f"{student.full_name} 在“{kp.title}”的掌握度由练习正确率、资源访问、阶段测验和教师评价综合生成。",
                    updated_at=NOW - timedelta(days=max(1, 20 - kp_index % 18)),
                )
            )
            if kp_index < 24:
                resource = resource_by_kp.get(int(kp.id))
                if resource is not None:
                    session.add(
                        LearningBehaviorEvent(
                            user_id=int(student.id),
                            course_id=int(course.id),
                            kp_id=int(kp.id),
                            event_type="resource_visit",
                            value_json=json.dumps({"resource_id": int(resource.id), "seed": DEMO_TAG}, ensure_ascii=False),
                            created_at=NOW - timedelta(days=22 - kp_index % 18, hours=student_index),
                        )
                    )
                session.add(
                    Note(
                        user_id=int(student.id),
                        kp_id=int(kp.id),
                        content=f"课堂笔记：{kp.title} 需要关注定义条件、典型题型和易错变形。",
                        created_at=NOW - timedelta(days=21 - kp_index % 18, hours=student_index),
                    )
                )
        for quiz_index, quiz in enumerate(quizzes[:18]):
            score = max(0.25, min(0.98, base + 0.05 - quiz_index * 0.012 + ((student_index % 2) * 0.02)))
            session.add(
                QuizAttempt(
                    user_id=int(student.id),
                    quiz_id=int(quiz.id),
                    kp_id=int(quiz.kp_id),
                    score=score,
                    passed=score >= 0.8,
                    duration_ms=int(180000 + (1 - base) * 160000 + quiz_index * 3000),
                    created_at=NOW - timedelta(days=18 - min(quiz_index, 17), hours=student_index),
                )
            )
        if questions:
            review_q = questions[min(student_index, len(questions) - 1)]
            session.add(
                ReviewSchedule(
                    user_id=int(student.id),
                    question_id=int(review_q.id),
                    kp_id=int(review_q.kp_id),
                    interval_days=3 if base < 0.65 else 7,
                    due_at=NOW - timedelta(days=1) if base < 0.58 else NOW + timedelta(days=3),
                    last_result="wrong" if base < 0.58 else "correct",
                    created_at=NOW - timedelta(days=12),
                    updated_at=NOW - timedelta(days=2),
                )
            )
        for r_index in range(5):
            source = kps[min(r_index + student_index, len(kps) - 2)]
            target = kps[min(r_index + student_index + 1, len(kps) - 1)]
            session.add(
                RecommendationLog(
                    user_id=int(student.id),
                    subject=SUBJECT,
                    grade=GRADE,
                    source_kp_id=int(source.id),
                    target_kp_id=int(target.id),
                    persona_type=profile["persona"],
                    reason_summary=f"根据 {source.title} 的掌握状态，推荐继续学习 {target.title}。",
                    payload_json=json.dumps({"seed": DEMO_TAG, "rank": r_index + 1}, ensure_ascii=False),
                    created_at=NOW - timedelta(days=10 - r_index, hours=student_index),
                )
            )
    session.commit()


def _add_teacher_and_questionnaire_data(
    session: Session,
    *,
    course: Course,
    stages: list[CourseStage],
    students: list[User],
    teacher: User,
    teacher_indicators: list[PortraitIndicator],
    questionnaire_indicators: list[PortraitIndicator],
    profile_by_user: dict[int, dict],
) -> None:
    for student_index, student in enumerate(students):
        base = float(profile_by_user[int(student.id)]["base"])
        for indicator_index, indicator in enumerate(questionnaire_indicators[:5]):
            session.add(
                QuestionnairePortraitIndicatorInput(
                    user_id=int(student.id),
                    course_id=int(course.id),
                    dimension_id=int(indicator.dimension_id),
                    indicator_id=int(indicator.id),
                    score=max(0.25, min(0.98, base + 0.03 - indicator_index * 0.015)),
                    note="高等数学期中演示问卷数据",
                    updated_at=NOW - timedelta(days=16, hours=student_index),
                )
            )
        for stage in stages:
            session.add(
                StageTeacherFeedback(
                    user_id=int(student.id),
                    course_id=int(course.id),
                    stage_id=int(stage.id),
                    subject=SUBJECT,
                    grade=GRADE,
                    feedback_tag="表现稳定" if base >= 0.7 else "需要跟进" if base < 0.6 else "持续进步",
                    comment=f"{student.full_name} 在{stage.title}中完成了课堂任务和图谱练习，建议继续强化错题复盘与概念表达。",
                    updated_by=teacher.username,
                    updated_at=(stage.ends_at or NOW) - timedelta(hours=2),
                )
            )
            for indicator_index, indicator in enumerate(teacher_indicators[:4]):
                session.add(
                    TeacherPortraitIndicatorInput(
                        user_id=int(student.id),
                        course_id=int(course.id),
                        stage_id=int(stage.id),
                        dimension_id=int(indicator.dimension_id),
                        indicator_id=int(indicator.id),
                        score=max(0.25, min(0.98, base + 0.02 - indicator_index * 0.02 + stage.stage_order * 0.01)),
                        note=f"{stage.title} 高数课堂观察记录",
                        updated_by=teacher.username,
                        updated_at=(stage.ends_at or NOW) - timedelta(hours=1),
                    )
                )
    session.commit()


def _add_final_confirmations(session: Session, *, course: Course, students: list[User], teacher: User) -> None:
    snapshots = {
        int(row.user_id): row
        for row in session.exec(select(LearnerProfileSnapshot).where(LearnerProfileSnapshot.subject == SUBJECT, LearnerProfileSnapshot.grade == GRADE)).all()
    }
    for student in students:
        snapshot = snapshots.get(int(student.id))
        if snapshot is None:
            continue
        confirmed = max(0.0, min(1.0, float(snapshot.dynamic_score) + 0.015))
        row = session.exec(
            select(TeacherFinalScoreConfirmation).where(
                TeacherFinalScoreConfirmation.user_id == int(student.id),
                TeacherFinalScoreConfirmation.course_id == int(course.id),
            )
        ).first()
        if row is None:
            row = TeacherFinalScoreConfirmation(user_id=int(student.id), course_id=int(course.id), subject=SUBJECT, grade=GRADE)
        row.subject = SUBJECT
        row.grade = GRADE
        row.suggested_score = float(snapshot.dynamic_score)
        row.confirmed_score = confirmed
        row.confirmed_level = "优秀" if confirmed >= 0.85 else "良好" if confirmed >= 0.72 else "合格" if confirmed >= 0.6 else "需帮扶"
        row.comment = f"{student.full_name} 的期中评价结合高数图谱掌握度、阶段导入记录、练习/小测表现和教师观察确认。"
        row.recommendation_summary = "后续建议围绕导数应用、综合证明题和错题复盘继续推进个性化推荐。"
        row.confirmed_by = teacher.username
        row.confirmed_at = NOW
        row.updated_at = NOW
        session.add(row)
    session.commit()


def seed() -> None:
    init_db()
    bootstrap_defaults()
    seed_high_math_graph_content()

    with Session(engine) as session:
        teacher = _ensure_user(session, TEACHER_USERNAME, role=UserRole.teacher, full_name="王敏", password="teacher123")
        _ensure_user(session, "admin", role=UserRole.admin, full_name="系统管理员", password="admin123")
        course = _ensure_course(session, teacher)
        students = [
            _ensure_user(
                session,
                username,
                role=UserRole.student,
                full_name=full_name,
                password="student123",
                student_no=student_no,
                class_name=class_name,
            )
            for username, full_name, student_no, class_name, _, _ in STUDENT_PROFILES
        ]
        _clear_seeded_student_data(session, course=course, students=students)
        stages = [_ensure_stage(session, course, spec) for spec in STAGES]
        _enroll_students(session, course=course, teacher=teacher, students=students)
        _, teacher_indicators, questionnaire_indicators = _enable_indicators(session, course=course, teacher=teacher)

        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE, KnowledgePoint.code.like("HM-%"))
            .order_by(KnowledgePoint.code)
        ).all()
        if not kps:
            raise SystemExit("没有可见的高等数学 HM-* 知识点，请先运行 seed_high_math_graph.py。")
        profile_by_user = {
            int(student.id): {"base": base, "persona": persona}
            for student, (_, _, _, _, base, persona) in zip(students, STUDENT_PROFILES)
            if student.id is not None
        }

        _add_stage_records(session, course=course, stages=stages, students=students, kps=kps, profile_by_user=profile_by_user)
        _add_learning_evidence(session, course=course, students=students, kps=kps, profile_by_user=profile_by_user)
        _add_teacher_and_questionnaire_data(
            session,
            course=course,
            stages=stages,
            students=students,
            teacher=teacher,
            teacher_indicators=teacher_indicators,
            questionnaire_indicators=questionnaire_indicators,
            profile_by_user=profile_by_user,
        )
        for stage in stages:
            recalculate_stage_snapshots_for_stage(session, stage_id=int(stage.id), user_ids=[int(s.id) for s in students], persist=True)
        for student in students:
            recalculate_profile_snapshot(
                session,
                user_id=int(student.id),
                subject=SUBJECT,
                grade=GRADE,
                refresh_mastery=False,
                persist=True,
            )
        _add_final_confirmations(session, course=course, students=students, teacher=teacher)

        print("高等数学期中答辩演示数据已就绪。")
        print(f"课程：{COURSE_CODE} / {SUBJECT}")
        print(f"教师账号：{TEACHER_USERNAME} / teacher123")
        print("学生账号：hm_student1 ~ hm_student8 / student123")
        print(f"学生数：{len(students)}，阶段数：{len(stages)}，可见知识点：{len(kps)}")


if __name__ == "__main__":
    seed()
