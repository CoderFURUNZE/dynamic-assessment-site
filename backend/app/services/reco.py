from __future__ import annotations

import json

from sqlalchemy import Integer, func
from sqlmodel import Session, desc, select

from app.db.models import (
    EvalConfig,
    ExpressionEvent,
    KnowledgeEdge,
    LearningResource,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
)
from app.services.eval import upsert_mastery
from app.services.practice import practice_status
from app.services.reco_policy import (
    evidence_checklist,
    infer_guess_slip,
    recent_expression_state,
    recent_wrong_streak,
)


def _get_config(session: Session, subject: str, grade: str) -> EvalConfig:
    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == grade)).first()
    if cfg is None:
        cfg = EvalConfig(subject=subject, grade=grade)
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    return cfg


def recommend_next(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str):
    cfg = _get_config(session, subject, grade)
    thresholds = json.loads(cfg.thresholds_json)
    window = json.loads(cfg.window_json or "{}")
    unlock_accuracy = float(thresholds.get("unlock_accuracy", 0.9))
    unlock_max_difficulty = float(thresholds.get("unlock_max_difficulty", 0.35))

    mastery = upsert_mastery(session, user_id=user_id, kp_id=kp_id, subject=subject, grade=grade)

    quiz_cfg = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    quiz_pass_accuracy = float(quiz_cfg.pass_accuracy) if quiz_cfg is not None else 0.8
    quiz = session.exec(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id == kp_id)
        .order_by(desc(QuizAttempt.created_at))
        .limit(1)
    ).first()
    quiz_accuracy = quiz.score if quiz else 0.0
    quiz_ok = bool(quiz and quiz_accuracy >= quiz_pass_accuracy)

    practice_n = int(window.get("practice_attempts", 10))
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
        for a, q in practice_rows:
            d = float(q.difficulty) if q is not None else 0.5
            w = 0.5 + d
            weight_sum += w
            weighted_correct += w * (1.0 if a.correct else 0.0)
        practice_accuracy = (weighted_correct / weight_sum) if weight_sum > 0 else 0.0
    else:
        practice_accuracy = 0.0

    st = practice_status(session, user_id=user_id, kp_id=kp_id)
    practice_completed = bool(st.get("completed"))
    practice_ok = practice_completed and (practice_accuracy >= unlock_accuracy)

    expr_n = int(window.get("expressions", 20))
    expr = session.exec(
        select(ExpressionEvent)
        .where(ExpressionEvent.user_id == user_id, ExpressionEvent.kp_id == kp_id)
        .order_by(desc(ExpressionEvent.created_at))
        .limit(expr_n)
    ).all()
    if expr:
        difficulty_avg = sum(e.difficulty for e in expr) / len(expr)
        confidence_avg = sum(e.confidence for e in expr) / len(expr)
        expression_difficulty = float(difficulty_avg if confidence_avg >= 0.2 else 0.5)
    else:
        expression_difficulty = None

    mastery_threshold = 0.7
    sure_ratio_threshold = float(window.get("evidence_sure_ratio", 0.5))
    evidence = evidence_checklist(
        session,
        user_id=user_id,
        kp_id=kp_id,
        sure_ratio_threshold=sure_ratio_threshold,
    )
    evidence_threshold = float(window.get("evidence_threshold", 0.75))
    evidence_ok = evidence.get("score", 0.0) >= evidence_threshold
    # Unlock is driven by mastery + assessment outcomes (quiz + practice).
    # Expression is kept only as a weak diagnostic signal (not a gate).
    unlocked = quiz_ok and practice_ok and (mastery.value >= mastery_threshold) and evidence_ok

    # Remedial decision helper (soft guidance)
    expr_state = recent_expression_state(
        session,
        user_id=user_id,
        kp_id=kp_id,
        window=expr_n,
        conf_threshold=float(window.get("expression_conf_threshold", 0.2)),
    )
    wrong_streak = recent_wrong_streak(session, user_id=user_id, kp_id=kp_id, window=5)
    last_attempt = session.exec(
        select(PracticeAttempt)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id == kp_id)
        .order_by(desc(PracticeAttempt.created_at))
        .limit(1)
    ).first()
    guess_slip = {"guess_score": 0.0, "slip_score": 0.0}
    if last_attempt and not last_attempt.correct:
        fast_ms = int(window.get("guess_fast_ms", 8000))
        slow_ms = int(window.get("slip_slow_ms", 45000))
        guess_slip = infer_guess_slip(
            duration_ms=int(last_attempt.duration_ms or 0),
            expr_diff=float(expr_state.get("difficulty_avg", 0.5)),
            fast_ms=fast_ms,
            slow_ms=slow_ms,
            self_report=str(getattr(last_attempt, "self_report", "unknown") or "unknown"),
        )
    remedy_action = "none"
    if guess_slip["slip_score"] >= 0.7:
        remedy_action = "retry_same_level"
    elif guess_slip["guess_score"] >= 0.7 or float(expr_state.get("difficulty_avg", 0.5)) >= 0.6 or wrong_streak >= 2:
        remedy_action = "remedial_path"

    prereqs = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.next_id == kp_id)).all()
    blocked = []
    for p in prereqs:
        m = session.exec(
            select(QuizAttempt).where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id == p.prereq_id)
        ).first()
        if m is None:
            blocked.append(p.prereq_id)

    resources = session.exec(
        select(LearningResource).where(LearningResource.kp_id == kp_id).limit(3)
    ).all()
    resource_list = [
        {"id": r.id, "title": r.title, "url": r.url, "type": r.type.value} for r in resources
    ]

    practice_qs = session.exec(select(Question).where(Question.kp_id == kp_id).limit(5)).all()
    practice_list = [{"question_id": q.id, "type": q.type, "difficulty": q.difficulty} for q in practice_qs]

    next_edges = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == kp_id)).all()
    next_candidates = [e.next_id for e in next_edges]

    return {
        "diagnosis": {
            "kp_id": kp_id,
            "mastery": mastery.value,
            "reasons": [
                {"signal": "quiz_accuracy", "value": quiz_accuracy, "threshold": quiz_pass_accuracy},
                {"signal": "practice_accuracy", "value": practice_accuracy, "threshold": unlock_accuracy},
                {"signal": "practice_completed", "value": practice_completed, "threshold": True},
                {"signal": "mastery", "value": mastery.value, "threshold": mastery_threshold},
                {"signal": "expression_difficulty", "value": expression_difficulty, "threshold": unlock_max_difficulty},
                {"signal": "evidence_score", "value": evidence.get("score", 0.0), "threshold": evidence_threshold},
            ],
        },
        "evidence": evidence,
        "remedy": {
            "action": remedy_action,
            "guess_score": guess_slip["guess_score"],
            "slip_score": guess_slip["slip_score"],
            "wrong_streak": wrong_streak,
            "expression_difficulty": expr_state.get("difficulty_avg", 0.5),
        },
        "remedy_path": {"blocked_prereqs": blocked, "path": blocked + [kp_id] if blocked else [kp_id]},
        "resources": resource_list,
        "practice": practice_list,
        "unlock": {"can_unlock_next": unlocked, "next_candidates": next_candidates},
    }
