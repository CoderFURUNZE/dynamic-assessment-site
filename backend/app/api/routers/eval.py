from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import false, func, or_
from sqlmodel import Session, select

from app.api.deps import assert_student_kp_access, assert_student_subject_access, get_current_user
from app.db.models import (
    Course,
    CourseApplication,
    Enrollment,
    EnrollmentStatus,
    KnowledgePoint,
    LearningBehaviorEvent,
    Mastery,
    PracticeAttempt,
    QuizAttempt,
    RecommendationLog,
    ReviewSchedule,
    VideoProgress,
    ApplicationStatus,
    CourseStage,
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
    build_graph_coverage_summary,
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


def _resolve_student_subject_grade(session: Session, user_id: int) -> tuple[str, str]:
    enrollments = session.exec(
        select(Enrollment)
        .where(Enrollment.student_id == user_id, Enrollment.status == EnrollmentStatus.active)
        .order_by(Enrollment.enrolled_at.desc())
    ).all()
    course_ids = [int(item.course_id) for item in enrollments]
    if not course_ids:
        approved = session.exec(
            select(CourseApplication.course_id)
            .where(
                CourseApplication.student_id == user_id,
                CourseApplication.status == ApplicationStatus.approved,
            )
            .order_by(CourseApplication.created_at.desc())
        ).all()
        course_ids = [int(item) for item in approved if item is not None]
    if not course_ids:
        raise HTTPException(status_code=400, detail="subject and grade are required")

    course = session.get(Course, course_ids[0])
    if course is None:
        raise HTTPException(status_code=400, detail="subject and grade are required")

    stage = session.exec(
        select(CourseStage)
        .where(CourseStage.course_id == int(course.id))
        .order_by(CourseStage.stage_order, CourseStage.id)
    ).first()
    if stage is not None and str(stage.grade or "").strip():
        return str(course.title), str(stage.grade).strip()

    kp = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == course.title)
        .order_by(KnowledgePoint.id)
    ).first()
    if kp is not None and str(kp.grade or "").strip():
        return str(course.title), str(kp.grade).strip()
    return str(course.title), "通用"


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


def _label_from_score(value: float) -> str:
    if value >= 0.85:
        return "优势"
    if value >= 0.65:
        return "稳定"
    if value >= 0.45:
        return "待加强"
    return "薄弱"


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
    if getattr(user, "role", None) == "student":
        kp = assert_student_kp_access(session, int(user.id), kp_id, allow_completed=True)
    else:
        kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
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
    subject: str | None = None,
    grade: str | None = None,
    days: int = 14,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if not subject or not grade:
        if getattr(user, "role", None) == "student":
            subject, grade = _resolve_student_subject_grade(session, int(user.id))
        else:
            raise HTTPException(status_code=400, detail="subject and grade are required")
    if getattr(user, "role", None) == "student":
        assert_student_subject_access(session, int(user.id), subject, allow_completed=True)
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
    graph_coverage = build_graph_coverage_summary(kps=list(kps), mastery_map=mastery_row_map)
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
    now = datetime.utcnow()
    since_30d = now - timedelta(days=30)
    since_14d = now - timedelta(days=14)
    course_id = int(course.id) if course and course.id is not None else None

    behavior_scope_stmt = select(LearningBehaviorEvent).where(
        LearningBehaviorEvent.user_id == user.id,
        LearningBehaviorEvent.created_at >= since_30d,
    )
    if course_id is not None and kp_ids:
        behavior_scope_stmt = behavior_scope_stmt.where(
            or_(
                LearningBehaviorEvent.course_id == course_id,
                LearningBehaviorEvent.kp_id.in_(kp_ids),
            )
        )
    elif course_id is not None:
        behavior_scope_stmt = behavior_scope_stmt.where(LearningBehaviorEvent.course_id == course_id)
    elif kp_ids:
        behavior_scope_stmt = behavior_scope_stmt.where(LearningBehaviorEvent.kp_id.in_(kp_ids))
    else:
        behavior_scope_stmt = behavior_scope_stmt.where(false())
    behavior_rows_30d = session.exec(
        behavior_scope_stmt.order_by(LearningBehaviorEvent.created_at.desc()).limit(800)
    ).all()
    behavior_rows_14d = [row for row in behavior_rows_30d if row.created_at and row.created_at >= since_14d]

    practice_rows_30d = session.exec(
        select(PracticeAttempt)
        .where(
            PracticeAttempt.user_id == user.id,
            PracticeAttempt.kp_id.in_(kp_ids) if kp_ids else True,
            PracticeAttempt.created_at >= since_30d,
        )
        .order_by(PracticeAttempt.created_at.desc())
        .limit(100)
    ).all()
    quiz_rows_30d = session.exec(
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user.id,
            QuizAttempt.kp_id.in_(kp_ids) if kp_ids else True,
            QuizAttempt.created_at >= since_30d,
        )
        .order_by(QuizAttempt.created_at.desc())
        .limit(80)
    ).all()
    video_rows_30d = session.exec(
        select(VideoProgress)
        .where(
            VideoProgress.user_id == user.id,
            VideoProgress.kp_id.in_(kp_ids) if kp_ids else True,
            VideoProgress.updated_at >= since_30d,
        )
        .order_by(VideoProgress.updated_at.desc())
        .limit(80)
    ).all()
    recommendation_rows_30d = session.exec(
        select(RecommendationLog)
        .where(
            RecommendationLog.user_id == user.id,
            RecommendationLog.subject == subject,
            RecommendationLog.grade == grade,
            RecommendationLog.created_at >= since_30d,
        )
        .order_by(RecommendationLog.created_at.desc())
        .limit(30)
    ).all()

    login_rows_30d = [row for row in behavior_rows_30d if (row.event_type or "").strip().lower() == "login"]
    login_days_30d = {row.created_at.date() for row in login_rows_30d if row.created_at}
    practice_14d = [row for row in practice_rows_30d if row.created_at and row.created_at >= since_14d]
    quiz_14d = [row for row in quiz_rows_30d if row.created_at and row.created_at >= since_14d]
    video_14d = [row for row in video_rows_30d if row.updated_at and row.updated_at >= since_14d]
    active_days_14d = (
        {row.created_at.date() for row in behavior_rows_14d if row.created_at}
        | {row.created_at.date() for row in practice_14d if row.created_at}
        | {row.created_at.date() for row in quiz_14d if row.created_at}
        | {row.updated_at.date() for row in video_14d if row.updated_at}
    )
    consecutive_days_14d = 0
    if active_days_14d:
        ordered = sorted(active_days_14d, reverse=True)
        consecutive_days_14d = 1
        for idx in range(1, len(ordered)):
            if (ordered[idx - 1] - ordered[idx]).days == 1:
                consecutive_days_14d += 1
                continue
            break
    study_seconds_14d = (
        sum(max(0, int(row.duration_ms or 0)) for row in practice_14d) / 1000.0
        + sum(max(0, int(row.duration_ms or 0)) for row in quiz_14d) / 1000.0
        + sum(max(0.0, float(row.watched_seconds or 0.0)) for row in video_14d)
    )
    practice_accuracy_30d = (
        len([row for row in practice_rows_30d if bool(row.correct)]) / len(practice_rows_30d)
        if practice_rows_30d
        else 0.0
    )
    video_completion_values_30d = [
        min(1.0, max(0.0, float(row.watched_seconds or 0.0) / float(row.duration_seconds)))
        for row in video_rows_30d
        if float(row.duration_seconds or 0.0) > 0
    ]
    avg_video_completion_30d = (
        sum(video_completion_values_30d) / len(video_completion_values_30d)
        if video_completion_values_30d
        else 0.0
    )
    event_counter = {}
    for row in behavior_rows_30d:
        key = (row.event_type or "").strip() or "unknown"
        event_counter[key] = int(event_counter.get(key, 0)) + 1
    top_event_types_30d = [
        {"event_type": key, "count": count}
        for key, count in sorted(event_counter.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    latest_recommendation = recommendation_rows_30d[0] if recommendation_rows_30d else None
    latest_recommendation_payload = {}
    if latest_recommendation is not None:
        target_kp = session.get(KnowledgePoint, int(latest_recommendation.target_kp_id))
        source_kp = session.get(KnowledgePoint, int(latest_recommendation.source_kp_id))
        latest_recommendation_payload = {
            "target_kp_id": int(latest_recommendation.target_kp_id),
            "target_kp_title": target_kp.title if target_kp is not None else "",
            "source_kp_id": int(latest_recommendation.source_kp_id),
            "source_kp_title": source_kp.title if source_kp is not None else "",
            "reason_summary": latest_recommendation.reason_summary,
            "created_at": latest_recommendation.created_at.isoformat(),
        }
    explain_cards = [
        {
            "key": "engagement",
            "label": "学习投入",
            "score": round(float(snapshot.engagement), 4),
            "score_label": _label_from_score(float(snapshot.engagement)),
            "explain": "主要来自登录频率、学习时长、资源完成度和连续学习情况。",
        },
        {
            "key": "achievement",
            "label": "学习成效",
            "score": round(float(snapshot.achievement), 4),
            "score_label": _label_from_score(float(snapshot.achievement)),
            "explain": "主要来自练习正确率、小测结果以及掌握度增长。",
        },
        {
            "key": "course_mastery",
            "label": "课程掌握",
            "score": round(float(snapshot.course_mastery), 4),
            "score_label": _label_from_score(float(snapshot.course_mastery)),
            "explain": "反映当前课程知识点整体掌握水平，是动态评价的重要基础项。",
        },
        {
            "key": "graph_score",
            "label": "知识图谱融合",
            "score": round(float(graph_coverage.get("graph_score", 0.0)), 4),
            "score_label": _label_from_score(float(graph_coverage.get("graph_score", 0.0))),
            "explain": (
                f"已通过终点知识点“{dict(graph_coverage.get('terminal_mastered') or {}).get('title', '终点')}”，"
                "图谱评价按课程达标计算，并以 20% 权重融入动态评价；未学习分支仍可作为拓展或补弱建议。"
                if graph_coverage.get("completion_rule") == "terminal_mastery"
                else (
                    f"已完成 {int(graph_coverage.get('completed_nodes', 0))}/{int(graph_coverage.get('total_nodes', 0))} 个图谱节点，"
                    f"已掌握 {int(graph_coverage.get('mastered_nodes', 0))}/{int(graph_coverage.get('total_nodes', 0))} 个节点；"
                    "图谱评价分按学习覆盖度 60% + 掌握覆盖度 40% 计算，并以 20% 权重融入动态评价。"
                )
            ),
        },
        {
            "key": "risk",
            "label": "风险信号",
            "score": round(float(snapshot.risk), 4),
            "score_label": "关注" if float(snapshot.risk) >= 0.48 else "可控",
            "explain": "主要观察拖延、错误连续出现、学习中断等风险迹象。",
        },
    ]
    next_actions: list[str] = []
    if feedback is not None and feedback.comment.strip():
        next_actions.append(f"教师建议：{feedback.comment.strip()}")
    if latest_recommendation_payload.get("target_kp_title"):
        next_actions.append(
            f"优先处理推荐知识点“{latest_recommendation_payload['target_kp_title']}”，原因：{latest_recommendation_payload.get('reason_summary') or '当前为系统推荐目标'}"
        )
    if weak_points:
        weak_titles = [kp.title for kp in kps if kp.id is not None and int(kp.id) in set(weak_points[:3])]
        if weak_titles:
            next_actions.append("先补薄弱知识点：" + "、".join(weak_titles))
    if not next_actions:
        next_actions.append("当前结果较稳定，建议继续按课程阶段推进并保持练习频率。")
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
        current_stage_title=current_stage.stage_title if current_stage is not None else None,
        current_trend_label=current_stage.trend_label if current_stage is not None else None,
        summary=(
            current_stage.reason_summary
            if current_stage is not None and current_stage.reason_summary
            else snapshot.reason_summary
        ),
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
        learning_behavior_overview={
            "window_days": {"recent": 14, "history": 30},
            "login_count_30d": len(login_rows_30d),
            "login_days_30d": len(login_days_30d),
            "active_days_14d": len(active_days_14d),
            "consecutive_days_14d": int(consecutive_days_14d),
            "study_duration_seconds_14d": round(float(study_seconds_14d), 2),
            "study_duration_minutes_14d": round(float(study_seconds_14d) / 60.0, 2),
            "video_started_30d": len([row for row in video_rows_30d if float(row.watched_seconds or 0.0) > 0]),
            "video_completed_30d": len([row for row in video_rows_30d if bool(row.completed)]),
            "avg_video_completion_30d": round(float(avg_video_completion_30d), 4),
            "practice_attempts_30d": len(practice_rows_30d),
            "practice_accuracy_30d": round(float(practice_accuracy_30d), 4),
            "recommendation_count_30d": len(recommendation_rows_30d),
            "top_event_types_30d": top_event_types_30d,
        },
        behavior_timeline=[
            {
                "id": int(row.id),
                "event_type": row.event_type,
                "kp_id": row.kp_id,
                "value_json": row.value_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in behavior_rows_30d[:60]
            if row.id is not None
        ],
        recent_practice_records=[
            {
                "id": int(row.id),
                "kp_id": row.kp_id,
                "question_id": row.question_id,
                "correct": bool(row.correct),
                "duration_ms": row.duration_ms,
                "created_at": row.created_at.isoformat(),
            }
            for row in practice_rows_30d[:40]
            if row.id is not None
        ],
        recent_quiz_records=[
            {
                "id": int(row.id),
                "kp_id": row.kp_id,
                "score": float(row.score),
                "passed": bool(row.passed),
                "duration_ms": row.duration_ms,
                "created_at": row.created_at.isoformat(),
            }
            for row in quiz_rows_30d[:30]
            if row.id is not None
        ],
        recent_video_records=[
            {
                "id": int(row.id),
                "kp_id": row.kp_id,
                "resource_id": row.resource_id,
                "watched_seconds": float(row.watched_seconds),
                "duration_seconds": float(row.duration_seconds),
                "completed": bool(row.completed),
                "updated_at": row.updated_at.isoformat(),
            }
            for row in video_rows_30d[:30]
            if row.id is not None
        ],
        latest_recommendation=latest_recommendation_payload,
        graph_coverage=graph_coverage,
        evaluation_explain={
            "summary": (
                current_stage.reason_summary
                if current_stage is not None and current_stage.reason_summary
                else snapshot.reason_summary
            ),
            "current_stage_title": current_stage.stage_title if current_stage is not None else "",
            "current_trend_label": current_stage.trend_label if current_stage is not None else "",
            "explain_cards": explain_cards,
            "next_actions": next_actions[:4],
            "teacher_feedback": feedback.comment if feedback is not None else "",
            "term_reason_summary": str((portrait_summary.get("term_summary") or {}).get("final_reason_summary") or ""),
        },
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
