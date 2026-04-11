from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.db.models import (
    Course,
    Enrollment,
    ExpressionEvent,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Note,
    PersonaType,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    RecommendationLog,
    ResourceType,
    User,
    VideoProgress,
)
from app.db.session import engine
from app.services.eval import refresh_subject_mastery


COURSE_SUBJECT_MAP = {
    "OS": "操作系统",
    "DS": "数据结构",
    "CN": "计算机网络",
    "CO": "计算机组成原理",
}

PROFILE_MAP = {
    "student1": {
        "practice_targets": [7, 6, 5, 4],
        "practice_accuracy": 0.86,
        "quiz_targets": [2, 1, 1, 1],
        "quiz_score": 0.84,
        "video_completion": 0.96,
        "recommendations": 3,
        "notes": 2,
        "persona": PersonaType.steady,
        "expression": "focused",
    },
    "student2": {
        "practice_targets": [6, 5, 4, 4],
        "practice_accuracy": 0.78,
        "quiz_targets": [1, 1, 1, 1],
        "quiz_score": 0.76,
        "video_completion": 0.87,
        "recommendations": 3,
        "notes": 2,
        "persona": PersonaType.diligent,
        "expression": "steady",
    },
    "student3": {
        "practice_targets": [5, 4, 4, 3],
        "practice_accuracy": 0.62,
        "quiz_targets": [1, 1, 1, 0],
        "quiz_score": 0.58,
        "video_completion": 0.72,
        "recommendations": 4,
        "notes": 3,
        "persona": PersonaType.struggling,
        "expression": "hesitant",
    },
    "student4": {
        "practice_targets": [6, 5, 5, 4],
        "practice_accuracy": 0.73,
        "quiz_targets": [1, 1, 1, 1],
        "quiz_score": 0.71,
        "video_completion": 0.83,
        "recommendations": 3,
        "notes": 2,
        "persona": PersonaType.diligent,
        "expression": "calm",
    },
    "student5": {
        "practice_targets": [6, 5, 4, 3],
        "practice_accuracy": 0.81,
        "quiz_targets": [2, 1, 1, 1],
        "quiz_score": 0.68,
        "video_completion": 0.79,
        "recommendations": 2,
        "notes": 1,
        "persona": PersonaType.smart,
        "expression": "fast_but_unstable",
    },
}

NOTE_PREFIX = "[demo-activity]"
PAYLOAD_SOURCE = "learning_activity_demo"
WINDOW_DAYS = 30


def _practice_created_at(*, now: datetime, course_id: int, user_id: int, kp_index: int, attempt_index: int) -> datetime:
    day_offset = min(27, kp_index * 5 + attempt_index * 2 + course_id + (user_id % 3))
    return now - timedelta(days=27 - day_offset, hours=(attempt_index * 3 + user_id) % 8)


def _quiz_created_at(*, now: datetime, course_id: int, user_id: int, kp_index: int, quiz_index: int) -> datetime:
    day_offset = min(24, kp_index * 6 + quiz_index * 3 + course_id + user_id)
    return now - timedelta(days=24 - day_offset, hours=(quiz_index + kp_index + user_id) % 6)


def _video_updated_at(*, now: datetime, course_id: int, user_id: int, kp_index: int) -> datetime:
    day_offset = min(22, kp_index * 4 + course_id + user_id)
    return now - timedelta(days=22 - day_offset, hours=(kp_index + user_id) % 5)


def _recent_rows(rows: list, dt_attr: str, since: datetime) -> list:
    return [row for row in rows if getattr(row, dt_attr) >= since]


def _select_subject(course: Course, kp_subjects: list[str]) -> str | None:
    mapped = COURSE_SUBJECT_MAP.get(str(course.code or "").upper())
    if mapped:
        return mapped
    normalized_title = str(course.title or "").strip()
    if normalized_title in kp_subjects:
        return normalized_title
    return None


def main() -> None:
    now = datetime.utcnow()
    since = now - timedelta(days=WINDOW_DAYS)
    summary = defaultdict(int)

    with Session(engine) as session:
        courses = session.exec(select(Course).order_by(Course.id)).all()
        students = session.exec(select(User).where(User.role == "student").order_by(User.id)).all()
        student_map = {int(user.id): user for user in students if user.id is not None}
        subject_rows = session.exec(select(KnowledgePoint.subject).distinct()).all()
        subject_values = [str(row) for row in subject_rows]

        enrollments = session.exec(select(Enrollment).order_by(Enrollment.course_id, Enrollment.student_id)).all()
        enrollments_by_course: dict[int, list[Enrollment]] = defaultdict(list)
        for row in enrollments:
            if row.course_id is not None:
                enrollments_by_course[int(row.course_id)].append(row)

        touched_subjects: set[tuple[int, str, str]] = set()

        for course in courses:
            if course.id is None:
                continue
            course_id = int(course.id)
            subject = _select_subject(course, subject_values)
            if not subject:
                continue

            kps = session.exec(
                select(KnowledgePoint)
                .where(KnowledgePoint.subject == subject)
                .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
            ).all()
            if not kps:
                continue
            grade = str(kps[0].grade or "大学计算机").strip() or "大学计算机"
            tracked_kps = kps[:4]
            kp_ids = [int(kp.id) for kp in tracked_kps if kp.id is not None]
            if not kp_ids:
                continue

            questions_by_kp: dict[int, list[Question]] = defaultdict(list)
            for question in session.exec(select(Question).where(Question.kp_id.in_(kp_ids)).order_by(Question.id)).all():
                questions_by_kp[int(question.kp_id)].append(question)

            quizzes_by_kp: dict[int, list[Quiz]] = defaultdict(list)
            for quiz in session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids)).order_by(Quiz.id)).all():
                quizzes_by_kp[int(quiz.kp_id)].append(quiz)

            videos_by_kp: dict[int, list[LearningResource]] = defaultdict(list)
            resources = session.exec(
                select(LearningResource)
                .where(LearningResource.kp_id.in_(kp_ids), LearningResource.type == ResourceType.video)
                .order_by(LearningResource.id)
            ).all()
            for resource in resources:
                videos_by_kp[int(resource.kp_id)].append(resource)

            for enrollment in enrollments_by_course.get(course_id, []):
                student_id = int(enrollment.student_id)
                student = student_map.get(student_id)
                if student is None or student.id is None:
                    continue
                profile = PROFILE_MAP.get(student.username, PROFILE_MAP["student2"])

                recent_practice = session.exec(
                    select(PracticeAttempt).where(
                        PracticeAttempt.user_id == student_id,
                        PracticeAttempt.kp_id.in_(kp_ids),
                        PracticeAttempt.created_at >= since,
                    )
                ).all()
                recent_quiz = session.exec(
                    select(QuizAttempt).where(
                        QuizAttempt.user_id == student_id,
                        QuizAttempt.kp_id.in_(kp_ids),
                        QuizAttempt.created_at >= since,
                    )
                ).all()
                recent_notes = session.exec(
                    select(Note).where(Note.user_id == student_id, Note.kp_id.in_(kp_ids), Note.created_at >= since)
                ).all()
                recent_behavior = session.exec(
                    select(LearningBehaviorEvent).where(
                        LearningBehaviorEvent.user_id == student_id,
                        LearningBehaviorEvent.course_id == course_id,
                        LearningBehaviorEvent.created_at >= since,
                    )
                ).all()
                recent_reco = session.exec(
                    select(RecommendationLog).where(
                        RecommendationLog.user_id == student_id,
                        RecommendationLog.subject == subject,
                        RecommendationLog.grade == grade,
                        RecommendationLog.created_at >= since,
                    )
                ).all()
                recent_expression = session.exec(
                    select(ExpressionEvent).where(
                        ExpressionEvent.user_id == student_id,
                        ExpressionEvent.kp_id.in_(kp_ids),
                        ExpressionEvent.created_at >= since,
                    )
                ).all()

                practice_count_by_kp = defaultdict(int)
                for row in recent_practice:
                    practice_count_by_kp[int(row.kp_id)] += 1

                quiz_count_by_kp = defaultdict(int)
                for row in recent_quiz:
                    quiz_count_by_kp[int(row.kp_id)] += 1

                note_count_by_kp = defaultdict(int)
                for row in recent_notes:
                    if NOTE_PREFIX in str(row.content or ""):
                        note_count_by_kp[int(row.kp_id)] += 1

                expression_count_by_kp = defaultdict(int)
                for row in recent_expression:
                    expression_count_by_kp[int(row.kp_id)] += 1

                behavior_marker_count = sum(1 for row in recent_behavior if PAYLOAD_SOURCE in str(row.value_json or ""))
                reco_marker_count = sum(1 for row in recent_reco if PAYLOAD_SOURCE in str(row.payload_json or ""))

                for kp_index, kp in enumerate(tracked_kps):
                    if kp.id is None:
                        continue
                    kp_id = int(kp.id)
                    kp_title = str(kp.title or f"知识点{kp_index + 1}")
                    question_rows = questions_by_kp.get(kp_id, [])
                    quiz_rows = quizzes_by_kp.get(kp_id, [])
                    video_rows = videos_by_kp.get(kp_id, [])

                    target_practice = profile["practice_targets"][min(kp_index, len(profile["practice_targets"]) - 1)]
                    existing_practice = practice_count_by_kp.get(kp_id, 0)
                    add_practice = max(0, target_practice - existing_practice)
                    for offset in range(add_practice):
                        if not question_rows:
                            break
                        question = question_rows[(student_id + kp_index * 3 + offset) % len(question_rows)]
                        threshold = int(round(float(profile["practice_accuracy"]) * 10))
                        correct = ((student_id + kp_index + offset * 2) % 10) < threshold
                        created_at = _practice_created_at(
                            now=now,
                            course_id=course_id,
                            user_id=student_id,
                            kp_index=kp_index,
                            attempt_index=offset,
                        )
                        session.add(
                            PracticeAttempt(
                                user_id=student_id,
                                question_id=int(question.id),
                                kp_id=kp_id,
                                correct=correct,
                                self_report="confident" if correct else "uncertain",
                                duration_ms=42000 + kp_index * 7000 + offset * 3000,
                                created_at=created_at,
                            )
                        )
                        session.add(
                            LearningBehaviorEvent(
                                user_id=student_id,
                                course_id=course_id,
                                kp_id=kp_id,
                                event_type="practice_submit",
                                value_json=json.dumps(
                                    {
                                        "source": PAYLOAD_SOURCE,
                                        "question_id": int(question.id),
                                        "correct": correct,
                                        "duration_ms": 42000 + kp_index * 7000 + offset * 3000,
                                    },
                                    ensure_ascii=False,
                                ),
                                created_at=created_at + timedelta(minutes=1),
                            )
                        )
                        summary["practice_attempts"] += 1
                        summary["behavior_events"] += 1

                    target_quiz = profile["quiz_targets"][min(kp_index, len(profile["quiz_targets"]) - 1)]
                    existing_quiz = quiz_count_by_kp.get(kp_id, 0)
                    add_quiz = max(0, target_quiz - existing_quiz)
                    for offset in range(add_quiz):
                        if not quiz_rows:
                            break
                        quiz = quiz_rows[(student_id + offset) % len(quiz_rows)]
                        raw_score = float(profile["quiz_score"]) - 0.06 * kp_index + 0.03 * offset
                        score = max(0.35, min(0.95, raw_score))
                        created_at = _quiz_created_at(
                            now=now,
                            course_id=course_id,
                            user_id=student_id,
                            kp_index=kp_index,
                            quiz_index=offset,
                        )
                        session.add(
                            QuizAttempt(
                                user_id=student_id,
                                quiz_id=int(quiz.id),
                                kp_id=kp_id,
                                score=score,
                                passed=score >= float(quiz.pass_accuracy or 0.8),
                                duration_ms=520000 + kp_index * 40000 + offset * 30000,
                                created_at=created_at,
                            )
                        )
                        session.add(
                            LearningBehaviorEvent(
                                user_id=student_id,
                                course_id=course_id,
                                kp_id=kp_id,
                                event_type="quiz_submit",
                                value_json=json.dumps(
                                    {
                                        "source": PAYLOAD_SOURCE,
                                        "quiz_id": int(quiz.id),
                                        "score": round(score, 2),
                                    },
                                    ensure_ascii=False,
                                ),
                                created_at=created_at + timedelta(minutes=2),
                            )
                        )
                        summary["quiz_attempts"] += 1
                        summary["behavior_events"] += 1

                    if video_rows:
                        for resource in video_rows[:1]:
                            updated_at = _video_updated_at(
                                now=now,
                                course_id=course_id,
                                user_id=student_id,
                                kp_index=kp_index,
                            )
                            completion = max(0.52, min(0.98, float(profile["video_completion"]) - 0.05 * kp_index))
                            duration = 720.0 + kp_index * 180.0
                            watched = round(duration * completion, 1)
                            progress = session.exec(
                                select(VideoProgress).where(
                                    VideoProgress.user_id == student_id,
                                    VideoProgress.resource_id == int(resource.id),
                                )
                            ).first()
                            if progress is None:
                                progress = VideoProgress(
                                    user_id=student_id,
                                    kp_id=kp_id,
                                    resource_id=int(resource.id),
                                    watched_seconds=watched,
                                    duration_seconds=duration,
                                    last_position_seconds=watched,
                                    completed=completion >= 0.9,
                                    updated_at=updated_at,
                                )
                                session.add(progress)
                                summary["video_progress_rows"] += 1
                            else:
                                progress.kp_id = kp_id
                                progress.watched_seconds = max(float(progress.watched_seconds or 0.0), watched)
                                progress.duration_seconds = max(float(progress.duration_seconds or 0.0), duration)
                                progress.last_position_seconds = max(float(progress.last_position_seconds or 0.0), watched)
                                progress.completed = bool(progress.completed or completion >= 0.9)
                                progress.updated_at = max(progress.updated_at, updated_at)
                                session.add(progress)
                            session.add(
                                LearningBehaviorEvent(
                                    user_id=student_id,
                                    course_id=course_id,
                                    kp_id=kp_id,
                                    event_type="video_progress",
                                    value_json=json.dumps(
                                        {
                                            "source": PAYLOAD_SOURCE,
                                            "resource_id": int(resource.id),
                                            "completion": round(completion, 2),
                                        },
                                        ensure_ascii=False,
                                    ),
                                    created_at=updated_at,
                                )
                            )
                            session.add(
                                LearningBehaviorEvent(
                                    user_id=student_id,
                                    course_id=course_id,
                                    kp_id=kp_id,
                                    event_type="resource_visit",
                                    value_json=json.dumps(
                                        {
                                            "source": PAYLOAD_SOURCE,
                                            "resource_id": int(resource.id),
                                            "resource_type": "video",
                                        },
                                        ensure_ascii=False,
                                    ),
                                    created_at=updated_at - timedelta(minutes=6),
                                )
                            )
                            summary["behavior_events"] += 2

                    target_notes = profile["notes"] if kp_index < 2 else max(0, profile["notes"] - 1)
                    existing_demo_notes = note_count_by_kp.get(kp_id, 0)
                    add_notes = max(0, target_notes - existing_demo_notes)
                    for offset in range(add_notes):
                        created_at = now - timedelta(days=11 - kp_index * 2 - offset, hours=(student_id + offset) % 4)
                        note = Note(
                            user_id=student_id,
                            kp_id=kp_id,
                            content=(
                                f"{NOTE_PREFIX} {student.full_name} 在《{subject}》中记录："
                                f"{kp_title} 需要结合课堂例题再复盘一次，重点关注易错点和操作步骤。"
                            ),
                            created_at=created_at,
                        )
                        session.add(note)
                        session.add(
                            LearningBehaviorEvent(
                                user_id=student_id,
                                course_id=course_id,
                                kp_id=kp_id,
                                event_type="note_create",
                                value_json=json.dumps(
                                    {"source": PAYLOAD_SOURCE, "topic": kp_title},
                                    ensure_ascii=False,
                                ),
                                created_at=created_at + timedelta(minutes=3),
                            )
                        )
                        summary["notes"] += 1
                        summary["behavior_events"] += 1

                    if expression_count_by_kp.get(kp_id, 0) < 1:
                        session.add(
                            ExpressionEvent(
                                user_id=student_id,
                                kp_id=kp_id,
                                label=str(profile["expression"]),
                                confidence=round(max(0.55, float(profile["practice_accuracy"]) + 0.08 - kp_index * 0.04), 2),
                                difficulty=round(min(0.9, 0.35 + kp_index * 0.12), 2),
                                created_at=now - timedelta(days=7 - kp_index, hours=(student_id + kp_index) % 5),
                            )
                        )
                        summary["expression_events"] += 1

                target_reco = int(profile["recommendations"])
                add_reco = max(0, target_reco - reco_marker_count)
                for offset in range(add_reco):
                    source_kp = tracked_kps[min(offset, len(tracked_kps) - 2)]
                    target_kp = tracked_kps[min(offset + 1, len(tracked_kps) - 1)]
                    if source_kp.id is None or target_kp.id is None:
                        continue
                    session.add(
                        RecommendationLog(
                            user_id=student_id,
                            subject=subject,
                            grade=grade,
                            source_kp_id=int(source_kp.id),
                            target_kp_id=int(target_kp.id),
                            persona_type=profile["persona"],
                            reason_summary=f"根据近期练习正确率与视频完成情况，建议继续推进到 {target_kp.title}。",
                            payload_json=json.dumps(
                                {
                                    "source": PAYLOAD_SOURCE,
                                    "course_id": course_id,
                                    "from": source_kp.title,
                                    "to": target_kp.title,
                                },
                                ensure_ascii=False,
                            ),
                            created_at=now - timedelta(days=5 - offset, hours=(student_id + offset) % 3),
                        )
                    )
                    summary["recommendations"] += 1

                base_behavior_target = 6 + (1 if profile["practice_accuracy"] >= 0.8 else 0)
                add_behavior = max(0, base_behavior_target - behavior_marker_count)
                extra_event_types = ["course_view", "resource_download", "resource_visit"]
                for offset in range(add_behavior):
                    kp = tracked_kps[offset % len(tracked_kps)]
                    if kp.id is None:
                        continue
                    event_type = extra_event_types[offset % len(extra_event_types)]
                    session.add(
                        LearningBehaviorEvent(
                            user_id=student_id,
                            course_id=course_id,
                            kp_id=int(kp.id),
                            event_type=event_type,
                            value_json=json.dumps(
                                {
                                    "source": PAYLOAD_SOURCE,
                                    "course_code": course.code,
                                    "kp_title": kp.title,
                                },
                                ensure_ascii=False,
                            ),
                            created_at=now - timedelta(days=14 - offset, hours=(course_id + student_id + offset) % 6),
                        )
                    )
                    summary["behavior_events"] += 1

                touched_subjects.add((student_id, subject, grade))

        session.commit()

        for student_id, subject, grade in sorted(touched_subjects):
            refresh_subject_mastery(session, user_id=student_id, subject=subject, grade=grade)
            summary["mastery_refresh_subjects"] += 1

        print(
            json.dumps(
                {
                    "ok": True,
                    "summary": dict(summary),
                    "touched_subjects": len(touched_subjects),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
