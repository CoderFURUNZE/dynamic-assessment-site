from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import hash_password
from app.db.models import (
    Course,
    CourseCompletionRecord,
    CourseStage,
    Enrollment,
    EnrollmentStatus,
    KnowledgeEdge,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    Note,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    RelationType,
    ResourceType,
    StageEvaluationSnapshot,
    StageImportBatch,
    StageImportRecord,
    StageMetricType,
    StageTeacherFeedback,
    TeacherFinalScoreConfirmation,
    User,
    UserRole,
    VideoProgress,
)
from app.db.session import engine
from app.services.learner_profile import (
    recalculate_stage_snapshots_for_stage,
    sync_profile_snapshot_from_stage,
)


SUBJECT = "计算机网络"
GRADE = "通用"
COURSE_CODE = "CS-NETWORK-001"
USERNAME = "student4"
PASSWORD = "student123"
FULL_NAME = "学生4"
STUDENT_NO = "2026004"
CLASS_NAME = "计算机网络演示班"
SEED_USER = "seed_student4_full_path"


def dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def topological_path(kps: list[KnowledgePoint], edges: list[KnowledgeEdge]) -> list[KnowledgePoint]:
    kp_by_id = {int(kp.id): kp for kp in kps if kp.id is not None}
    indegree = {kp_id: 0 for kp_id in kp_by_id}
    children: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        if edge.relation_type != RelationType.prerequisite:
            continue
        prereq_id = int(edge.prereq_id)
        next_id = int(edge.next_id)
        if prereq_id not in kp_by_id or next_id not in kp_by_id:
            continue
        children[prereq_id].append(next_id)
        indegree[next_id] += 1

    queue = deque(sorted(kp_id for kp_id, value in indegree.items() if value == 0))
    ordered: list[int] = []
    while queue:
        current = queue.popleft()
        ordered.append(current)
        for next_id in sorted(children[current]):
            indegree[next_id] -= 1
            if indegree[next_id] == 0:
                queue.append(next_id)

    missing = [kp_id for kp_id in sorted(kp_by_id) if kp_id not in ordered]
    return [kp_by_id[kp_id] for kp_id in ordered + missing]


def stage_for_index(stages: list[CourseStage], index: int, total: int) -> CourseStage:
    if len(stages) <= 1:
        return stages[0]
    bucket = min(len(stages) - 1, int(index * len(stages) / max(1, total)))
    return stages[bucket]


def staged_time(stage: CourseStage, offset: int, slot: int = 0) -> datetime:
    base = stage.starts_at or datetime(2026, 2, 11, 9, 0, 0)
    return base + timedelta(days=offset % 10, hours=8 + (offset % 4) * 2, minutes=slot * 7)


def clear_student_course_data(session: Session, *, user_id: int, course_id: int, kp_ids: list[int], stage_ids: list[int]) -> None:
    scoped_deletes = [
        delete(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id.in_(kp_ids)),
        delete(PracticeAttempt).where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id.in_(kp_ids)),
        delete(QuizAttempt).where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id.in_(kp_ids)),
        delete(VideoProgress).where(VideoProgress.user_id == user_id, VideoProgress.kp_id.in_(kp_ids)),
        delete(Note).where(Note.user_id == user_id, Note.kp_id.in_(kp_ids)),
        delete(LearningBehaviorEvent).where(
            LearningBehaviorEvent.user_id == user_id,
            (LearningBehaviorEvent.course_id == course_id) | (LearningBehaviorEvent.kp_id.in_(kp_ids)),
        ),
        delete(StageImportRecord).where(StageImportRecord.user_id == user_id, StageImportRecord.course_id == course_id),
        delete(StageEvaluationSnapshot).where(
            StageEvaluationSnapshot.user_id == user_id,
            StageEvaluationSnapshot.course_id == course_id,
        ),
        delete(StageTeacherFeedback).where(StageTeacherFeedback.user_id == user_id, StageTeacherFeedback.course_id == course_id),
        delete(TeacherFinalScoreConfirmation).where(
            TeacherFinalScoreConfirmation.user_id == user_id,
            TeacherFinalScoreConfirmation.course_id == course_id,
        ),
        delete(CourseCompletionRecord).where(
            CourseCompletionRecord.student_id == user_id,
            CourseCompletionRecord.course_id == course_id,
        ),
    ]
    for stmt in scoped_deletes:
        session.exec(stmt)
    if stage_ids:
        session.exec(
            delete(StageImportBatch).where(
                StageImportBatch.course_id == course_id,
                StageImportBatch.stage_id.in_(stage_ids),
                StageImportBatch.uploaded_by == SEED_USER,
            )
        )
    session.commit()


def upsert_student(session: Session) -> User:
    user = session.exec(select(User).where(User.username == USERNAME)).first()
    if user is None:
        user = User(
            username=USERNAME,
            password_hash=hash_password(PASSWORD),
            role=UserRole.student,
            full_name=FULL_NAME,
            student_no=STUDENT_NO,
            class_name=CLASS_NAME,
            active=True,
        )
    else:
        user.password_hash = hash_password(PASSWORD)
        user.role = UserRole.student
        user.full_name = FULL_NAME
        user.student_no = STUDENT_NO
        user.class_name = CLASS_NAME
        user.active = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def upsert_enrollment(session: Session, *, user_id: int, course_id: int) -> None:
    row = session.exec(
        select(Enrollment).where(Enrollment.student_id == user_id, Enrollment.course_id == course_id)
    ).first()
    if row is None:
        row = Enrollment(student_id=user_id, course_id=course_id, status=EnrollmentStatus.active)
    row.status = EnrollmentStatus.active
    row.enrolled_at = datetime.utcnow()
    session.add(row)
    session.commit()


def seed_path_learning(
    session: Session,
    *,
    user: User,
    course: Course,
    kps: list[KnowledgePoint],
    path: list[KnowledgePoint],
    stages: list[CourseStage],
) -> dict[int, list[int]]:
    questions_by_kp: dict[int, list[Question]] = defaultdict(list)
    for question in session.exec(select(Question).where(Question.kp_id.in_([int(kp.id) for kp in kps]))).all():
        questions_by_kp[int(question.kp_id)].append(question)

    quizzes_by_kp: dict[int, list[Quiz]] = defaultdict(list)
    for quiz in session.exec(select(Quiz).where(Quiz.kp_id.in_([int(kp.id) for kp in kps]))).all():
        quizzes_by_kp[int(quiz.kp_id)].append(quiz)

    resources_by_kp: dict[int, list[LearningResource]] = defaultdict(list)
    for resource in session.exec(
        select(LearningResource).where(
            LearningResource.kp_id.in_([int(kp.id) for kp in kps]),
            LearningResource.type == ResourceType.video,
        )
    ).all():
        resources_by_kp[int(resource.kp_id)].append(resource)

    stage_kp_map: dict[int, list[int]] = defaultdict(list)
    total = len(path)
    for index, kp in enumerate(path):
        kp_id = int(kp.id)
        stage = stage_for_index(stages, index, total)
        stage_kp_map[int(stage.id)].append(kp_id)
        event_time = staged_time(stage, index, 0)
        mastery_value = min(0.99, 0.90 + index * 0.0025)

        session.add(
            Mastery(
                user_id=int(user.id),
                kp_id=kp_id,
                value=mastery_value,
                direct_value=mastery_value,
                status="mastered",
                reason_summary=f"{FULL_NAME} 已按前置路径完成 {kp.code} {kp.title} 的资源、练习和测验。",
                updated_at=event_time + timedelta(hours=2),
            )
        )

        for resource_index, resource in enumerate(resources_by_kp.get(kp_id, [])[:2]):
            duration = 1260 + (index % 5) * 90 + resource_index * 60
            session.add(
                VideoProgress(
                    user_id=int(user.id),
                    kp_id=kp_id,
                    resource_id=int(resource.id),
                    watched_seconds=float(duration),
                    duration_seconds=float(duration),
                    last_position_seconds=float(duration),
                    completed=True,
                    updated_at=event_time + timedelta(minutes=18 + resource_index * 15),
                )
            )

        for question_index, question in enumerate(questions_by_kp.get(kp_id, [])[:3]):
            session.add(
                PracticeAttempt(
                    user_id=int(user.id),
                    question_id=int(question.id),
                    kp_id=kp_id,
                    correct=True,
                    self_report="sure",
                    duration_ms=52_000 + question_index * 8_000 + (index % 4) * 5_000,
                    created_at=event_time + timedelta(minutes=45 + question_index * 9),
                )
            )

        for quiz_index, quiz in enumerate(quizzes_by_kp.get(kp_id, [])[:2]):
            score = min(0.99, 0.90 + ((index + quiz_index) % 8) * 0.01)
            session.add(
                QuizAttempt(
                    user_id=int(user.id),
                    quiz_id=int(quiz.id),
                    kp_id=kp_id,
                    score=score,
                    passed=True,
                    duration_ms=210_000 + quiz_index * 30_000,
                    created_at=event_time + timedelta(minutes=80 + quiz_index * 12),
                )
            )

        session.add(
            Note(
                user_id=int(user.id),
                kp_id=kp_id,
                content=f"{kp.title}：已整理核心概念、典型题和与后续节点的衔接关系。",
                created_at=event_time + timedelta(minutes=100),
            )
        )

        events = [
            ("login", {"source": "seed", "stage_order": stage.stage_order}),
            ("graph_view", {"kp_title": kp.title, "path_index": index + 1}),
            ("kp_open", {"kp_code": kp.code, "kp_title": kp.title}),
            ("resource_visit", {"video_count": len(resources_by_kp.get(kp_id, [])), "completed": True}),
            ("video_progress", {"watched_ratio": 1.0, "completed": True}),
            ("practice_submit", {"correct": True, "attempts": min(3, len(questions_by_kp.get(kp_id, [])))}),
            ("quiz_submit", {"passed": True, "score": 0.92}),
            ("note_create", {"summary": "整理学习笔记"}),
            ("mastery_update", {"value": mastery_value, "status": "mastered"}),
        ]
        for event_index, (event_type, payload) in enumerate(events):
            session.add(
                LearningBehaviorEvent(
                    user_id=int(user.id),
                    course_id=int(course.id),
                    kp_id=kp_id,
                    event_type=event_type,
                    value_json=dump(payload),
                    created_at=event_time + timedelta(minutes=event_index * 5),
                )
            )

    session.commit()
    return stage_kp_map


def seed_stage_records(
    session: Session,
    *,
    user: User,
    course: Course,
    stages: list[CourseStage],
    kps_by_stage: dict[int, list[int]],
) -> None:
    metric_specs = [
        (StageMetricType.video, 96.0, 1.0, 24.0, "completed"),
        (StageMetricType.assignment, 93.0, 1.0, 32.0, "submitted"),
        (StageMetricType.quiz, 94.0, 1.0, 18.0, "passed"),
        (StageMetricType.task, 95.0, 1.0, 36.0, "completed"),
        (StageMetricType.participation, 98.0, 1.0, 12.0, "engaged"),
    ]
    for stage in stages:
        stage_id = int(stage.id)
        kp_ids = kps_by_stage.get(stage_id, [])
        for metric_type, score, completion, duration, status in metric_specs:
            batch = StageImportBatch(
                course_id=int(course.id),
                stage_id=stage_id,
                subject=SUBJECT,
                grade=GRADE,
                metric_type=metric_type,
                file_name=f"{USERNAME}_{metric_type.value}_stage_{stage.stage_order}.seed.json",
                uploaded_by=SEED_USER,
                total_rows=len(kp_ids),
                success_rows=len(kp_ids),
                failed_rows=0,
                error_json="[]",
                created_at=staged_time(stage, 0, 0),
            )
            session.add(batch)
            session.commit()
            session.refresh(batch)
            for row_index, kp_id in enumerate(kp_ids):
                session.add(
                    StageImportRecord(
                        batch_id=int(batch.id),
                        course_id=int(course.id),
                        stage_id=stage_id,
                        user_id=int(user.id),
                        kp_id=kp_id,
                        subject=SUBJECT,
                        grade=GRADE,
                        metric_type=metric_type,
                        score_value=score + min(3.0, row_index * 0.15),
                        completion_value=completion,
                        duration_minutes=duration,
                        attendance_value=0.0,
                        submitted_on_time=True,
                        status=status,
                        note=f"{FULL_NAME} 第 {stage.stage_order} 阶段 {metric_type.value} 数据完整。",
                        happened_at=staged_time(stage, row_index, 1),
                        raw_json=dump({"source": SEED_USER, "kp_id": kp_id, "stage_order": stage.stage_order}),
                    )
                )

        attendance_days = 6
        batch = StageImportBatch(
            course_id=int(course.id),
            stage_id=stage_id,
            subject=SUBJECT,
            grade=GRADE,
            metric_type=StageMetricType.attendance,
            file_name=f"{USERNAME}_attendance_stage_{stage.stage_order}.seed.json",
            uploaded_by=SEED_USER,
            total_rows=attendance_days,
            success_rows=attendance_days,
            failed_rows=0,
            error_json="[]",
            created_at=staged_time(stage, 0, 0),
        )
        session.add(batch)
        session.commit()
        session.refresh(batch)
        for day in range(attendance_days):
            session.add(
                StageImportRecord(
                    batch_id=int(batch.id),
                    course_id=int(course.id),
                    stage_id=stage_id,
                    user_id=int(user.id),
                    kp_id=None,
                    subject=SUBJECT,
                    grade=GRADE,
                    metric_type=StageMetricType.attendance,
                    score_value=100.0,
                    completion_value=1.0,
                    duration_minutes=45.0,
                    attendance_value=1.0,
                    submitted_on_time=True,
                    status="present",
                    note=f"{FULL_NAME} 第 {stage.stage_order} 阶段第 {day + 1} 次出勤。",
                    happened_at=staged_time(stage, day, 2),
                    raw_json=dump({"source": SEED_USER, "stage_order": stage.stage_order, "day": day + 1}),
                )
            )
        session.add(
            StageTeacherFeedback(
                user_id=int(user.id),
                course_id=int(course.id),
                stage_id=stage_id,
                subject=SUBJECT,
                grade=GRADE,
                feedback_tag="优秀",
                comment=f"{FULL_NAME} 第 {stage.stage_order} 阶段按知识路径推进，资源、练习、测验和课堂参与记录完整。",
                updated_by=SEED_USER,
                updated_at=datetime.utcnow(),
            )
        )
    session.commit()


def seed_recent_followup(
    session: Session,
    *,
    user: User,
    course: Course,
    path: list[KnowledgePoint],
) -> None:
    now = datetime.utcnow()
    last_nodes = list(reversed(path[-6:]))
    terminal = last_nodes[0]
    terminal_question = session.exec(select(Question).where(Question.kp_id == int(terminal.id)).order_by(Question.id)).first()
    terminal_quiz = session.exec(select(Quiz).where(Quiz.kp_id == int(terminal.id)).order_by(Quiz.id)).first()
    terminal_resource = session.exec(
        select(LearningResource)
        .where(LearningResource.kp_id == int(terminal.id), LearningResource.type == ResourceType.video)
        .order_by(LearningResource.id)
    ).first()

    for day in range(7):
        kp = last_nodes[day % len(last_nodes)]
        event_time = now - timedelta(days=6 - day, hours=2)
        events = [
            ("login", {"source": "recent_followup", "day": day + 1}),
            ("graph_view", {"mode": "review", "target": "课程综合达标"}),
            ("resource_visit", {"mode": "review", "kp_code": kp.code}),
            ("practice_submit", {"mode": "review", "correct": True}),
            ("quiz_submit", {"mode": "review", "passed": True, "score": 0.96}),
            ("reflection_submit", {"summary": "阶段复盘完成"}),
        ]
        for event_index, (event_type, payload) in enumerate(events):
            session.add(
                LearningBehaviorEvent(
                    user_id=int(user.id),
                    course_id=int(course.id),
                    kp_id=int(kp.id),
                    event_type=event_type,
                    value_json=dump(payload),
                    created_at=event_time + timedelta(minutes=event_index * 6),
                )
            )
        if terminal_question is not None:
            session.add(
                PracticeAttempt(
                    user_id=int(user.id),
                    question_id=int(terminal_question.id),
                    kp_id=int(terminal.id),
                    correct=True,
                    self_report="sure",
                    duration_ms=68_000,
                    created_at=event_time + timedelta(minutes=45),
                )
            )
        if terminal_quiz is not None:
            session.add(
                QuizAttempt(
                    user_id=int(user.id),
                    quiz_id=int(terminal_quiz.id),
                    kp_id=int(terminal.id),
                    score=0.97,
                    passed=True,
                    duration_ms=220_000,
                    created_at=event_time + timedelta(minutes=60),
                )
            )

    if terminal_resource is not None:
        progress = session.exec(
            select(VideoProgress).where(
                VideoProgress.user_id == int(user.id),
                VideoProgress.resource_id == int(terminal_resource.id),
            )
        ).first()
        if progress is not None:
            progress.updated_at = now - timedelta(hours=1)
            progress.watched_seconds = max(float(progress.watched_seconds or 0), float(progress.duration_seconds or 0), 1800.0)
            progress.duration_seconds = max(float(progress.duration_seconds or 0), 1800.0)
            progress.last_position_seconds = progress.duration_seconds
            progress.completed = True
            session.add(progress)
    session.commit()


def validate_path(path: list[KnowledgePoint], edges: list[KnowledgeEdge], mastered_ids: set[int]) -> list[str]:
    errors: list[str] = []
    path_order = {int(kp.id): index for index, kp in enumerate(path)}
    for edge in edges:
        if edge.relation_type != RelationType.prerequisite:
            continue
        prereq_id = int(edge.prereq_id)
        next_id = int(edge.next_id)
        if next_id in mastered_ids and prereq_id not in mastered_ids:
            errors.append(f"{next_id} unlocked before prereq {prereq_id}")
        if prereq_id in path_order and next_id in path_order and path_order[prereq_id] > path_order[next_id]:
            errors.append(f"path order invalid: {prereq_id} after {next_id}")
    return errors


def main() -> None:
    with Session(engine) as session:
        course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
        if course is None or course.id is None:
            raise RuntimeError(f"course not found: {COURSE_CODE}")

        stages = session.exec(
            select(CourseStage)
            .where(CourseStage.course_id == int(course.id), CourseStage.subject == SUBJECT, CourseStage.grade == GRADE)
            .order_by(CourseStage.stage_order)
        ).all()
        if not stages:
            raise RuntimeError("course stages not found")

        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)
            .order_by(KnowledgePoint.id)
        ).all()
        kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
        edges = session.exec(
            select(KnowledgeEdge).where(KnowledgeEdge.subject == SUBJECT, KnowledgeEdge.grade == GRADE)
        ).all()
        path = topological_path(list(kps), list(edges))
        terminal = next((kp for kp in path if kp.title == "课程综合达标" or kp.is_terminal), None)
        if terminal is None or int(path[-1].id) != int(terminal.id):
            path = [kp for kp in path if terminal is None or int(kp.id) != int(terminal.id)]
            if terminal is not None:
                path.append(terminal)

        user = upsert_student(session)
        upsert_enrollment(session, user_id=int(user.id), course_id=int(course.id))
        clear_student_course_data(
            session,
            user_id=int(user.id),
            course_id=int(course.id),
            kp_ids=kp_ids,
            stage_ids=[int(stage.id) for stage in stages],
        )

        kps_by_stage = seed_path_learning(session, user=user, course=course, kps=list(kps), path=path, stages=list(stages))
        seed_stage_records(session, user=user, course=course, stages=list(stages), kps_by_stage=kps_by_stage)
        seed_recent_followup(session, user=user, course=course, path=path)

        for stage in stages:
            recalculate_stage_snapshots_for_stage(session, stage_id=int(stage.id), user_ids=[int(user.id)], persist=True)
        snapshot = sync_profile_snapshot_from_stage(session, user_id=int(user.id), subject=SUBJECT, grade=GRADE, persist=True)

        session.add(
            CourseCompletionRecord(
                course_id=int(course.id),
                student_id=int(user.id),
                completed_at=datetime.utcnow(),
                note="已沿完整前置路径完成至终点：课程综合达标。",
            )
        )
        final_score = float(snapshot.dynamic_score) if snapshot is not None else 0.96
        session.add(
            TeacherFinalScoreConfirmation(
                user_id=int(user.id),
                course_id=int(course.id),
                subject=SUBJECT,
                grade=GRADE,
                suggested_score=final_score,
                confirmed_score=max(0.95, final_score),
                confirmed_level="优秀",
                comment="完整完成计算机网络知识图谱路径，终点课程综合达标已掌握。",
                recommendation_summary="可进入综合项目或高阶真题训练，继续保持复盘节奏。",
                confirmed_by=SEED_USER,
                confirmed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        session.commit()

        mastered_ids = {int(row.kp_id) for row in session.exec(select(Mastery).where(Mastery.user_id == int(user.id))).all() if row.value >= 0.85}
        errors = validate_path(path, list(edges), mastered_ids)
        if errors:
            raise RuntimeError("; ".join(errors[:5]))

        counts = {
            "user_id": int(user.id),
            "path_nodes": len(path),
            "terminal": terminal.title if terminal else "",
            "mastery": len(mastered_ids),
            "video_progress": len(session.exec(select(VideoProgress).where(VideoProgress.user_id == int(user.id))).all()),
            "practice_attempts": len(session.exec(select(PracticeAttempt).where(PracticeAttempt.user_id == int(user.id))).all()),
            "quiz_attempts": len(session.exec(select(QuizAttempt).where(QuizAttempt.user_id == int(user.id))).all()),
            "behavior_events": len(session.exec(select(LearningBehaviorEvent).where(LearningBehaviorEvent.user_id == int(user.id))).all()),
            "stage_snapshots": len(session.exec(select(StageEvaluationSnapshot).where(StageEvaluationSnapshot.user_id == int(user.id))).all()),
            "dynamic_score": round(float(snapshot.dynamic_score), 4) if snapshot is not None else None,
            "course_mastery": round(float(snapshot.course_mastery), 4) if snapshot is not None else None,
        }
        print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
