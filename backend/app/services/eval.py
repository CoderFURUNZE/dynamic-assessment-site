from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean

from sqlmodel import Session, desc, select

from app.db.models import (
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    Mastery,
    RelationType,
    ResourceType,
    ReviewSchedule,
    VideoProgress,
    PracticeAttempt,
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
    resources = session.exec(
        select(LearningResource).where(LearningResource.kp_id == kp_id, LearningResource.type == ResourceType.video)
    ).all()
    if not resources:
        return 0.0
    progress_map = {
        int(row.resource_id): row
        for row in session.exec(
            select(VideoProgress).where(VideoProgress.user_id == user_id, VideoProgress.kp_id == kp_id)
        ).all()
    }
    completed = 0
    for resource in resources:
        if resource.id is None:
            continue
        row = progress_map.get(int(resource.id))
        if row is not None and row.completed:
            completed += 1
    return _clamp01(completed / len(resources))


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
        .limit(20)
    ).all()
    quiz_rows = session.exec(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id == kp_id)
        .order_by(desc(QuizAttempt.created_at))
        .limit(5)
    ).all()

    practice_accuracy = mean(1.0 if row.correct else 0.0 for row in practice_rows) if practice_rows else 0.0
    quiz_accuracy = mean(float(row.score) for row in quiz_rows) if quiz_rows else 0.0
    resource_completion = _resource_completion(session, user_id=user_id, kp_id=kp_id)
    learning_frequency = _learning_frequency(session, user_id=user_id, kp_id=kp_id)
    review_completion = _review_completion(session, user_id=user_id, kp_id=kp_id)

    direct_value = _clamp01(
        0.30 * quiz_accuracy
        + 0.35 * practice_accuracy
        + 0.15 * resource_completion
        + 0.10 * learning_frequency
        + 0.10 * review_completion
    )

    prereq_edges = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.next_id == kp_id,
            KnowledgeEdge.relation_type == RelationType.prerequisite,
        )
    ).all()
    if prereq_edges:
        prereq_values: list[float] = []
        for edge in prereq_edges:
            mastery = session.exec(
                select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == edge.prereq_id)
            ).first()
            prereq_values.append(float(mastery.value) if mastery is not None else 0.0)
        prereq_avg = mean(prereq_values) if prereq_values else 0.5
    else:
        prereq_avg = 0.5

    final_value = _clamp01(0.80 * direct_value + 0.20 * prereq_avg)
    activity_count = len(practice_rows) + len(quiz_rows)
    status = _mastery_status(final_value=final_value, direct_value=direct_value, activity_count=activity_count)
    reason_summary = (
        f"测验 {quiz_accuracy:.2f} / 练习 {practice_accuracy:.2f} / 资源 {resource_completion:.2f} / "
        f"频次 {learning_frequency:.2f} / 复习 {review_completion:.2f}"
    )

    mastery = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == kp_id)).first()
    if mastery is None:
        mastery = Mastery(
            user_id=user_id,
            kp_id=kp_id,
            value=final_value,
            direct_value=direct_value,
            status=status,
            reason_summary=reason_summary,
            updated_at=datetime.utcnow(),
        )
    else:
        mastery.value = final_value
        mastery.direct_value = direct_value
        mastery.status = status
        mastery.reason_summary = reason_summary
        mastery.updated_at = datetime.utcnow()

    session.add(mastery)
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
