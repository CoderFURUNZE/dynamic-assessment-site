import json
import math
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from sqlalchemy import delete, func

from app.api.deps import get_current_user
from app.db.models import EvalConfig, ExpressionEvent, KnowledgePoint, PracticeAttempt, Question
from app.db.session import get_session
from app.schemas.practice import PracticeNextOut, PracticeQuestionOut, PracticeSubmitIn, PracticeStatsOut, PracticeWrongOut
from app.services.eval import upsert_mastery
from app.services.dl_reco import predict_one, score_questions, score_recent
from app.services.practice import practice_status

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/questions", response_model=list[PracticeQuestionOut])
def list_questions(
    kp_id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    ordered = session.exec(select(Question).where(Question.kp_id == kp_id).order_by(Question.id)).all()

    return [
        PracticeQuestionOut(
            id=q.id,
            kp_id=kp_id,
            type=q.type,
            prompt=q.prompt,
            options=json.loads(q.options_json),
            difficulty=q.difficulty,
        )
        for q in ordered
    ]


@router.post("/submit")
def submit(
    payload: PracticeSubmitIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    q = session.get(Question, payload.question_id)
    if q is None or q.kp_id != payload.kp_id:
        raise HTTPException(status_code=400, detail="Invalid question")
    answer = payload.answer.strip()
    is_correct = answer.upper() == q.answer.strip().upper()
    session.add(
        PracticeAttempt(
            user_id=user.id,
            question_id=q.id,
            kp_id=q.kp_id,
            correct=is_correct,
            duration_ms=payload.duration_ms,
        )
    )
    session.commit()
    mastery = upsert_mastery(
        session, user_id=user.id, kp_id=q.kp_id, subject=q.subject, grade=q.grade
    )
    return {
        "correct": is_correct,
        "explanation": q.explanation,
        "mastery": {"kp_id": q.kp_id, "value": mastery.value},
    }


@router.get("/next", response_model=PracticeNextOut)
def next_question(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == kp.subject, EvalConfig.grade == kp.grade)).first()
    window = json.loads(cfg.window_json) if cfg else {}
    total_cfg = int(kp.practice_total) if kp.practice_total is not None else int(window.get("practice_total", 10))
    step = float(window.get("difficulty_step", 0.1))
    step = max(0.05, min(0.5, step))

    total_available = session.exec(select(Question.id).where(Question.kp_id == kp_id)).all()
    total_available_n = len(total_available)
    total_n = min(total_cfg, total_available_n)

    attempted_rows = session.exec(
        select(PracticeAttempt.question_id, Question.prompt)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
    ).all()
    attempted_set = {int(r[0]) for r in attempted_rows if r[0] is not None}
    attempted_prompts = {r[1] for r in attempted_rows if r[1]}
    attempted_n = len(attempted_set)

    if total_n == 0:
        return PracticeNextOut(
            done=True,
            total_questions=0,
            attempted_questions=attempted_n,
            question=None,
        )
    if attempted_n >= total_n:
        return PracticeNextOut(
            done=True,
            total_questions=total_n,
            attempted_questions=attempted_n,
            question=None,
        )

    last = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
        .order_by(PracticeAttempt.created_at.desc())
        .limit(1)
    ).first()

    target = 0.0
    last_correct = True
    if last:
        attempt, question = last
        last_diff = float(question.difficulty) if question is not None else 0.5
        last_correct = bool(attempt.correct)
        target = last_diff + (step if last_correct else -step)

    expr_n = int(window.get("expressions", 20))
    expr_conf_threshold = float(window.get("expression_conf_threshold", 0.2))
    expr_influence = float(window.get("expression_influence", 1.0))
    expr_influence = max(0.0, min(3.0, expr_influence))
    expr = session.exec(
        select(ExpressionEvent)
        .where(ExpressionEvent.user_id == user.id, ExpressionEvent.kp_id == kp_id)
        .order_by(ExpressionEvent.created_at.desc())
        .limit(expr_n)
    ).all()
    if expr:
        diff_avg = sum(e.difficulty for e in expr) / len(expr)
        conf_avg = sum(e.confidence for e in expr) / len(expr)
        expr_diff = diff_avg if conf_avg >= expr_conf_threshold else 0.5
    else:
        expr_diff = 0.5
    expr_ease = 1.0 - expr_diff
    # Continuous adjustment: expr_ease in [0,1] -> delta in [-step*expr_influence, +step*expr_influence]
    # Higher ease -> harder next; lower ease -> easier next.
    target += (expr_ease - 0.5) * 2.0 * step * expr_influence

    target = max(0.0, min(1.0, target))

    bucket_start = math.floor(target / step) * step
    bucket_start = max(0.0, min(1.0 - step, bucket_start))

    def candidates_in_range(start: float) -> list[Question]:
        end = min(1.0, start + step)
        q = select(Question).where(Question.kp_id == kp_id, Question.difficulty >= start)
        if end < 1.0:
            q = q.where(Question.difficulty < end)
        if attempted_set:
            q = q.where(~Question.id.in_(attempted_set))
        if attempted_prompts:
            q = q.where(~Question.prompt.in_(attempted_prompts))
        return session.exec(q.order_by(Question.difficulty, Question.id)).all()

    ranges: list[float] = [bucket_start]
    max_steps = int(math.ceil(1.0 / step))
    for i in range(1, max_steps + 1):
        down = bucket_start - i * step
        up = bucket_start + i * step
        if last_correct:
            if up >= 0:
                ranges.append(up)
            if down >= 0:
                ranges.append(down)
        else:
            if down >= 0:
                ranges.append(down)
            if up >= 0:
                ranges.append(up)

    rng = random.Random(user.id * 1000003 + kp_id * 97 + attempted_n)
    picked = None
    picked_range = None
    predicted_correct = None
    model_used = False
    reason = None
    for start in ranges:
        if start < 0 or start > 1.0:
            continue
        cand = candidates_in_range(start)
        if cand:
            scored = score_questions(session, user_id=user.id, kp_id=kp_id, questions=cand)
            if scored:
                scored_sorted = sorted(scored, key=lambda x: x[0], reverse=True)
                top_n = min(5, len(scored_sorted))
                best_score, best_q = rng.choice(scored_sorted[:top_n])
                picked = best_q
                predicted_correct = float(best_score)
                model_used = True
                reason = "model_best_in_range"
            else:
                picked = rng.choice(cand)
                model_used = False
                reason = "rule_best_in_range"
            picked_range = start
            break

    if picked is None:
        q = select(Question).where(Question.kp_id == kp_id)
        if attempted_set:
            q = q.where(~Question.id.in_(attempted_set))
        if attempted_prompts:
            q = q.where(~Question.prompt.in_(attempted_prompts))
        picked = session.exec(q.order_by(Question.difficulty, Question.id)).first()
        picked_range = None
        if picked is not None:
            pred = predict_one(session, user_id=user.id, kp_id=kp_id, question=picked)
            if pred is not None:
                predicted_correct = pred
                model_used = True
                reason = "model_fallback"
            else:
                model_used = False
                reason = "rule_fallback"

    if picked is None:
        return PracticeNextOut(done=True, total_questions=total_n, attempted_questions=attempted_n, question=None)

    range_label = None
    if picked_range is not None:
        range_label = f"{picked_range:.1f}~{min(1.0, picked_range + step):.1f}"

    recent_preds = score_recent(session, user_id=user.id, kp_id=kp_id) or []
    return PracticeNextOut(
        done=False,
        total_questions=total_n,
        attempted_questions=attempted_n,
        difficulty_range=range_label,
        question=PracticeQuestionOut(
            id=picked.id,
            kp_id=kp_id,
            type=picked.type,
            prompt=picked.prompt,
            options=json.loads(picked.options_json),
            difficulty=picked.difficulty,
        ),
        model_used=model_used,
        predicted_correct=predicted_correct,
        reason=reason,
        recent_predictions=recent_preds,
    )


@router.post("/reset")
def reset_practice(
    payload: dict,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp_id = payload.get("kp_id")
    try:
        kp_id = int(kp_id)
    except Exception:
        raise HTTPException(status_code=400, detail="kp_id required")
    session.exec(
        delete(PracticeAttempt).where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
    )
    session.commit()
    return {"ok": True}


@router.get("/history")
def history(
    kp_id: int,
    limit: int = 50,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    limit = max(1, min(200, int(limit)))
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
        .order_by(PracticeAttempt.created_at.desc())
        .limit(limit)
    ).all()
    items = []
    correct_count = 0
    for attempt, question in rows:
        correct = bool(attempt.correct)
        if correct:
            correct_count += 1
        items.append(
            {
                "id": attempt.id,
                "question_id": attempt.question_id,
                "prompt": question.prompt if question else "",
                "type": question.type if question else "",
                "difficulty": float(question.difficulty) if question else 0.5,
                "correct": correct,
                "duration_ms": attempt.duration_ms,
                "created_at": attempt.created_at.isoformat(),
            }
        )
    total = len(items)
    accuracy = (correct_count / total) if total else 0.0
    return {
        "kp_id": kp_id,
        "total": total,
        "correct": correct_count,
        "incorrect": total - correct_count,
        "accuracy": accuracy,
        "items": items,
    }


@router.get("/stats", response_model=PracticeStatsOut)
def stats(
    kp_id: int,
    days: int = 14,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    days = max(1, min(90, days))
    since = datetime.utcnow() - timedelta(days=days)
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(
            PracticeAttempt.user_id == user.id,
            PracticeAttempt.kp_id == kp_id,
            PracticeAttempt.created_at >= since,
        )
    ).all()
    total = len(rows)
    correct = sum(1 for a, _ in rows if a.correct)
    incorrect = total - correct
    accuracy = (correct / total) if total else 0.0

    # 按日期聚合
    buckets: dict[str, dict] = {}
    for attempt, _ in rows:
        day = attempt.created_at.date().isoformat()
        if day not in buckets:
            buckets[day] = {"date": day, "total": 0, "correct": 0}
        buckets[day]["total"] += 1
        if attempt.correct:
            buckets[day]["correct"] += 1
    daily = []
    for day in sorted(buckets.keys()):
        b = buckets[day]
        daily.append(
            {
                "date": b["date"],
                "total": b["total"],
                "correct": b["correct"],
                "accuracy": (b["correct"] / b["total"]) if b["total"] else 0.0,
            }
        )

    return PracticeStatsOut(
        kp_id=kp_id,
        total=total,
        correct=correct,
        incorrect=incorrect,
        accuracy=accuracy,
        daily=daily,
    )


@router.get("/wrong", response_model=list[PracticeWrongOut])
def wrong_list(
    kp_id: int,
    limit: int = 50,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    limit = max(1, min(200, int(limit)))
    latest = (
        select(
            PracticeAttempt.question_id,
            func.max(PracticeAttempt.created_at).label("max_created"),
        )
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
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
        .where(PracticeAttempt.correct == False)  # noqa: E712
        .order_by(PracticeAttempt.created_at.desc())
        .limit(limit)
    ).all()
    out: list[PracticeWrongOut] = []
    for attempt, question in rows:
        out.append(
            PracticeWrongOut(
                id=attempt.id,
                question_id=attempt.question_id,
                kp_id=attempt.kp_id,
                prompt=question.prompt if question else "",
                type=question.type if question else "",
                difficulty=float(question.difficulty) if question else 0.5,
                created_at=attempt.created_at.isoformat(),
                options=json.loads(question.options_json) if question else [],
            )
        )
    return out


@router.get("/wrong/page")
def wrong_page(
    kp_id: int,
    page: int = 1,
    page_size: int = 20,
    days: int | None = None,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    latest = (
        select(
            PracticeAttempt.question_id,
            func.max(PracticeAttempt.created_at).label("max_created"),
        )
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
        .group_by(PracticeAttempt.question_id)
        .subquery()
    )
    base = (
        select(PracticeAttempt, Question)
        .join(
            latest,
            (PracticeAttempt.question_id == latest.c.question_id)
            & (PracticeAttempt.created_at == latest.c.max_created),
        )
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.correct == False)  # noqa: E712
    )
    if days:
        since = datetime.utcnow() - timedelta(days=max(1, min(90, int(days))))
        base = base.where(PracticeAttempt.created_at >= since)

    count_q = (
        select(func.count())
        .select_from(latest)
        .join(
            PracticeAttempt,
            (PracticeAttempt.question_id == latest.c.question_id)
            & (PracticeAttempt.created_at == latest.c.max_created),
        )
        .where(PracticeAttempt.correct == False)  # noqa: E712
    )
    if days:
        count_q = count_q.where(PracticeAttempt.created_at >= since)
    total = session.exec(count_q).one()

    rows = session.exec(
        base.order_by(PracticeAttempt.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items: list[PracticeWrongOut] = []
    for attempt, question in rows:
        items.append(
            PracticeWrongOut(
                id=attempt.id,
                question_id=attempt.question_id,
                kp_id=attempt.kp_id,
                prompt=question.prompt if question else "",
                type=question.type if question else "",
                difficulty=float(question.difficulty) if question else 0.5,
                created_at=attempt.created_at.isoformat(),
                options=json.loads(question.options_json) if question else [],
            )
        )
    return {"total": int(total or 0), "items": items, "page": page, "page_size": page_size}


@router.get("/export")
def export_csv(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    rows = session.exec(
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id == kp_id)
        .order_by(PracticeAttempt.created_at)
    ).all()
    lines = ["question_id,prompt,type,difficulty,correct,duration_ms,created_at"]
    for attempt, question in rows:
        prompt = (question.prompt if question else "").replace('"', "'").replace(",", "，")
        qtype = question.type if question else ""
        diff = float(question.difficulty) if question else 0.5
        lines.append(
            f"{attempt.question_id},\"{prompt}\",{qtype},{diff},{int(bool(attempt.correct))},{attempt.duration_ms},{attempt.created_at.isoformat()}"
        )
    csv = "\n".join(lines)
    return Response(content=csv, media_type="text/csv")


@router.get("/question/{question_id}", response_model=PracticeQuestionOut)
def get_question_detail(
    question_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    q = session.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return PracticeQuestionOut(
        id=q.id,
        kp_id=q.kp_id,
        type=q.type,
        prompt=q.prompt,
        options=json.loads(q.options_json),
        difficulty=q.difficulty,
    )

@router.get("/status")
def status(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return practice_status(session, user_id=user.id, kp_id=kp_id)
