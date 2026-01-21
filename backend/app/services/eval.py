from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session, desc, select

from app.db.models import EvalConfig, ExpressionEvent, Mastery, PracticeAttempt, Question, QuizAttempt, VideoProgress


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _get_config(session: Session, subject: str, grade: str) -> EvalConfig:
    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == grade)).first()
    if cfg is None:
        cfg = EvalConfig(subject=subject, grade=grade)
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    return cfg


def upsert_mastery(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str) -> Mastery:
    cfg = _get_config(session, subject, grade)
    weights = json.loads(cfg.weights_json)
    window = json.loads(cfg.window_json)

    practice_n = int(window.get("practice_attempts", 10))
    expr_n = int(window.get("expressions", 20))

    practice_rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
        .limit(practice_n)
    ).all()
    if practice_rows:
        weighted_correct = 0.0
        weight_sum = 0.0
        duration_ms_sum = 0.0
        for attempt, question in practice_rows:
            difficulty = float(question.difficulty) if question is not None else 0.5
            weight = 0.5 + difficulty
            weight_sum += weight
            weighted_correct += weight * (1.0 if attempt.correct else 0.0)
            duration_ms_sum += attempt.duration_ms
        practice_accuracy = (weighted_correct / weight_sum) if weight_sum > 0 else 0.0
        duration_ms_avg = duration_ms_sum / len(practice_rows)
    else:
        practice_accuracy = 0.0
        duration_ms_avg = 0.0

    quiz = session.exec(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id == kp_id)
        .order_by(desc(QuizAttempt.created_at))
        .limit(3)
    ).all()
    quiz_accuracy = quiz[0].score if quiz else 0.0

    expr = session.exec(
        select(ExpressionEvent)
        .where(ExpressionEvent.user_id == user_id, ExpressionEvent.kp_id == kp_id)
        .order_by(desc(ExpressionEvent.created_at))
        .limit(expr_n)
    ).all()
    if expr:
        difficulty_avg = sum(e.difficulty for e in expr) / len(expr)
        confidence_avg = sum(e.confidence for e in expr) / len(expr)
        difficulty = difficulty_avg if confidence_avg >= 0.2 else 0.5
    else:
        difficulty = 0.5

    expression_ease = 1.0 - difficulty

    video_rows = session.exec(
        select(VideoProgress).where(VideoProgress.user_id == user_id, VideoProgress.kp_id == kp_id)
    ).all()
    if video_rows:
        best_ratio = 0.0
        for r in video_rows:
            if r.duration_seconds > 0:
                best_ratio = max(best_ratio, r.watched_seconds / r.duration_seconds)
        video_full_ratio = float(window.get("video_complete_ratio", 0.8))
        video_min_ratio = float(window.get("video_min_ratio", 0.0))
        if video_full_ratio <= video_min_ratio:
            video_min_ratio = 0.0
        if best_ratio <= video_min_ratio:
            video_completion = 0.0
        elif best_ratio >= video_full_ratio:
            video_completion = 1.0
        else:
            video_completion = (best_ratio - video_min_ratio) / (video_full_ratio - video_min_ratio)
    else:
        video_completion = 0.0

    duration_penalty = 0.0
    if duration_ms_avg > 0:
        duration_penalty = _clamp01((duration_ms_avg - 60_000) / 120_000)

    w_quiz = float(weights.get("quiz_accuracy", 0.2))
    w_practice = float(weights.get("practice_accuracy", 0.65))
    w_expr = float(weights.get("expression_ease", 0.1))
    w_video = float(weights.get("video_completion", 0.05))
    w_penalty = float(weights.get("duration_penalty", 0.0))

    # Cold start: if practice attempts are too few, reduce practice weight and redistribute.
    practice_count = len(practice_rows)
    if practice_count < 3:
        w_practice = w_practice * 0.5
        remaining = 1.0 - w_practice
        other_sum = w_quiz + w_expr + w_video
        if other_sum > 0:
            w_quiz = remaining * (w_quiz / other_sum)
            w_expr = remaining * (w_expr / other_sum)
            w_video = remaining * (w_video / other_sum)

    raw = (
        w_quiz * quiz_accuracy
        + w_practice * practice_accuracy
        + w_expr * expression_ease
        + w_video * video_completion
        - w_penalty * duration_penalty
    )
    mastery_value = _clamp01(raw)

    mastery = session.exec(
        select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == kp_id)
    ).first()
    if mastery is None:
        mastery = Mastery(user_id=user_id, kp_id=kp_id, value=mastery_value, updated_at=datetime.utcnow())
    else:
        # Keep mastery monotonic: never decrease once achieved.
        mastery.value = max(float(mastery.value), mastery_value)
        mastery.updated_at = datetime.utcnow()

    session.add(mastery)
    session.commit()
    session.refresh(mastery)
    return mastery
