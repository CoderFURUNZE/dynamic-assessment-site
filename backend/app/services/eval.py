from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, desc, select

from app.db.models import (
    KnowledgeEdge,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    RelationType,
    ResourceType,
    ReviewSchedule,
    VideoProgress,
    PracticeAttempt,
    Question,
    QuizAttempt,
)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mastery_status(*, final_value: float, direct_value: float, activity_count: int) -> str:
    if activity_count == 0 and direct_value == 0:
        return "not_started"
    if final_value >= 0.85:
        return "mastered"
    if final_value >= 0.5:
        return "learning"
    return "risk"


def _resource_completion(session: Session, *, user_id: int, kp_id: int) -> float:
    resources = session.exec(select(LearningResource).where(LearningResource.kp_id == kp_id)).all()
    if not resources:
        return 0.0
    progress_map = {
        int(row.resource_id): row
        for row in session.exec(
            select(VideoProgress).where(VideoProgress.user_id == user_id, VideoProgress.kp_id == kp_id)
        ).all()
    }
    visited_resource_ids: set[int] = set()
    for event in session.exec(
        select(LearningBehaviorEvent).where(
            LearningBehaviorEvent.user_id == user_id,
            LearningBehaviorEvent.kp_id == kp_id,
            LearningBehaviorEvent.event_type.in_(["resource_visit", "resource_download"]),
        )
    ).all():
        try:
            import json

            payload = json.loads(event.value_json or "{}")
            resource_id = int(payload.get("resource_id") or 0)
        except Exception:
            resource_id = 0
        if resource_id > 0:
            visited_resource_ids.add(resource_id)

    score = 0.0
    counted = 0
    for resource in resources:
        if resource.id is None:
            continue
        counted += 1
        resource_id = int(resource.id)
        if resource.type == ResourceType.video:
            row = progress_map.get(resource_id)
            if row is None:
                continue
            if row.completed:
                score += 1.0
            elif row.duration_seconds and row.duration_seconds > 0:
                score += _clamp01(float(row.watched_seconds or 0) / float(row.duration_seconds))
            continue
        if resource_id in visited_resource_ids:
            score += 1.0
    return _clamp01(score / counted) if counted else 0.0


def _learning_frequency(session: Session, *, user_id: int, kp_id: int) -> float:
    since = datetime.utcnow() - timedelta(days=30)
    practice_count = len(
        session.exec(
            select(PracticeAttempt.id).where(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.kp_id == kp_id,
                PracticeAttempt.created_at >= since,
            )
        ).all()
    )
    quiz_count = len(
        session.exec(
            select(QuizAttempt.id).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.kp_id == kp_id,
                QuizAttempt.created_at >= since,
            )
        ).all()
    )
    video_count = len(
        session.exec(
            select(VideoProgress.id).where(
                VideoProgress.user_id == user_id,
                VideoProgress.kp_id == kp_id,
                VideoProgress.updated_at >= since,
            )
        ).all()
    )
    return _clamp01((practice_count + quiz_count + video_count) / 10.0)


def _review_completion(session: Session, *, user_id: int, kp_id: int) -> float:
    rows = session.exec(
        select(ReviewSchedule).where(ReviewSchedule.user_id == user_id, ReviewSchedule.kp_id == kp_id)
    ).all()
    if not rows:
        return 0.0
    correct = len([row for row in rows if row.last_result == "correct"])
    return _clamp01(correct / len(rows))


def upsert_mastery(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str) -> Mastery:
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise ValueError(f"Knowledge point not found: {kp_id}")

    practice_rows = session.exec(
        select(PracticeAttempt)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
    ).all()
    quiz_rows = session.exec(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id == kp_id)
        .order_by(desc(QuizAttempt.created_at))
        .limit(5)
    ).all()

    question_ids = session.exec(select(Question.id).where(Question.kp_id == kp_id).order_by(Question.id)).all()
    available_questions = len([item for item in question_ids if item is not None])
    required_questions = min(int(kp.practice_total or 5), available_questions) if available_questions else 0
    required_questions = max(1, required_questions) if available_questions else 0
    correct_question_ids = {int(row.question_id) for row in practice_rows if row.correct and row.question_id is not None}
    practice_progress = _clamp01(len(correct_question_ids) / required_questions) if required_questions > 0 else 0.0
    practice_accuracy = mean(1.0 if row.correct else 0.0 for row in practice_rows) if practice_rows else 0.0
    quiz_accuracy = mean(float(row.score) for row in quiz_rows) if quiz_rows else 0.0
    resource_completion = _resource_completion(session, user_id=user_id, kp_id=kp_id)
    learning_frequency = _learning_frequency(session, user_id=user_id, kp_id=kp_id)
    review_completion = _review_completion(session, user_id=user_id, kp_id=kp_id)

    assessment_value = max(practice_progress, quiz_accuracy)
    process_value = max(learning_frequency, review_completion)
    combined_value = _clamp01(assessment_value * 0.6 + resource_completion * 0.3 + process_value * 0.1)
    direct_value = _clamp01(max(assessment_value, combined_value))
    final_value = direct_value
    activity_count = len(practice_rows) + len(quiz_rows) + (1 if resource_completion > 0 else 0)
    status = _mastery_status(final_value=final_value, direct_value=direct_value, activity_count=activity_count)
    reason_summary = (
        f"测验 {quiz_accuracy:.2f} / 练习 {practice_accuracy:.2f} / 资源 {resource_completion:.2f} / "
        f"频次 {learning_frequency:.2f} / 复习 {review_completion:.2f}"
    )

    reason_summary = (
        f"练习进度 {len(correct_question_ids)}/{required_questions or available_questions} / "
        f"练习正确率 {practice_accuracy:.2f}"
    )

    reason_summary = (
        f"练习进度 {len(correct_question_ids)}/{required_questions or available_questions} / "
        f"练习正确率 {practice_accuracy:.2f} / 小测 {quiz_accuracy:.2f} / "
        f"资源学习 {resource_completion:.2f} / 学习频次 {learning_frequency:.2f} / 复习 {review_completion:.2f}"
    )

    def apply_values(mastery: Mastery) -> Mastery:
        mastery.value = final_value
        mastery.direct_value = direct_value
        mastery.status = status
        mastery.reason_summary = reason_summary
        mastery.updated_at = datetime.utcnow()
        return mastery

    mastery = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == kp_id)).first()
    if mastery is None:
        mastery = apply_values(Mastery(user_id=user_id, kp_id=kp_id))
    else:
        mastery = apply_values(mastery)

    session.add(mastery)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        mastery = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == kp_id)).first()
        if mastery is None:
            raise
        session.add(apply_values(mastery))
        session.commit()
    session.refresh(mastery)
    return mastery


def refresh_subject_mastery(session: Session, *, user_id: int, subject: str, grade: str) -> list[Mastery]:
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    rows: list[Mastery] = []
    for kp in kps:
        if kp.id is None:
            continue
        rows.append(upsert_mastery(session, user_id=user_id, kp_id=int(kp.id), subject=subject, grade=grade))
    return rows
