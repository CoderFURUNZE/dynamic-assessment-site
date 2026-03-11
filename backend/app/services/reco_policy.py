from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import func
from sqlmodel import Session, desc, select

from app.db.models import PracticeAttempt, Question


def difficulty_band(difficulty: float) -> str:
    if difficulty < 0.4:
        return "easy"
    if difficulty < 0.7:
        return "medium"
    return "hard"


def latest_attempts(session: Session, *, user_id: int, kp_id: int) -> list[tuple[PracticeAttempt, Question | None]]:
    latest = (
        select(
            PracticeAttempt.question_id,
            func.max(PracticeAttempt.created_at).label("max_created"),
        )
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .group_by(PracticeAttempt.question_id)
        .subquery()
    )
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(
            latest,
            (PracticeAttempt.question_id == latest.c.question_id)
            & (PracticeAttempt.created_at == latest.c.max_created),
        )
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .order_by(PracticeAttempt.created_at.desc())
    ).all()
    return rows


def evidence_checklist(
    session: Session,
    *,
    user_id: int,
    kp_id: int,
    sure_ratio_threshold: float = 0.5,
) -> dict:
    rows = latest_attempts(session, user_id=user_id, kp_id=kp_id)
    type_ok = {"mcq": False, "blank": False}
    band_ok = {"easy": False, "medium": False, "hard": False}
    medium_correct = 0
    hard_correct = 0
    total_correct = 0
    sure_correct = 0

    for attempt, question in rows:
        if question is None:
            continue
        if not attempt.correct:
            continue
        total_correct += 1
        if getattr(attempt, "self_report", "unknown") == "sure":
            sure_correct += 1
        q_type = question.type
        if q_type in type_ok:
            type_ok[q_type] = True
        band = difficulty_band(float(question.difficulty))
        band_ok[band] = True
        if band == "medium":
            medium_correct += 1
        if band == "hard":
            hard_correct += 1

    # Evidence requirements
    req_type_mcq = type_ok["mcq"]
    req_type_blank = type_ok["blank"]
    req_medium = band_ok["medium"]
    req_hard_or_two_medium = hard_correct > 0 or medium_correct >= 2
    sure_ratio = (sure_correct / total_correct) if total_correct > 0 else 0.0
    req_sure_ratio = sure_ratio >= max(0.0, min(1.0, sure_ratio_threshold))

    items = {
        "mcq_correct": req_type_mcq,
        "blank_correct": req_type_blank,
        "medium_correct": req_medium,
        "hard_or_two_medium": req_hard_or_two_medium,
        "sure_ratio": req_sure_ratio,
    }
    satisfied = sum(1 for v in items.values() if v)
    score = satisfied / len(items)

    missing = [k for k, v in items.items() if not v]
    return {
        "items": items,
        "missing": missing,
        "score": score,
        "summary": {
            "total_correct": total_correct,
            "medium_correct": medium_correct,
            "hard_correct": hard_correct,
            "sure_ratio": sure_ratio,
        },
    }

def recent_wrong_streak(session: Session, *, user_id: int, kp_id: int, window: int = 5) -> int:
    rows = session.exec(
        select(PracticeAttempt)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
        .limit(window)
    ).all()
    streak = 0
    for r in rows:
        if r.correct:
            break
        streak += 1
    return streak


def infer_guess_slip(
    *,
    duration_ms: int,
    expr_diff: float,
    fast_ms: int,
    slow_ms: int,
    self_report: str = "unknown",
) -> dict:
    guess_score = 0.0
    slip_score = 0.0
    if self_report == "guess":
        guess_score = 1.0
    if self_report == "sure":
        slip_score = 0.4
    if duration_ms <= fast_ms:
        guess_score = 1.0
    elif duration_ms <= int(fast_ms * 1.5):
        guess_score = 0.7

    if duration_ms >= slow_ms and expr_diff <= 0.4:
        slip_score = 1.0
    elif duration_ms >= int(slow_ms * 0.7) and expr_diff <= 0.5:
        slip_score = 0.7

    return {"guess_score": guess_score, "slip_score": slip_score}
