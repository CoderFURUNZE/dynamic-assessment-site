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
    DynamicBreakdownOut,
    MasteryMapItem,
    MasteryOut,
    OverviewOut,
    OverviewPracticeOut,
    OverviewRecentOut,
    OverviewSummaryOut,
    PersonaSignalOut,
    PortraitTimelinePointOut,
    ProfileOut,
    ProfileTrendPointOut,
    StageDimensionConfigOut,
    TeacherFeedbackOut,
)
from app.services.eval import refresh_subject_mastery, upsert_mastery
from app.services.learner_profile import (
    build_ability_practice_cognitive_summary,
    build_kp_dimension_summary,
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


def _risk_level_label(dynamic_score: float) -> str:
    if dynamic_score >= 0.85:
        return "优秀"
    if dynamic_score >= 0.70:
        return "良好"
    if dynamic_score >= 0.50:
        return "预警"
    return "风险"


def _pct(value: float) -> str:
    return f"{round(float(value) * 100)}%"


def _signal_level(value: float, *, warn_low: float | None = None, warn_high: float | None = None) -> str:
    if warn_low is not None and value < warn_low:
        return "attention"
    if warn_high is not None and value > warn_high:
        return "attention"
    if value >= 0.72:
        return "positive"
    if value >= 0.45:
        return "neutral"
    return "attention"


def _build_persona_signals(
    *,
    persona_label: str,
    override_source: str,
    engagement: float,
    achievement: float,
    habit: float,
    characteristic: float,
    efficiency: float,
    risk: float,
    course_mastery: float,
    dynamic_score: float,
    stability: float,
) -> tuple[str, list[PersonaSignalOut]]:
    intro = (
        f"系统结合知识点掌握、练习/测验与（如有）阶段评价数据，将当前学习者归类为「{persona_label}」。"
        + (" 画像标签含人工覆盖，请以教师说明为准。" if override_source == "manual" else " 以下为据此标签拆解的各维度说明，便于理解动态评价来源。")
    )
    signals: list[PersonaSignalOut] = [
        PersonaSignalOut(
            key="persona",
            label="画像类型",
            detail=(
                f"标签：{persona_label}。"
                + ("来源：教师/管理员指定。" if override_source == "manual" else "来源：系统根据投入度、成效与效率等自动判定。")
            ),
            level="neutral",
        ),
        PersonaSignalOut(
            key="engagement",
            label="学习投入",
            detail=f"投入综合指数约 {_pct(engagement)}，体现学习频次、时长、资源完成与连续性等行为信号。",
            level=_signal_level(engagement, warn_low=0.38),
        ),
        PersonaSignalOut(
            key="achievement",
            label="学习成效",
            detail=f"成效综合指数约 {_pct(achievement)}，主要来自练习/测验表现与掌握度增长。",
            level=_signal_level(achievement, warn_low=0.48),
        ),
        PersonaSignalOut(
            key="habit",
            label="学习习惯",
            detail=f"习惯维度约 {_pct(habit)}（阶段评价中由出勤、任务按时率等构成；无阶段数据时可能为 0）。",
            level=_signal_level(habit, warn_low=0.35) if habit > 0 else "neutral",
        ),
        PersonaSignalOut(
            key="characteristic",
            label="学习特征",
            detail=f"特征维度约 {_pct(characteristic)}，反映问卷或阶段画像中的个性背景类指标汇总。",
            level=_signal_level(characteristic, warn_low=0.35) if characteristic > 0 else "neutral",
        ),
        PersonaSignalOut(
            key="efficiency",
            label="学习效率",
            detail=f"效率指数约 {_pct(efficiency)}，与单位时间正确率、任务完成情况相关。",
            level=_signal_level(efficiency, warn_low=0.45),
        ),
        PersonaSignalOut(
            key="risk",
            label="风险信号",
            detail=f"风险指数约 {_pct(risk)}，数值越高表示逾期、错题连击、学习中断等信号越强。",
            level="attention" if risk >= 0.48 else "neutral" if risk >= 0.22 else "positive",
        ),
        PersonaSignalOut(
            key="mastery",
            label="课程掌握度",
            detail=f"全课知识点掌握均值约 {_pct(course_mastery)}，动态评价中通常占较高权重。",
            level=_signal_level(course_mastery, warn_low=0.4),
        ),
        PersonaSignalOut(
            key="dynamic",
            label="动态综合分",
            detail=f"当前动态评分 {_pct(dynamic_score)}，稳定性约 {_pct(stability)}（分数波动越小稳定性越高）。",
            level=_signal_level(dynamic_score, warn_low=0.42),
        ),
    ]
    return intro, signals


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
    days: int = 14,
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
    mastery_row_map: dict[int, Mastery] = {}
    weak_points = []
    for kp in kps:
        if kp.id is None:
            continue
        m = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp.id)).first()
        if m is not None:
            mastery_row_map[int(kp.id)] = m
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
    stage_rows = list(
        reversed(get_stage_snapshot_trend(session, user_id=user.id, subject=subject, grade=grade, days=days))
    )
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
    portrait_timeline = []
    if stage_rows:
        portrait_timeline = [
            PortraitTimelinePointOut(
                updated_at=item.updated_at.isoformat(),
                persona_label=persona_label(item.persona_type),
                dynamic_score=float(item.dynamic_score),
                course_mastery=float(item.course_mastery),
                risk_level=_risk_level_label(float(item.dynamic_score)),
                stage_title=item.stage_title,
                trend_label=item.trend_label,
                reason_summary=item.reason_summary,
            )
            for item in stage_rows
        ]
    else:
        # get_profile_trend 返回 LearnerProfileSnapshot，无 stage_title / trend_label（仅阶段快照 StageEvaluationSnapshot 具备）
        portrait_timeline = [
            PortraitTimelinePointOut(
                updated_at=item.updated_at.isoformat(),
                persona_label=persona_label(item.persona_type),
                dynamic_score=float(item.dynamic_score),
                course_mastery=float(item.course_mastery),
                risk_level=_risk_level_label(float(item.dynamic_score)),
                stage_title=None,
                trend_label=None,
                reason_summary=item.reason_summary or "",
            )
            for item in reversed(get_profile_trend(session, user_id=user.id, subject=subject, grade=grade, days=days))
        ]
    _bd_raw = portrait_summary.get("dynamic_breakdown")
    dynamic_breakdown_parsed: DynamicBreakdownOut | None = None
    if isinstance(_bd_raw, dict) and _bd_raw:
        try:
            dynamic_breakdown_parsed = DynamicBreakdownOut.model_validate(_bd_raw)
        except Exception:
            dynamic_breakdown_parsed = None
    persona_intro, persona_signals = _build_persona_signals(
        persona_label=persona_label(snapshot.persona_type),
        override_source=str(snapshot.override_source or "auto"),
        engagement=float(snapshot.engagement),
        achievement=float(snapshot.achievement),
        habit=float(current_stage.habit) if current_stage is not None else 0.0,
        characteristic=float(current_stage.characteristic) if current_stage is not None else 0.0,
        efficiency=float(snapshot.efficiency),
        risk=float(snapshot.risk),
        course_mastery=float(snapshot.course_mastery),
        dynamic_score=float(snapshot.dynamic_score),
        stability=float(snapshot.stability),
    )
    course = session.exec(
        select(Course)
        .where(Course.title == subject)
        .order_by(Course.id)
    ).first()
    kp_dimension_summary = build_kp_dimension_summary(
        session,
        user_id=user.id,
        subject=subject,
        grade=grade,
        kps=kps,
        mastery_map=mastery_row_map,
    )
    kp_ids = [int(k.id) for k in kps if k.id is not None]
    ability_practice_stats = build_ability_practice_cognitive_summary(
        session,
        user_id=user.id,
        kp_ids=kp_ids,
    )
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
        kp_dimension_summary=kp_dimension_summary,
        ability_practice_stats=ability_practice_stats,
        portrait_timeline=portrait_timeline,
        dynamic_breakdown=dynamic_breakdown_parsed,
        persona_intro=persona_intro,
        persona_signals=persona_signals,
    )


@router.get("/overview", response_model=OverviewOut)
def overview(
    subject: str,
    grade: str,
    days: int = 14,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    refresh_subject_mastery(session, user_id=user.id, subject=subject, grade=grade)
    profile_data = profile(subject=subject, grade=grade, days=days, session=session, user=user)
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
