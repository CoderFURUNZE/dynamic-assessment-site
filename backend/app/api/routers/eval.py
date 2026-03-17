from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import (
    Course,
    KnowledgePoint,
    Mastery,
    PracticeAttempt,
    QuizAttempt,
    ReviewSchedule,
    VideoProgress,
)
from app.db.session import get_session
from app.schemas.eval import (
    CurrentStageOut,
    MasteryMapItem,
    MasteryOut,
    OverviewOut,
    OverviewPracticeOut,
    OverviewRecentOut,
    OverviewSummaryOut,
    ProfileOut,
    ProfileTrendPointOut,
    StageDimensionConfigOut,
    TeacherFeedbackOut,
)
from app.services.eval import refresh_subject_mastery, upsert_mastery
from app.services.learner_profile import (
    _json_load,
    get_or_create_persona_rule,
    get_profile_trend,
    get_stage_snapshot_trend,
    get_stage_teacher_feedback,
    persona_label,
    recalculate_profile_snapshot,
    resolve_persona_weights,
)

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/mastery", response_model=MasteryOut)
def mastery(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, kp_id)
    m = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp_id)).first()
    if m is None:
        m = upsert_mastery(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
    label = "mastered" if m.value >= 0.85 else "learning" if m.value >= 0.5 else "risk"
    return MasteryOut(
        kp_id=kp_id,
        value=float(m.value),
        label=label,
        direct_value=float(m.direct_value),
        status=m.status,
        reason_summary=m.reason_summary,
    )


@router.get("/profile", response_model=ProfileOut)
def profile(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    refresh_subject_mastery(session, user_id=user.id, subject=subject, grade=grade)
    snapshot = recalculate_profile_snapshot(
        session,
        user_id=user.id,
        subject=subject,
        grade=grade,
        refresh_mastery=False,
        persist=True,
    )
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    mastery_map = []
    weak_points = []
    for kp in kps:
        if kp.id is None:
            continue
        m = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp.id)).first()
        value = float(m.value) if m else 0.0
        mastery_map.append(
            {
                "kp_id": int(kp.id),
                "value": value,
                "status": m.status if m else "not_started",
                "direct_value": float(m.direct_value) if m else 0.0,
            }
        )
        if value < 0.5:
            weak_points.append(int(kp.id))
    stage_rows = list(reversed(get_stage_snapshot_trend(session, user_id=user.id, subject=subject, grade=grade)))
    if stage_rows:
        trend = [
            ProfileTrendPointOut(
                updated_at=item.updated_at.isoformat(),
                dynamic_score=float(item.dynamic_score),
                course_mastery=float(item.course_mastery),
                persona_type=item.persona_type.value,
                stage_title=item.stage_title,
                trend_label=item.trend_label,
            )
            for item in stage_rows
        ]
    else:
        trend = [
            ProfileTrendPointOut(
                updated_at=item.updated_at.isoformat(),
                dynamic_score=float(item.dynamic_score),
                course_mastery=float(item.course_mastery),
                persona_type=item.persona_type.value,
            )
            for item in reversed(get_profile_trend(session, user_id=user.id, subject=subject, grade=grade))
        ]
    current_stage = stage_rows[-1] if stage_rows else None
    rule = get_or_create_persona_rule(session, subject=subject, grade=grade)
    stage_dimension_cfg = (resolve_persona_weights(rule).get("stage_dimensions") or {})
    dimension_labels = {
        "engagement": "学习投入",
        "achievement": "学习成效",
        "habit": "学习习惯",
        "characteristic": "学习特征",
    }
    feedback = get_stage_teacher_feedback(
        session,
        user_id=user.id,
        subject=subject,
        grade=grade,
        stage_id=int(current_stage.stage_id) if current_stage is not None else None,
    )
    portrait_summary = _json_load(snapshot.portrait_summary_json, {})
    course = session.exec(
        select(Course)
        .where(Course.title == subject)
        .order_by(Course.id)
    ).first()
    return ProfileOut(
        user_id=user.id,
        course_id=int(current_stage.course_id) if current_stage is not None else int(course.id) if course and course.id is not None else None,
        subject=subject,
        grade=grade,
        mastery_map=mastery_map,
        weak_points=weak_points,
        persona_type=snapshot.persona_type.value,
        persona_label=persona_label(snapshot.persona_type),
        engagement=float(snapshot.engagement),
        achievement=float(snapshot.achievement),
        habit=float(current_stage.habit) if current_stage is not None else 0.0,
        characteristic=float(current_stage.characteristic) if current_stage is not None else 0.0,
        efficiency=float(snapshot.efficiency),
        risk=float(snapshot.risk),
        course_mastery=float(snapshot.course_mastery),
        dynamic_score=float(snapshot.dynamic_score),
        stability=float(snapshot.stability),
        risk_level=snapshot.risk_level,
        override_source=snapshot.override_source,
        reason_summary=snapshot.reason_summary,
        trend=trend,
        current_stage=(
            CurrentStageOut(
                stage_id=int(current_stage.stage_id),
                course_id=int(current_stage.course_id),
                stage_title=current_stage.stage_title,
                stage_order=int(current_stage.stage_order),
                engagement=float(current_stage.engagement),
                achievement=float(current_stage.achievement),
                habit=float(current_stage.habit),
                characteristic=float(current_stage.characteristic),
                dynamic_score=float(current_stage.dynamic_score),
                course_mastery=float(current_stage.course_mastery),
                trend_label=current_stage.trend_label,
                risk_level=current_stage.risk_level,
                reason_summary=current_stage.reason_summary,
                portrait_dimensions=_json_load(current_stage.dimension_summary_json, {}).get("portrait_dimensions", []),
                portrait_indicators=_json_load(current_stage.indicator_summary_json, {}).get("portrait_indicators", []),
            )
            if current_stage is not None
            else None
        ),
        stage_history=[
            CurrentStageOut(
                stage_id=int(item.stage_id),
                course_id=int(item.course_id),
                stage_title=item.stage_title,
                stage_order=int(item.stage_order),
                engagement=float(item.engagement),
                achievement=float(item.achievement),
                habit=float(item.habit),
                characteristic=float(item.characteristic),
                dynamic_score=float(item.dynamic_score),
                course_mastery=float(item.course_mastery),
                trend_label=item.trend_label,
                risk_level=item.risk_level,
                reason_summary=item.reason_summary,
                portrait_dimensions=_json_load(item.dimension_summary_json, {}).get("portrait_dimensions", []),
                portrait_indicators=_json_load(item.indicator_summary_json, {}).get("portrait_indicators", []),
            )
            for item in stage_rows
        ],
        dimension_config=[
            StageDimensionConfigOut(
                key=key,
                label=dimension_labels.get(key, key),
                enabled=bool(cfg.get("enabled", True)),
                weight=float(cfg.get("weight", 0.0)),
            )
            for key, cfg in stage_dimension_cfg.items()
        ],
        teacher_feedback=(
            TeacherFeedbackOut(
                stage_id=int(feedback.stage_id),
                feedback_tag=feedback.feedback_tag,
                comment=feedback.comment,
                updated_by=feedback.updated_by,
                updated_at=feedback.updated_at.isoformat(),
            )
            if feedback is not None
            else None
        ),
        portrait_dimensions=portrait_summary.get("portrait_dimensions", []),
        portrait_indicators=portrait_summary.get("portrait_indicators", []),
        final_portrait_dimensions=portrait_summary.get("final_portrait_dimensions", []),
        final_portrait_indicators=portrait_summary.get("final_portrait_indicators", []),
        term_summary=portrait_summary.get("term_summary", {}),
    )


@router.get("/overview", response_model=OverviewOut)
def overview(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    refresh_subject_mastery(session, user_id=user.id, subject=subject, grade=grade)
    profile_data = profile(subject=subject, grade=grade, session=session, user=user)
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    kp_ids = [int(k.id) for k in kps if k.id is not None]

    mastery_rows = []
    if kp_ids:
        mastery_rows = session.exec(
            select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id.in_(kp_ids))
        ).all()
    mastery_map = {int(m.kp_id): m for m in mastery_rows}

    items: list[MasteryMapItem] = []
    for kp in kps:
        if kp.id is None:
            continue
        row = mastery_map.get(int(kp.id))
        items.append(
            MasteryMapItem(
                kp_id=int(kp.id),
                code=kp.code,
                title=kp.title,
                chapter=kp.chapter,
                mastery=float(row.value) if row else 0.0,
                direct_value=float(row.direct_value) if row else 0.0,
                status=row.status if row else "not_started",
                reason_summary=row.reason_summary if row else "",
            )
        )

    total_kps = len(items)
    mastered = len([i for i in items if i.mastery >= 0.85])
    in_progress = len([i for i in items if 0.5 <= i.mastery < 0.85])
    not_mastered = len([i for i in items if i.mastery < 0.5])
    avg_mastery = (sum(i.mastery for i in items) / total_kps) if total_kps else 0.0
    weak_points = sorted(items, key=lambda x: x.mastery)[:5]

    last_practice_at = None
    last_quiz_at = None
    last_video_at = None
    if kp_ids:
        last_practice_at = session.exec(
            select(func.max(PracticeAttempt.created_at)).where(
                PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id.in_(kp_ids)
            )
        ).one()
        last_quiz_at = session.exec(
            select(func.max(QuizAttempt.created_at)).where(
                QuizAttempt.user_id == user.id, QuizAttempt.kp_id.in_(kp_ids)
            )
        ).one()
        last_video_at = session.exec(
            select(func.max(VideoProgress.updated_at)).where(
                VideoProgress.user_id == user.id, VideoProgress.kp_id.in_(kp_ids)
            )
        ).one()

    since = datetime.utcnow() - timedelta(days=7)
    practice_rows = []
    if kp_ids:
        practice_rows = session.exec(
            select(PracticeAttempt.correct).where(
                PracticeAttempt.user_id == user.id,
                PracticeAttempt.kp_id.in_(kp_ids),
                PracticeAttempt.created_at >= since,
            )
        ).all()
    practice_total = len(practice_rows)
    practice_correct = len([r for r in practice_rows if bool(r)])
    practice_accuracy = (practice_correct / practice_total) if practice_total else 0.0
    review_due = 0
    if kp_ids:
        review_due = int(
            session.exec(
                select(func.count()).select_from(ReviewSchedule).where(
                    ReviewSchedule.user_id == user.id,
                    ReviewSchedule.kp_id.in_(kp_ids),
                    ReviewSchedule.due_at <= datetime.utcnow(),
                )
            ).one()
            or 0
        )

    return OverviewOut(
        subject=subject,
        grade=grade,
        summary=OverviewSummaryOut(
            total_kps=total_kps,
            mastered=mastered,
            in_progress=in_progress,
            not_mastered=not_mastered,
            avg_mastery=avg_mastery,
            dynamic_score=float(profile_data.dynamic_score),
            risk_level=profile_data.risk_level,
        ),
        mastery_map=items,
        weak_points=weak_points,
        recent_activity=OverviewRecentOut(
            last_practice_at=last_practice_at.isoformat() if last_practice_at else None,
            last_quiz_at=last_quiz_at.isoformat() if last_quiz_at else None,
            last_video_at=last_video_at.isoformat() if last_video_at else None,
        ),
        practice_7d=OverviewPracticeOut(
            total=practice_total,
            correct=practice_correct,
            accuracy=practice_accuracy,
        ),
        review_due=review_due,
        profile=profile_data,
    )
