import json
import math
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from sqlalchemy import delete, func

from app.api.deps import get_current_user
from app.db.models import EvalConfig, ExpressionEvent, KnowledgePoint, PracticeAttempt, Question, ReviewSchedule
from app.db.session import get_session
from app.schemas.practice import (
    PracticeNextOut,
    PracticeQuestionOut,
    PracticeSubmitIn,
    PracticeStatsOut,
    PracticeWrongOut,
    ReviewItemOut,
    ReviewQueueOut,
)
from app.services.eval import upsert_mastery
from app.services.dl_reco import predict_one, score_questions, score_recent
from app.services.practice import practice_status
from app.services.reco_policy import evidence_checklist, recent_expression_state, recent_wrong_streak, difficulty_band

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


def _infer_wrong_tags(*, prompt: str, q_type: str) -> list[str]:
    p = prompt.lower()
    tags: list[str] = []
    if q_type == "mcq":
        tags.append("选择题")
    if q_type == "blank":
        tags.append("填空题")
    if any(k in p for k in ["概念", "定义", "性质", "含义", "公式", "定理"]):
        tags.append("概念理解")
    if any(k in p for k in ["计算", "求", "数值", "多少", "求解", "求出"]):
        tags.append("计算")
    if any(k in p for k in ["证明", "推导", "论证", "说明"]):
        tags.append("推理")
    if len(prompt) >= 80:
        tags.append("题干较长")
    if not tags:
        tags.append("综合")
    return tags


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
    self_report = (payload.self_report or "unknown").strip().lower()
    if self_report not in {"guess", "sure", "unknown"}:
        self_report = "unknown"
    session.add(
        PracticeAttempt(
            user_id=user.id,
            question_id=q.id,
            kp_id=q.kp_id,
            correct=is_correct,
            self_report=self_report,
            duration_ms=payload.duration_ms,
        )
    )
    _upsert_review_schedule(session, user_id=user.id, question=q, is_correct=is_correct)
    session.commit()
    mastery = upsert_mastery(
        session, user_id=user.id, kp_id=q.kp_id, subject=q.subject, grade=q.grade
    )
    return {
        "correct": is_correct,
        "explanation": q.explanation,
        "mastery": {"kp_id": q.kp_id, "value": mastery.value},
    }


def _next_interval_days(current: int) -> int:
    ladder = [1, 3, 7, 14, 30]
    for step in ladder:
        if current < step:
            return step
    return 30


def _upsert_review_schedule(*, session: Session, user_id: int, question: Question, is_correct: bool) -> None:
    now = datetime.utcnow()
    sched = session.exec(
        select(ReviewSchedule).where(ReviewSchedule.user_id == user_id, ReviewSchedule.question_id == question.id)
    ).first()

    if sched is None:
        if is_correct:
            return
        sched = ReviewSchedule(
            user_id=user_id,
            question_id=question.id,
            kp_id=question.kp_id,
            interval_days=1,
            due_at=now + timedelta(days=1),
            last_result="wrong",
            updated_at=now,
        )
        session.add(sched)
        return

    if is_correct:
        next_interval = _next_interval_days(int(sched.interval_days or 1))
        sched.interval_days = next_interval
        sched.due_at = now + timedelta(days=next_interval)
        sched.last_result = "correct"
    else:
        sched.interval_days = 1
        sched.due_at = now + timedelta(days=1)
        sched.last_result = "wrong"
    sched.updated_at = now
    session.add(sched)


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
    last_diff = 0.5
    if last:
        attempt, question = last
        last_diff = float(question.difficulty) if question is not None else 0.5
        last_correct = bool(attempt.correct)
        target = last_diff + (step if last_correct else -step)

    evidence = evidence_checklist(session, user_id=user.id, kp_id=kp_id)
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

    # Stability: pull target towards last difficulty and cap per-step jump.
    stability_strength = float(window.get("stability_strength", 0.4))
    stability_strength = max(0.0, min(1.0, stability_strength))
    max_jump = float(window.get("max_difficulty_jump", 0.2))
    max_jump = max(0.0, min(0.5, max_jump))

    if last:
        target = (1.0 - stability_strength) * target + stability_strength * last_diff
        if max_jump > 0:
            target = max(last_diff - max_jump, min(last_diff + max_jump, target))

    # Remedial: if frustration is high or wrong streak, bias to easier range.
    wrong_streak = recent_wrong_streak(session, user_id=user.id, kp_id=kp_id, window=5)
    expr_state = recent_expression_state(
        session,
        user_id=user.id,
        kp_id=kp_id,
        window=expr_n,
        conf_threshold=expr_conf_threshold,
    )
    if (not last_correct) and (wrong_streak >= 2 or float(expr_state.get("difficulty_avg", 0.5)) >= 0.6):
        target = max(0.0, target - step)

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
    w_need = float(window.get("w_need", 0.45))
    w_gain = float(window.get("w_gain", 0.4))
    w_risk = float(window.get("w_risk", 0.15))

    missing = set(evidence.get("missing", []))
    missing_types = set()
    missing_bands = set()
    for item in missing:
        if "mcq" in item:
            missing_types.add("mcq")
        if "blank" in item:
            missing_types.add("blank")
        if "medium" in item:
            missing_bands.add("medium")
        if "hard" in item:
            missing_bands.add("hard")

    risk = min(1.0, 0.6 * float(expr_state.get("difficulty_avg", 0.5)) + 0.4 * min(1.0, wrong_streak / 3))

    def rule_score(q: Question, target_value: float) -> float:
        need = 0.2
        if q.type in missing_types:
            need += 0.4
        band = difficulty_band(float(q.difficulty))
        if band in missing_bands:
            need += 0.4
        need = min(1.0, need)
        learn_gain = 1.0 - min(1.0, abs(float(q.difficulty) - target_value) * 1.5)
        return w_need * need + w_gain * learn_gain - w_risk * risk

    def learn_gain_from_prob(p: float) -> float:
        return max(0.0, 1.0 - abs(p - 0.65) / 0.65)

    for start in ranges:
        if start < 0 or start > 1.0:
            continue
        cand = candidates_in_range(start)
        if cand:
            scored = score_questions(session, user_id=user.id, kp_id=kp_id, questions=cand)
            if scored:
                scored_with_policy = []
                for prob, q in scored:
                    policy_score = rule_score(q, target)
                    gain_ml = learn_gain_from_prob(float(prob))
                    final = 0.7 * policy_score + 0.3 * gain_ml
                    scored_with_policy.append((final, prob, q))
                scored_sorted = sorted(scored_with_policy, key=lambda x: x[0], reverse=True)
                top_n = min(5, len(scored_sorted))
                final_score, best_prob, best_q = rng.choice(scored_sorted[:top_n])
                picked = best_q
                predicted_correct = float(best_prob)
                model_used = True
                reason = "policy+model"
            else:
                cand_scored = [(rule_score(q, target), q) for q in cand]
                cand_sorted = sorted(cand_scored, key=lambda x: x[0], reverse=True)
                top_n = min(5, len(cand_sorted))
                picked = rng.choice(cand_sorted[:top_n])[1]
                model_used = False
                reason = "policy_rule"
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
                reason = "policy+model_fallback"
            else:
                model_used = False
                reason = "policy_fallback"

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
        prompt = question.prompt if question else ""
        q_type = question.type if question else ""
        out.append(
            PracticeWrongOut(
                id=attempt.id,
                question_id=attempt.question_id,
                kp_id=attempt.kp_id,
                prompt=prompt,
                type=q_type,
                difficulty=float(question.difficulty) if question else 0.5,
                created_at=attempt.created_at.isoformat(),
                options=json.loads(question.options_json) if question else [],
                tags=_infer_wrong_tags(prompt=prompt, q_type=q_type),
            )
        )
    return out


@router.get("/wrong/page")
def wrong_page(
    kp_id: int,
    page: int = 1,
    page_size: int = 20,
    days: int | None = None,
    q_type: str | None = None,
    min_difficulty: float | None = None,
    max_difficulty: float | None = None,
    order: str = "recent",
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
    if q_type:
        base = base.where(Question.type == q_type)
    if min_difficulty is not None:
        base = base.where(Question.difficulty >= float(min_difficulty))
    if max_difficulty is not None:
        base = base.where(Question.difficulty <= float(max_difficulty))

    count_q = (
        select(func.count())
        .select_from(latest)
        .join(
            PracticeAttempt,
            (PracticeAttempt.question_id == latest.c.question_id)
            & (PracticeAttempt.created_at == latest.c.max_created),
        )
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.correct == False)  # noqa: E712
    )
    if days:
        count_q = count_q.where(PracticeAttempt.created_at >= since)
    if q_type:
        count_q = count_q.where(Question.type == q_type)
    if min_difficulty is not None:
        count_q = count_q.where(Question.difficulty >= float(min_difficulty))
    if max_difficulty is not None:
        count_q = count_q.where(Question.difficulty <= float(max_difficulty))
    total = session.exec(count_q).one()

    if order == "difficulty_asc":
        order_by = Question.difficulty.asc().nullslast()
    elif order == "difficulty_desc":
        order_by = Question.difficulty.desc().nullslast()
    else:
        order_by = PracticeAttempt.created_at.desc()

    rows = session.exec(
        base.order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items: list[PracticeWrongOut] = []
    for attempt, question in rows:
        prompt = question.prompt if question else ""
        q_type = question.type if question else ""
        items.append(
            PracticeWrongOut(
                id=attempt.id,
                question_id=attempt.question_id,
                kp_id=attempt.kp_id,
                prompt=prompt,
                type=q_type,
                difficulty=float(question.difficulty) if question else 0.5,
                created_at=attempt.created_at.isoformat(),
                options=json.loads(question.options_json) if question else [],
                tags=_infer_wrong_tags(prompt=prompt, q_type=q_type),
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


@router.get("/review/queue", response_model=ReviewQueueOut)
def review_queue(
    kp_id: int | None = None,
    days: int = 7,
    due_only: bool = False,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    days = max(1, min(30, int(days)))
    now = datetime.utcnow()
    until = now + timedelta(days=days)

    q = (
        select(ReviewSchedule, Question)
        .join(Question, ReviewSchedule.question_id == Question.id, isouter=True)
        .where(ReviewSchedule.user_id == user.id)
    )
    if kp_id:
        q = q.where(ReviewSchedule.kp_id == kp_id)
    if due_only:
        q = q.where(ReviewSchedule.due_at <= now)
    else:
        q = q.where(ReviewSchedule.due_at <= until)

    rows = session.exec(q.order_by(ReviewSchedule.due_at.asc())).all()
    items: list[ReviewItemOut] = []
    due_count = 0
    for sched, question in rows:
        overdue = sched.due_at <= now
        if overdue:
            due_count += 1
        items.append(
            ReviewItemOut(
                id=sched.id,
                question_id=sched.question_id,
                kp_id=sched.kp_id,
                prompt=question.prompt if question else "",
                type=question.type if question else "",
                difficulty=float(question.difficulty) if question else 0.5,
                due_at=sched.due_at.isoformat(),
                interval_days=int(sched.interval_days),
                last_result=sched.last_result,
                overdue=overdue,
            )
        )

    return ReviewQueueOut(total=len(items), due=due_count, items=items)

@router.get("/status")
def status(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return practice_status(session, user_id=user.id, kp_id=kp_id)
