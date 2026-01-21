import json

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import EvalConfig, KnowledgePoint, PracticeAttempt, Question


def _get_practice_total(session: Session, *, kp_id: int) -> int:
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        return 0
    if kp.practice_total is not None:
        total_cfg = int(kp.practice_total)
    else:
        total_cfg = 10
        cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == kp.subject, EvalConfig.grade == kp.grade)).first()
        if cfg is not None:
            window = json.loads(cfg.window_json or "{}")
            total_cfg = int(window.get("practice_total", 10))
    available = session.exec(select(func.count()).select_from(Question).where(Question.kp_id == kp_id)).one()
    total_n = min(int(total_cfg), int(available or 0))
    return max(0, total_n)


def practice_status(session: Session, *, user_id: int, kp_id: int) -> dict:
    total_n = _get_practice_total(session, kp_id=kp_id)
    attempted = session.exec(
        select(func.count(func.distinct(PracticeAttempt.question_id)))
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
    ).one()
    attempted_n = int(attempted or 0)
    return {
        "kp_id": kp_id,
        "total_questions": total_n,
        "attempted_questions": attempted_n,
        "completed": total_n > 0 and attempted_n >= total_n,
    }
