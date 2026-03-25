from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, desc, select

from app.db.models import (
    Course,
    CoursePortraitIndicatorSelection,
    CourseStage,
    KnowledgePoint,
    LearnerPersonaOverride,
    LearnerPersonaRule,
    LearnerProfileSnapshot,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    PersonaType,
    PortraitDimension,
    PortraitIndicator,
    PracticeAttempt,
    QuestionnairePortraitIndicatorInput,
    QuizAttempt,
    ReviewSchedule,
    ResourceType,
    StageEvaluationSnapshot,
    StageImportRecord,
    StageMetricType,
    StageTeacherFeedback,
    TeacherPortraitIndicatorInput,
    User,
    UserRole,
    VideoProgress,
)
from app.services.practice import practice_status


PERSONA_LABELS = {
    PersonaType.smart: "聪明能干型",
    PersonaType.diligent: "踏实学习型",
    PersonaType.struggling: "困难坚持型",
    PersonaType.procrastinating: "拖延风险型",
    PersonaType.steady: "平稳发展型",
}

DEFAULT_PERSONA_THRESHOLDS: dict[str, float] = {
    "procrastinating_e": 0.4,
    "smart_a": 0.75,
    "smart_f": 0.75,
    "diligent_e": 0.75,
    "diligent_a": 0.6,
    "struggling_e": 0.6,
    "struggling_a": 0.6,
}

DEFAULT_PERSONA_WEIGHTS: dict[str, Any] = {
    "engagement": {"learning_frequency": 0.35, "study_duration": 0.35, "resource_completion": 0.2, "streak": 0.1},
    "achievement": {"practice_accuracy": 0.5, "quiz_accuracy": 0.3, "mastery_growth": 0.2},
    "efficiency": {"unit_time_accuracy": 0.6, "task_completion": 0.4},
    "risk": {"overdue_rate": 0.4, "wrong_streak": 0.3, "abandonment_rate": 0.3},
    "dynamic": {"engagement": 0.25, "achievement": 0.3, "course_mastery": 0.35, "stability": 0.1},
    "stage_dimensions": {
        "engagement": {
            "enabled": True,
            "weight": 0.3,
            "metrics": {
                "activity_frequency": 0.25,
                "study_duration": 0.35,
                "completion": 0.25,
                "attendance_participation": 0.15,
            },
        },
        "achievement": {
            "enabled": True,
            "weight": 0.35,
            "metrics": {
                "assignment_score": 0.35,
                "quiz_score": 0.35,
                "task_score": 0.15,
                "stage_mastery": 0.15,
            },
        },
        "habit": {
            "enabled": True,
            "weight": 0.2,
            "metrics": {
                "on_time_rate": 0.4,
                "attendance_rate": 0.35,
                "continuity": 0.25,
            },
        },
        "characteristic": {
            "enabled": True,
            "weight": 0.15,
            "metrics": {
                "participation": 0.35,
                "task_completion": 0.35,
                "resource_initiative": 0.3,
            },
        },
    },
}

DIMENSION_LEGACY_LABELS = {
    "potential_trait": "潜能与特质倾向",
    "social_emotional": "情感与社会性发展",
    "knowledge_cognition": "知识与认知状态",
    "learning_behavior": "学习行为与过程",
    "individual_background": "个体基础特征",
}

METRIC_LABELS = {
    "activity_frequency": "阶段活跃天数",
    "study_duration": "阶段学习时长",
    "completion": "阶段完成度",
    "attendance_rate": "阶段出勤率",
    "participation": "课堂参与度",
    "assignment_score": "作业成绩",
    "quiz_score": "小测成绩",
    "task_score": "任务成绩",
    "stage_mastery": "知识掌握度",
    "on_time_rate": "按时提交率",
    "continuity": "连续学习情况",
    "task_completion": "任务完成率",
    "resource_initiative": "资源主动使用度",
    "engagement_base": "学习投入基线",
    "achievement_base": "学习成效基线",
    "habit_base": "学习习惯基线",
    "characteristic_base": "学习特征基线",
}

INDICATOR_RULES: dict[str, dict[str, Any]] = {
    "creative_thinking": {
        "source_detail": "教师补充评分优先；没有教师评分时，根据任务完成、资源主动使用和课堂参与综合估算。",
        "formula_text": "0.45*任务完成率 + 0.30*资源主动使用度 + 0.25*课堂参与度",
        "metrics": ["task_completion", "resource_initiative", "participation"],
        "weights": {"task_completion": 0.45, "resource_initiative": 0.30, "participation": 0.25},
    },
    "cross_context_transfer": {
        "source_detail": "优先依据阶段导入的综合任务与小测，再结合知识掌握度判断迁移能力。",
        "formula_text": "0.40*任务成绩 + 0.30*小测成绩 + 0.30*知识掌握度",
        "metrics": ["task_score", "quiz_score", "stage_mastery"],
        "weights": {"task_score": 0.40, "quiz_score": 0.30, "stage_mastery": 0.30},
    },
    "value_judgement": {
        "source_detail": "需要老师结合反思作业、课堂表现进行补充评分，系统暂不自动估算。",
        "formula_text": "教师补充评分",
        "metrics": [],
        "weights": {},
    },
    "collaboration": {
        "source_detail": "主要通过阶段参与度、任务协作完成情况和出勤表现综合判断。",
        "formula_text": "0.45*课堂参与度 + 0.30*任务完成率 + 0.25*出勤率",
        "metrics": ["participation", "task_completion", "attendance_rate"],
        "weights": {"participation": 0.45, "task_completion": 0.30, "attendance_rate": 0.25},
    },
    "motivation": {
        "source_detail": "优先依据阶段导入数据，观察学生持续投入、完成情况和连续学习状态。",
        "formula_text": "0.45*学习投入基线 + 0.35*阶段完成度 + 0.20*连续学习情况",
        "metrics": ["engagement_base", "completion", "continuity"],
        "weights": {"engagement_base": 0.45, "completion": 0.35, "continuity": 0.20},
    },
    "self_regulation": {
        "source_detail": "通过是否按时提交、是否持续学习以及是否主动使用资源来估算自我调节能力。",
        "formula_text": "0.40*按时提交率 + 0.35*连续学习情况 + 0.25*资源主动使用度",
        "metrics": ["on_time_rate", "continuity", "resource_initiative"],
        "weights": {"on_time_rate": 0.40, "continuity": 0.35, "resource_initiative": 0.25},
    },
    "cross_discipline_link": {
        "source_detail": "结合知识图谱掌握度和资源延伸使用情况，判断跨学科连接能力。",
        "formula_text": "0.55*知识掌握度 + 0.45*资源主动使用度",
        "metrics": ["stage_mastery", "resource_initiative"],
        "weights": {"stage_mastery": 0.55, "resource_initiative": 0.45},
    },
    "discipline_level": {
        "source_detail": "根据阶段成效基线和知识掌握度，判断本学科能力层级。",
        "formula_text": "0.60*学习成效基线 + 0.40*知识掌握度",
        "metrics": ["achievement_base", "stage_mastery"],
        "weights": {"achievement_base": 0.60, "stage_mastery": 0.40},
    },
    "language_mastery": {
        "source_detail": "主要看作业与小测中的表达、理解类表现。",
        "formula_text": "0.65*作业成绩 + 0.35*小测成绩",
        "metrics": ["assignment_score", "quiz_score"],
        "weights": {"assignment_score": 0.65, "quiz_score": 0.35},
    },
    "logic_mastery": {
        "source_detail": "主要看小测与任务中的推理、结构化解题表现。",
        "formula_text": "0.65*小测成绩 + 0.35*任务成绩",
        "metrics": ["quiz_score", "task_score"],
        "weights": {"quiz_score": 0.65, "task_score": 0.35},
    },
    "resource_preference": {
        "source_detail": "根据资源使用情况与学习时长，判断资源偏好是否稳定。",
        "formula_text": "0.55*阶段完成度 + 0.45*阶段学习时长",
        "metrics": ["completion", "study_duration"],
        "weights": {"completion": 0.55, "study_duration": 0.45},
    },
    "strategy_preference": {
        "source_detail": "通过任务推进、资源使用和按时完成情况判断学习策略。",
        "formula_text": "0.50*任务完成率 + 0.25*资源主动使用度 + 0.25*按时提交率",
        "metrics": ["task_completion", "resource_initiative", "on_time_rate"],
        "weights": {"task_completion": 0.50, "resource_initiative": 0.25, "on_time_rate": 0.25},
    },
    "text_discussion_interaction": {
        "source_detail": "通过课堂参与与文本作业表现判断讨论/文本型互动倾向。",
        "formula_text": "0.50*课堂参与度 + 0.50*作业成绩",
        "metrics": ["participation", "assignment_score"],
        "weights": {"participation": 0.50, "assignment_score": 0.50},
    },
    "practice_experience_interaction": {
        "source_detail": "通过任务成绩与任务完成率判断实践/体验型互动倾向。",
        "formula_text": "0.55*任务成绩 + 0.45*任务完成率",
        "metrics": ["task_score", "task_completion"],
        "weights": {"task_score": 0.55, "task_completion": 0.45},
    },
    "academic_background": {
        "source_detail": "通过问卷/基础资料补充，不参与阶段自动估算。",
        "formula_text": "学生补充或教师补充",
        "metrics": [],
        "weights": {},
    },
    "interest_type": {
        "source_detail": "通过问卷或标签补充，不参与阶段自动估算。",
        "formula_text": "学生补充或教师补充",
        "metrics": [],
        "weights": {},
    },
    "intelligence_advantage": {
        "source_detail": "通过问卷和教师观察综合补充，不参与阶段自动估算。",
        "formula_text": "学生补充 + 教师观察",
        "metrics": [],
        "weights": {},
    },
}


def _aggregate_stage_portrait_summary(
    history: list[StageEvaluationSnapshot],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not history:
        return [], [], {"stage_count": 0, "progress_stages": 0, "steady_stages": 0, "regress_stages": 0, "final_score_reference": 0.0}

    dimension_bucket: dict[str, list[float]] = {}
    indicator_bucket: dict[str, dict[str, Any]] = {}
    trend_counter = Counter((item.trend_label or "持平") for item in history)
    scores = [float(item.dynamic_score or 0.0) for item in history]

    for item in history:
        dimension_rows = _json_load(item.dimension_summary_json, {}).get("portrait_dimensions", [])
        for row in dimension_rows:
            title = str(row.get("dimension_title") or "").strip()
            score = row.get("score")
            available = bool(row.get("available"))
            if not title or not available or score is None:
                continue
            dimension_bucket.setdefault(title, []).append(float(score))

        indicator_rows = _json_load(item.indicator_summary_json, {}).get("portrait_indicators", [])
        for row in indicator_rows:
            title = str(row.get("title") or "").strip()
            score = row.get("score")
            available = bool(row.get("available"))
            if not title or not available or score is None:
                continue
            item_bucket = indicator_bucket.setdefault(
                title,
                {
                    "title": title,
                    "scores": [],
                    "source_type": row.get("source_type", "auto"),
                    "weight": float(row.get("weight") or 0.0),
                    "score_source": row.get("score_source"),
                    "formula_text": row.get("formula_text"),
                    "source_detail": row.get("source_detail"),
                },
            )
            item_bucket["scores"].append(float(score))

    final_dimensions = [
        {
            "dimension_title": title,
            "score": _clamp01(mean(values)) if values else None,
            "available": bool(values),
        }
        for title, values in dimension_bucket.items()
    ]
    final_dimensions.sort(key=lambda item: item["dimension_title"])

    final_indicators = []
    for _, payload in indicator_bucket.items():
        scores_list = payload.pop("scores", [])
        final_indicators.append(
            {
                **payload,
                "score": _clamp01(mean(scores_list)) if scores_list else None,
                "available": bool(scores_list),
            }
        )
    final_indicators.sort(key=lambda item: item["title"])

    latest_score = scores[-1] if scores else 0.0
    avg_score = mean(scores) if scores else 0.0
    final_score_reference = _clamp01(0.6 * avg_score + 0.4 * latest_score)
    term_summary = {
        "stage_count": len(history),
        "progress_stages": int(trend_counter.get("进步", 0)),
        "steady_stages": int(trend_counter.get("持平", 0)),
        "regress_stages": int(trend_counter.get("退步", 0)),
        "avg_dynamic_score": _clamp01(avg_score),
        "latest_dynamic_score": _clamp01(latest_score),
        "final_score_reference": final_score_reference,
    }
    return final_dimensions, final_indicators, term_summary


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _json_load(raw: str | None, default: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return default
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else default
    except Exception:
        return default


def parse_kp_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = [
        item.strip()
        for item in str(raw)
        .replace("；", ",")
        .replace(";", ",")
        .replace("、", ",")
        .replace("/", ",")
        .replace("\n", ",")
        .split(",")
    ]
    result: list[str] = []
    for item in parts:
        if item and item not in result:
            result.append(item)
    return result


def build_kp_dimension_summary(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    kps: list[KnowledgePoint] | None = None,
    mastery_map: dict[int, Mastery] | None = None,
) -> dict[str, Any]:
    kp_rows = list(kps or session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all())
    kp_ids = [int(kp.id) for kp in kp_rows if kp.id is not None]
    if not kp_ids:
        return {
            "summary": {
                "knowledge_total": 0,
                "knowledge_achieved": 0,
                "ability_target_total": 0,
                "ability_achieved": 0,
                "literacy_target_total": 0,
                "literacy_achieved": 0,
                "top_abilities": [],
                "top_literacies": [],
            },
            "by_kp": {},
        }

    if mastery_map is None:
        mastery_rows = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id.in_(kp_ids))).all()
        mastery_map = {int(item.kp_id): item for item in mastery_rows}
    else:
        mastery_map = {int(key): value for key, value in mastery_map.items()}

    practice_rows = session.exec(
        select(PracticeAttempt).where(PracticeAttempt.user_id == user_id, PracticeAttempt.kp_id.in_(kp_ids))
    ).all()
    quiz_rows = session.exec(
        select(QuizAttempt).where(QuizAttempt.user_id == user_id, QuizAttempt.kp_id.in_(kp_ids))
    ).all()
    video_rows = session.exec(
        select(VideoProgress).where(VideoProgress.user_id == user_id, VideoProgress.kp_id.in_(kp_ids))
    ).all()
    behavior_rows = session.exec(
        select(LearningBehaviorEvent).where(
            LearningBehaviorEvent.user_id == user_id,
            LearningBehaviorEvent.kp_id.in_(kp_ids),
        )
    ).all()

    practice_bucket: dict[int, dict[str, float]] = {}
    for row in practice_rows:
        item = practice_bucket.setdefault(int(row.kp_id), {"total": 0.0, "correct": 0.0})
        item["total"] += 1
        if row.correct:
            item["correct"] += 1

    quiz_bucket: dict[int, dict[str, float]] = {}
    for row in quiz_rows:
        item = quiz_bucket.setdefault(int(row.kp_id), {"total": 0.0, "passed": 0.0, "best_score": 0.0})
        item["total"] += 1
        if row.passed:
            item["passed"] += 1
        item["best_score"] = max(float(item["best_score"]), float(row.score or 0.0))

    video_bucket: dict[int, dict[str, float]] = {}
    for row in video_rows:
        item = video_bucket.setdefault(
            int(row.kp_id),
            {"started": 0.0, "completed": 0.0, "watched_seconds": 0.0},
        )
        item["started"] += 1
        item["watched_seconds"] += max(0.0, float(row.watched_seconds or 0.0))
        if row.completed:
            item["completed"] += 1

    behavior_bucket: dict[int, dict[str, float]] = {}
    for row in behavior_rows:
        item = behavior_bucket.setdefault(int(row.kp_id), {"resource_visits": 0.0, "resource_downloads": 0.0})
        if row.event_type == "resource_visit":
            item["resource_visits"] += 1
        elif row.event_type == "resource_download":
            item["resource_downloads"] += 1

    ability_counter: Counter[str] = Counter()
    ability_target_counter: Counter[str] = Counter()
    literacy_counter: Counter[str] = Counter()
    literacy_target_counter: Counter[str] = Counter()
    by_kp: dict[int, dict[str, Any]] = {}
    knowledge_achieved = 0
    ability_target_total = 0
    ability_achieved = 0
    literacy_target_total = 0
    literacy_achieved = 0

    for kp in kp_rows:
        if kp.id is None:
            continue
        kp_id = int(kp.id)
        mastery = mastery_map.get(kp_id)
        mastery_value = float(mastery.value) if mastery is not None else 0.0
        practice_info = practice_bucket.get(kp_id, {"total": 0.0, "correct": 0.0})
        quiz_info = quiz_bucket.get(kp_id, {"total": 0.0, "passed": 0.0, "best_score": 0.0})
        video_info = video_bucket.get(kp_id, {"started": 0.0, "completed": 0.0, "watched_seconds": 0.0})
        behavior_info = behavior_bucket.get(kp_id, {"resource_visits": 0.0, "resource_downloads": 0.0})

        has_learning_evidence = any(
            float(value) > 0
            for value in (
                practice_info["total"],
                quiz_info["total"],
                video_info["started"],
                behavior_info["resource_visits"],
                behavior_info["resource_downloads"],
            )
        )

        knowledge_status = "achieved" if mastery_value >= 0.6 else "in_progress" if mastery_value >= 0.2 or has_learning_evidence else "not_started"
        if knowledge_status == "achieved":
            knowledge_achieved += 1

        ability_labels = parse_kp_tags(kp.ability_tag)
        ability_enabled = bool(ability_labels)
        for label in ability_labels:
            ability_target_counter[label] += 1
        if ability_enabled:
            ability_target_total += 1
        ability_evidence_score = 0
        if mastery_value >= 0.7:
            ability_evidence_score += 1
        if float(practice_info["correct"]) >= 1:
            ability_evidence_score += 1
        if float(quiz_info["passed"]) >= 1 or float(quiz_info["best_score"]) >= 0.6:
            ability_evidence_score += 1
        if not ability_enabled:
            ability_status = "not_started"
        elif mastery_value >= 0.6 and ability_evidence_score >= 2:
            ability_status = "achieved"
        elif mastery_value >= 0.35 or has_learning_evidence:
            ability_status = "in_progress"
        else:
            ability_status = "not_started"
        if ability_status == "achieved":
            ability_achieved += 1
            for label in ability_labels:
                ability_counter[label] += 1

        literacy_labels = parse_kp_tags(kp.literacy_tag)
        literacy_enabled = bool(literacy_labels)
        for label in literacy_labels:
            literacy_target_counter[label] += 1
        if literacy_enabled:
            literacy_target_total += 1
        literacy_evidence_score = 0
        if float(behavior_info["resource_visits"]) >= 1 or float(behavior_info["resource_downloads"]) >= 1:
            literacy_evidence_score += 1
        if float(video_info["watched_seconds"]) >= 120 or float(video_info["completed"]) >= 1:
            literacy_evidence_score += 1
        if float(behavior_info["resource_visits"]) + float(video_info["started"]) >= 2:
            literacy_evidence_score += 1
        if not literacy_enabled:
            literacy_status = "not_started"
        elif literacy_evidence_score >= 2:
            literacy_status = "achieved"
        elif literacy_evidence_score >= 1:
            literacy_status = "in_progress"
        else:
            literacy_status = "not_started"
        if literacy_status == "achieved":
            literacy_achieved += 1
            for label in literacy_labels:
                literacy_counter[label] += 1

        by_kp[kp_id] = {
            "knowledge_enabled": True,
            "ability_enabled": ability_enabled,
            "literacy_enabled": literacy_enabled,
            "knowledge_label": (kp.knowledge_tag or kp.title or "知识掌握").strip(),
            "ability_labels": ability_labels,
            "literacy_labels": literacy_labels,
            "knowledge_status": knowledge_status,
            "ability_status": ability_status,
            "literacy_status": literacy_status,
            "evidence": {
                "mastery": round(mastery_value, 4),
                "practice_total": int(practice_info["total"]),
                "practice_correct": int(practice_info["correct"]),
                "quiz_total": int(quiz_info["total"]),
                "quiz_passed": int(quiz_info["passed"]),
                "video_started": int(video_info["started"]),
                "video_completed": int(video_info["completed"]),
                "watched_seconds": round(float(video_info["watched_seconds"]), 2),
                "resource_visits": int(behavior_info["resource_visits"]),
                "resource_downloads": int(behavior_info["resource_downloads"]),
            },
        }

    def _to_ranked_rows(counter: Counter[str], target_counter: Counter[str]) -> list[dict[str, Any]]:
        rows = []
        for label, target_count in target_counter.items():
            rows.append(
                {
                    "label": label,
                    "achieved_count": int(counter.get(label, 0)),
                    "target_count": int(target_count),
                }
            )
        rows.sort(key=lambda item: (-item["achieved_count"], -item["target_count"], item["label"]))
        return rows[:8]

    return {
        "summary": {
            "knowledge_total": len(kp_rows),
            "knowledge_achieved": knowledge_achieved,
            "ability_target_total": ability_target_total,
            "ability_achieved": ability_achieved,
            "literacy_target_total": literacy_target_total,
            "literacy_achieved": literacy_achieved,
            "top_abilities": _to_ranked_rows(ability_counter, ability_target_counter),
            "top_literacies": _to_ranked_rows(literacy_counter, literacy_target_counter),
        },
        "by_kp": by_kp,
    }


def _safe_ratio(value: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return _clamp01(float(value) / float(base))


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, value in base.items():
        if isinstance(value, dict):
            merged[key] = _deep_merge_dict(value, override.get(key, {}) if isinstance(override.get(key), dict) else {})
        else:
            merged[key] = value
    for key, value in override.items():
        if key not in merged:
            merged[key] = value
    return merged


def resolve_persona_thresholds(rule: LearnerPersonaRule) -> dict[str, Any]:
    return _deep_merge_dict(DEFAULT_PERSONA_THRESHOLDS, _json_load(rule.thresholds_json, {}))


def resolve_persona_weights(rule: LearnerPersonaRule) -> dict[str, Any]:
    return _deep_merge_dict(DEFAULT_PERSONA_WEIGHTS, _json_load(rule.weights_json, {}))


def persona_label(persona_type: PersonaType | str | None) -> str:
    if persona_type is None:
        return PERSONA_LABELS[PersonaType.steady]
    try:
        enum_value = persona_type if isinstance(persona_type, PersonaType) else PersonaType(str(persona_type))
    except Exception:
        return str(persona_type)
    return PERSONA_LABELS.get(enum_value, enum_value.value)


def get_or_create_persona_rule(session: Session, *, subject: str, grade: str) -> LearnerPersonaRule:
    rule = session.exec(
        select(LearnerPersonaRule).where(LearnerPersonaRule.subject == subject, LearnerPersonaRule.grade == grade)
    ).first()
    if rule is None:
        rule = LearnerPersonaRule(subject=subject, grade=grade)
        session.add(rule)
        session.commit()
        session.refresh(rule)
    return rule


def get_latest_profile_snapshot(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
) -> LearnerProfileSnapshot | None:
    return session.exec(
        select(LearnerProfileSnapshot)
        .where(
            LearnerProfileSnapshot.user_id == user_id,
            LearnerProfileSnapshot.subject == subject,
            LearnerProfileSnapshot.grade == grade,
        )
        .order_by(desc(LearnerProfileSnapshot.updated_at), desc(LearnerProfileSnapshot.id))
        .limit(1)
    ).first()


def get_profile_trend(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    limit: int = 8,
) -> list[LearnerProfileSnapshot]:
    rows = session.exec(
        select(LearnerProfileSnapshot)
        .where(
            LearnerProfileSnapshot.user_id == user_id,
            LearnerProfileSnapshot.subject == subject,
            LearnerProfileSnapshot.grade == grade,
        )
        .order_by(desc(LearnerProfileSnapshot.updated_at), desc(LearnerProfileSnapshot.id))
        .limit(max(1, limit))
    ).all()
    return list(rows)


def get_stage_snapshot_trend(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    limit: int = 8,
) -> list[StageEvaluationSnapshot]:
    rows = session.exec(
        select(StageEvaluationSnapshot)
        .where(
            StageEvaluationSnapshot.user_id == user_id,
            StageEvaluationSnapshot.subject == subject,
            StageEvaluationSnapshot.grade == grade,
        )
        .order_by(desc(StageEvaluationSnapshot.stage_order), desc(StageEvaluationSnapshot.updated_at))
        .limit(max(1, limit))
    ).all()
    return list(rows)


def get_latest_stage_snapshot(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
) -> StageEvaluationSnapshot | None:
    return session.exec(
        select(StageEvaluationSnapshot)
        .where(
            StageEvaluationSnapshot.user_id == user_id,
            StageEvaluationSnapshot.subject == subject,
            StageEvaluationSnapshot.grade == grade,
        )
        .order_by(desc(StageEvaluationSnapshot.stage_order), desc(StageEvaluationSnapshot.updated_at))
        .limit(1)
    ).first()


def get_stage_teacher_feedback(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    stage_id: int | None = None,
) -> StageTeacherFeedback | None:
    stmt = select(StageTeacherFeedback).where(
        StageTeacherFeedback.user_id == user_id,
        StageTeacherFeedback.subject == subject,
        StageTeacherFeedback.grade == grade,
    )
    if stage_id is not None:
        stmt = stmt.where(StageTeacherFeedback.stage_id == stage_id)
    return session.exec(stmt.order_by(desc(StageTeacherFeedback.updated_at))).first()


def _normalize_metric_score(value: float) -> float:
    score = float(value or 0.0)
    if score > 1.0 and score <= 100.0:
        score = score / 100.0
    return _clamp01(score)


def _mean_or_default(values: list[float], default: float = 0.0) -> float:
    cleaned = [float(item) for item in values if item is not None]
    return float(mean(cleaned)) if cleaned else float(default)


def _metric_type_name(value: StageMetricType | str) -> str:
    return value.value if isinstance(value, StageMetricType) else str(value)


def _coerce_bool_like(value: bool | None) -> float:
    return 1.0 if bool(value) else 0.0


def _course_indicator_rows(session: Session, *, course_id: int) -> list[dict[str, Any]]:
    selections = session.exec(
        select(CoursePortraitIndicatorSelection).where(
            CoursePortraitIndicatorSelection.course_id == course_id,
            CoursePortraitIndicatorSelection.enabled == True,  # noqa: E712
        )
    ).all()
    rows: list[dict[str, Any]] = []
    for selection in selections:
        indicator = session.get(PortraitIndicator, selection.indicator_id)
        if indicator is None or not indicator.active:
            continue
        dimension = session.get(PortraitDimension, selection.dimension_id)
        if dimension is None or not dimension.active:
            continue
        rows.append(
            {
                "selection": selection,
                "indicator": indicator,
                "dimension": dimension,
                "weight": float(selection.weight or indicator.default_weight or 1.0),
            }
        )
    return rows


def _infer_indicator_score(code: str, *, metrics: dict[str, float]) -> float | None:
    rules = INDICATOR_RULES.get(code)
    if not rules:
        return None
    metric_weights = rules.get("weights", {})
    if not metric_weights:
        return None
    return _clamp01(sum(float(metric_weights.get(name, 0.0)) * float(metrics.get(name, 0.0)) for name in metric_weights))


def _indicator_rule_payload(code: str, metrics: dict[str, float]) -> dict[str, Any]:
    rule = INDICATOR_RULES.get(code, {})
    metric_names = list(rule.get("metrics", []))
    evidence_rows = [
        {
            "metric_key": metric_name,
            "metric_label": METRIC_LABELS.get(metric_name, metric_name),
            "metric_value": round(float(metrics.get(metric_name, 0.0)), 4),
            "metric_percent": round(float(metrics.get(metric_name, 0.0)) * 100, 1),
            "weight": float(rule.get("weights", {}).get(metric_name, 0.0)),
        }
        for metric_name in metric_names
    ]
    return {
        "formula_text": rule.get("formula_text", "系统按阶段规则自动估算"),
        "source_detail": rule.get("source_detail", "系统根据阶段数据和补充信息综合判断"),
        "evidence_metrics": evidence_rows,
    }


def _build_portrait_indicator_summary(
    session: Session,
    *,
    course_id: int,
    metrics: dict[str, float],
    user_id: int | None = None,
    stage_id: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    rows = _course_indicator_rows(session, course_id=course_id)
    if not rows:
        return [], [], {}

    teacher_inputs: dict[int, TeacherPortraitIndicatorInput] = {}
    questionnaire_inputs: dict[int, QuestionnairePortraitIndicatorInput] = {}
    if user_id is not None and stage_id is not None:
        teacher_rows = session.exec(
            select(TeacherPortraitIndicatorInput).where(
                TeacherPortraitIndicatorInput.user_id == user_id,
                TeacherPortraitIndicatorInput.stage_id == stage_id,
                TeacherPortraitIndicatorInput.course_id == course_id,
            )
        ).all()
        teacher_inputs = {int(row.indicator_id): row for row in teacher_rows}
    if user_id is not None:
        questionnaire_rows = session.exec(
            select(QuestionnairePortraitIndicatorInput).where(
                QuestionnairePortraitIndicatorInput.user_id == user_id,
                QuestionnairePortraitIndicatorInput.course_id == course_id,
            )
        ).all()
        questionnaire_inputs = {int(row.indicator_id): row for row in questionnaire_rows}

    dimension_bucket: dict[str, dict[str, Any]] = {}
    indicator_items: list[dict[str, Any]] = []
    for row in rows:
        indicator: PortraitIndicator = row["indicator"]
        dimension: PortraitDimension = row["dimension"]
        weight = float(row["weight"])
        teacher_input = teacher_inputs.get(int(indicator.id))
        questionnaire_input = questionnaire_inputs.get(int(indicator.id))
        if teacher_input is not None:
            score = _clamp01(float(teacher_input.score))
            score_source = "teacher_input"
        elif questionnaire_input is not None:
            score = _clamp01(float(questionnaire_input.score))
            score_source = "questionnaire_input"
        else:
            score = _infer_indicator_score(indicator.code, metrics=metrics)
            score_source = "stage_inference" if score is not None else "missing"
        rule_payload = _indicator_rule_payload(indicator.code, metrics)
        available = score is not None
        indicator_items.append(
            {
                "indicator_id": int(indicator.id),
                "dimension_id": int(dimension.id),
                "dimension_code": dimension.code,
                "dimension_title": dimension.title,
                "code": indicator.code,
                "title": indicator.title,
                "source_type": indicator.source_type.value if hasattr(indicator.source_type, "value") else str(indicator.source_type),
                "weight": weight,
                "available": available,
                "score": None if score is None else float(score),
                "note": teacher_input.note if teacher_input is not None else questionnaire_input.note if questionnaire_input is not None else "",
                "score_source": score_source,
                "formula_text": rule_payload["formula_text"],
                "source_detail": rule_payload["source_detail"],
                "evidence_metrics": rule_payload["evidence_metrics"],
            }
        )
        bucket = dimension_bucket.setdefault(
            dimension.code,
            {
                "dimension_id": int(dimension.id),
                "dimension_code": dimension.code,
                "dimension_title": dimension.title,
                "indicator_count": 0,
                "available_indicator_count": 0,
                "selection_weight": 0.0,
                "weight_total": 0.0,
                "weighted_score": 0.0,
            },
        )
        bucket["indicator_count"] += 1
        bucket["selection_weight"] += weight
        if available:
            bucket["available_indicator_count"] += 1
            bucket["weight_total"] += weight
            bucket["weighted_score"] += float(score) * weight

    dimension_items: list[dict[str, Any]] = []
    dimension_score_map: dict[str, float] = {}
    for code, bucket in dimension_bucket.items():
        available = bucket["weight_total"] > 0
        score = _clamp01(bucket["weighted_score"] / bucket["weight_total"]) if available else None
        if score is not None:
            dimension_score_map[code] = float(score)
        dimension_items.append(
            {
                "dimension_id": bucket["dimension_id"],
                "dimension_code": code,
                "dimension_title": bucket["dimension_title"],
                "available": available,
                "score": None if score is None else float(score),
                "indicator_count": bucket["indicator_count"],
                "available_indicator_count": bucket["available_indicator_count"],
                "selection_weight": float(bucket["selection_weight"]),
            }
        )
    dimension_items.sort(key=lambda item: item["dimension_id"])
    return dimension_items, indicator_items, dimension_score_map


def _stage_consecutive_days(days: list[date]) -> int:
    if not days:
        return 0
    ordered = sorted(set(days))
    streak = 1
    best = 1
    for idx in range(1, len(ordered)):
        if (ordered[idx] - ordered[idx - 1]).days == 1:
            streak += 1
            best = max(best, streak)
        else:
            streak = 1
    return best


def upsert_stage_teacher_feedback(
    session: Session,
    *,
    user_id: int,
    stage_id: int,
    subject: str,
    grade: str,
    course_id: int,
    feedback_tag: str,
    comment: str,
    updated_by: str,
) -> StageTeacherFeedback:
    row = session.exec(
        select(StageTeacherFeedback).where(
            StageTeacherFeedback.user_id == user_id,
            StageTeacherFeedback.stage_id == stage_id,
        )
    ).first()
    if row is None:
        row = StageTeacherFeedback(
            user_id=user_id,
            stage_id=stage_id,
            subject=subject,
            grade=grade,
            course_id=course_id,
        )
    row.feedback_tag = feedback_tag.strip()
    row.comment = comment.strip()
    row.updated_by = updated_by
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def recalculate_stage_snapshot(
    session: Session,
    *,
    user_id: int,
    stage_id: int,
    persist: bool = True,
) -> StageEvaluationSnapshot | None:
    stage = session.get(CourseStage, stage_id)
    if stage is None:
        return None

    records = session.exec(
        select(StageImportRecord)
        .where(StageImportRecord.user_id == user_id, StageImportRecord.stage_id == stage_id)
        .order_by(StageImportRecord.happened_at)
    ).all()
    if not records:
        return None

    rule = get_or_create_persona_rule(session, subject=stage.subject, grade=stage.grade)
    thresholds = resolve_persona_thresholds(rule)
    weights = resolve_persona_weights(rule)
    stage_dimensions = weights.get("stage_dimensions", {})

    metric_types = {_metric_type_name(row.metric_type) for row in records}
    days = [row.happened_at.date() for row in records if row.happened_at]
    activity_frequency = _clamp01(len(set(days)) / 6.0)
    study_duration = _clamp01(sum(max(0.0, float(row.duration_minutes or 0.0)) for row in records) / 240.0)
    completion = _mean_or_default([_clamp01(row.completion_value) for row in records], default=0.0)

    attendance_rows = [row for row in records if _metric_type_name(row.metric_type) == StageMetricType.attendance.value]
    attendance_rate = _mean_or_default(
        [max(_clamp01(row.attendance_value), 1.0 if (row.status or "").strip().lower() in {"present", "attended", "on_time"} else 0.0) for row in attendance_rows],
        default=0.0,
    )

    participation_rows = [row for row in records if _metric_type_name(row.metric_type) == StageMetricType.participation.value]
    participation = _mean_or_default(
        [
            max(
                _normalize_metric_score(row.score_value),
                _clamp01(row.completion_value),
                1.0 if (row.status or "").strip().lower() in {"active", "positive", "engaged"} else 0.0,
            )
            for row in participation_rows
        ],
        default=0.0,
    )

    engagement_cfg = stage_dimensions.get("engagement", {})
    achievement_cfg = stage_dimensions.get("achievement", {})
    habit_cfg = stage_dimensions.get("habit", {})
    characteristic_cfg = stage_dimensions.get("characteristic", {})

    engagement_metrics = engagement_cfg.get("metrics", {})
    achievement_metrics = achievement_cfg.get("metrics", {})
    habit_metrics = habit_cfg.get("metrics", {})
    characteristic_metrics = characteristic_cfg.get("metrics", {})

    engagement = _clamp01(
        float(engagement_metrics.get("activity_frequency", 0.25)) * activity_frequency
        + float(engagement_metrics.get("study_duration", 0.35)) * study_duration
        + float(engagement_metrics.get("completion", 0.25)) * completion
        + float(engagement_metrics.get("attendance_participation", 0.15)) * _mean_or_default([attendance_rate, participation], default=0.0)
    )

    assignment_rows = [row for row in records if _metric_type_name(row.metric_type) == StageMetricType.assignment.value]
    quiz_rows = [row for row in records if _metric_type_name(row.metric_type) == StageMetricType.quiz.value]
    task_rows = [row for row in records if _metric_type_name(row.metric_type) == StageMetricType.task.value]

    assignment_score = _mean_or_default([_normalize_metric_score(row.score_value) for row in assignment_rows], default=0.0)
    quiz_score = _mean_or_default([_normalize_metric_score(row.score_value) for row in quiz_rows], default=0.0)
    task_score = _mean_or_default([max(_normalize_metric_score(row.score_value), _clamp01(row.completion_value)) for row in task_rows], default=0.0)

    kp_ids = sorted({int(row.kp_id) for row in records if row.kp_id is not None})
    mastery_rows = []
    if kp_ids:
        mastery_rows = session.exec(
            select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id.in_(kp_ids))
        ).all()
    stage_mastery = _mean_or_default([float(row.value) for row in mastery_rows], default=max(assignment_score, quiz_score, task_score, completion))

    achievement = _clamp01(
        float(achievement_metrics.get("assignment_score", 0.35)) * assignment_score
        + float(achievement_metrics.get("quiz_score", 0.35)) * quiz_score
        + float(achievement_metrics.get("task_score", 0.15)) * task_score
        + float(achievement_metrics.get("stage_mastery", 0.15)) * stage_mastery
    )

    on_time_pool = [row for row in records if _metric_type_name(row.metric_type) in {StageMetricType.assignment.value, StageMetricType.quiz.value, StageMetricType.task.value}]
    on_time_rate = _mean_or_default([_coerce_bool_like(row.submitted_on_time) for row in on_time_pool], default=completion if on_time_pool else 0.0)
    continuity = _clamp01(_stage_consecutive_days(days) / 4.0)
    habit = _clamp01(
        float(habit_metrics.get("on_time_rate", 0.4)) * on_time_rate
        + float(habit_metrics.get("attendance_rate", 0.35)) * attendance_rate
        + float(habit_metrics.get("continuity", 0.25)) * continuity
    )

    task_completion = _mean_or_default([_clamp01(row.completion_value) for row in task_rows], default=completion if task_rows else 0.0)
    resource_initiative = _clamp01(len(metric_types) / 5.0)
    characteristic = _clamp01(
        float(characteristic_metrics.get("participation", 0.35)) * participation
        + float(characteristic_metrics.get("task_completion", 0.35)) * task_completion
        + float(characteristic_metrics.get("resource_initiative", 0.3)) * resource_initiative
    )

    portrait_metrics = {
        "activity_frequency": activity_frequency,
        "study_duration": study_duration,
        "completion": completion,
        "attendance_rate": attendance_rate,
        "participation": participation,
        "assignment_score": assignment_score,
        "quiz_score": quiz_score,
        "task_score": task_score,
        "stage_mastery": stage_mastery,
        "on_time_rate": on_time_rate,
        "continuity": continuity,
        "task_completion": task_completion,
        "resource_initiative": resource_initiative,
        "engagement_base": engagement,
        "achievement_base": achievement,
        "habit_base": habit,
        "characteristic_base": characteristic,
    }
    portrait_dimensions, portrait_indicators, portrait_dimension_scores = _build_portrait_indicator_summary(
        session,
        course_id=stage.course_id,
        metrics=portrait_metrics,
        user_id=user_id,
        stage_id=stage_id,
    )

    engagement = float(portrait_dimension_scores.get("learning_behavior", engagement))
    achievement = float(portrait_dimension_scores.get("knowledge_cognition", achievement))
    habit = float(portrait_dimension_scores.get("social_emotional", habit))
    characteristic_candidates = [
        value
        for value in (
            portrait_dimension_scores.get("potential_trait"),
            portrait_dimension_scores.get("individual_background"),
        )
        if value is not None
    ]
    if characteristic_candidates:
        characteristic = _mean_or_default([float(item) for item in characteristic_candidates], default=characteristic)

    efficiency = _clamp01(0.55 * habit + 0.45 * characteristic)
    risk = _clamp01(1.0 - (0.3 * engagement + 0.3 * achievement + 0.25 * habit + 0.15 * characteristic))

    enabled_weights: dict[str, float] = {}
    stage_dimension_values = {
        "engagement": engagement,
        "achievement": achievement,
        "habit": habit,
        "characteristic": characteristic,
    }
    for key, cfg in stage_dimensions.items():
        if bool(cfg.get("enabled", True)):
            enabled_weights[key] = max(0.0, float(cfg.get("weight", 0.0)))
    if not enabled_weights:
        enabled_weights = {"engagement": 0.3, "achievement": 0.35, "habit": 0.2, "characteristic": 0.15}
    weight_total = sum(enabled_weights.values()) or 1.0
    dynamic_score = _clamp01(
        sum(stage_dimension_values.get(key, 0.0) * (value / weight_total) for key, value in enabled_weights.items())
    )
    if portrait_dimensions:
        available_dimensions = [item for item in portrait_dimensions if item.get("available") and item.get("score") is not None]
        portrait_weight_total = sum(float(item.get("selection_weight", 0.0)) for item in available_dimensions) or 0.0
        if portrait_weight_total > 0:
            dynamic_score = _clamp01(
                sum(float(item.get("score", 0.0)) * (float(item.get("selection_weight", 0.0)) / portrait_weight_total) for item in available_dimensions)
            )

    previous = session.exec(
        select(StageEvaluationSnapshot)
        .where(
            StageEvaluationSnapshot.user_id == user_id,
            StageEvaluationSnapshot.subject == stage.subject,
            StageEvaluationSnapshot.grade == stage.grade,
            StageEvaluationSnapshot.stage_order < stage.stage_order,
        )
        .order_by(desc(StageEvaluationSnapshot.stage_order), desc(StageEvaluationSnapshot.updated_at))
        .limit(1)
    ).first()
    trend_label = "持平"
    if previous is not None:
        delta = float(dynamic_score) - float(previous.dynamic_score)
        if delta >= 0.05:
            trend_label = "进步"
        elif delta <= -0.05:
            trend_label = "退步"

    persona_type = _classify_persona(
        engagement=engagement,
        achievement=achievement,
        efficiency=efficiency,
        thresholds=thresholds,
    )
    override = session.exec(
        select(LearnerPersonaOverride).where(
            LearnerPersonaOverride.user_id == user_id,
            LearnerPersonaOverride.subject == stage.subject,
            LearnerPersonaOverride.grade == stage.grade,
        )
    ).first()
    if override is not None:
        persona_type = override.persona_type

    signals = [
        ("投入偏弱", engagement < 0.45),
        ("成效偏弱", achievement < 0.55),
        ("习惯待改进", habit < 0.5),
        ("风险偏高", risk >= 0.5),
    ]
    top_flags = [label for label, ok in signals if ok] or ["阶段表现稳定"]
    portrait_focus = [item["dimension_title"] for item in portrait_dimensions if item.get("available") and item.get("score", 0) >= 0.6][:2]
    focus_summary = f"；重点维度：{'、'.join(portrait_focus)}" if portrait_focus else ""
    reason_summary = f"{stage.title}：{persona_label(persona_type)}；主要判断：{'、'.join(top_flags[:2])}{focus_summary}"

    existing = session.exec(
        select(StageEvaluationSnapshot).where(
            StageEvaluationSnapshot.user_id == user_id,
            StageEvaluationSnapshot.stage_id == stage_id,
        )
    ).first()
    snapshot = existing or StageEvaluationSnapshot(
        user_id=user_id,
        course_id=stage.course_id,
        stage_id=stage_id,
        subject=stage.subject,
        grade=stage.grade,
    )
    snapshot.stage_title = stage.title
    snapshot.stage_order = stage.stage_order
    snapshot.persona_type = persona_type
    snapshot.engagement = engagement
    snapshot.achievement = achievement
    snapshot.habit = habit
    snapshot.characteristic = characteristic
    snapshot.efficiency = efficiency
    snapshot.risk = risk
    snapshot.course_mastery = stage_mastery
    snapshot.dynamic_score = dynamic_score
    snapshot.trend_label = trend_label
    snapshot.risk_level = _risk_level(dynamic_score)
    snapshot.reason_summary = reason_summary
    snapshot.dimension_summary_json = _json_dump(
        {
            "portrait_dimensions": portrait_dimensions,
            "activity_frequency": activity_frequency,
            "study_duration": study_duration,
            "completion": completion,
            "attendance_rate": attendance_rate,
            "participation": participation,
            "assignment_score": assignment_score,
            "quiz_score": quiz_score,
            "task_score": task_score,
            "stage_mastery": stage_mastery,
            "on_time_rate": on_time_rate,
            "continuity": continuity,
            "task_completion": task_completion,
            "resource_initiative": resource_initiative,
            "metric_types": sorted(metric_types),
        }
    )
    snapshot.indicator_summary_json = _json_dump({"portrait_indicators": portrait_indicators})
    snapshot.enabled_dimensions_json = _json_dump(
        {
            "stage_dimensions": {key: {"enabled": True, "weight": enabled_weights.get(key, 0.0)} for key in stage_dimensions.keys()},
            "selected_portrait_dimensions": portrait_dimensions,
        }
    )
    snapshot.updated_at = datetime.utcnow()

    if persist:
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
    return snapshot


def sync_profile_snapshot_from_stage(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    persist: bool = True,
) -> LearnerProfileSnapshot | None:
    latest = get_latest_stage_snapshot(session, user_id=user_id, subject=subject, grade=grade)
    if latest is None:
        return None
    history = get_stage_snapshot_trend(session, user_id=user_id, subject=subject, grade=grade, limit=5)
    ordered_history = list(reversed(history))
    scores = [float(item.dynamic_score) for item in reversed(history)]
    if len(scores) <= 1:
        stability = 0.7
    else:
        deltas = [abs(scores[idx] - scores[idx - 1]) for idx in range(1, len(scores))]
        stability = _clamp01(1.0 - (_mean_or_default(deltas, default=0.0) / 0.25))

    override = session.exec(
        select(LearnerPersonaOverride).where(
            LearnerPersonaOverride.user_id == user_id,
            LearnerPersonaOverride.subject == subject,
            LearnerPersonaOverride.grade == grade,
        )
    ).first()
    persona_type = override.persona_type if override is not None else latest.persona_type
    override_source = "manual" if override is not None else "auto"
    final_portrait_dimensions, final_portrait_indicators, term_summary = _aggregate_stage_portrait_summary(ordered_history)
    focus_dimensions = [item["dimension_title"] for item in final_portrait_dimensions if item.get("score") is not None and float(item["score"]) >= 0.6][:2]
    final_reason_summary = (
        f"共分析 {term_summary['stage_count']} 个阶段；"
        f"进步 {term_summary['progress_stages']} 次，持平 {term_summary['steady_stages']} 次，回落 {term_summary['regress_stages']} 次；"
        f"期末参考分 {round(float(term_summary['final_score_reference']) * 100)}%"
    )
    if focus_dimensions:
        final_reason_summary += f"；主要优势：{'、'.join(focus_dimensions)}"

    snapshot = LearnerProfileSnapshot(
        user_id=user_id,
        subject=subject,
        grade=grade,
        persona_type=persona_type,
        engagement=float(latest.engagement),
        achievement=float(latest.achievement),
        efficiency=float(latest.efficiency),
        risk=float(latest.risk),
        course_mastery=float(latest.course_mastery),
        dynamic_score=float(latest.dynamic_score),
        stability=stability,
        risk_level=latest.risk_level,
        override_source=override_source,
        reason_summary=latest.reason_summary,
        portrait_summary_json=_json_dump(
            {
                "portrait_dimensions": _json_load(latest.dimension_summary_json, {}).get("portrait_dimensions", []),
                "portrait_indicators": _json_load(latest.indicator_summary_json, {}).get("portrait_indicators", []),
                "final_portrait_dimensions": final_portrait_dimensions,
                "final_portrait_indicators": final_portrait_indicators,
                "term_summary": {
                    **term_summary,
                    "final_reason_summary": final_reason_summary,
                },
            }
        ),
        updated_at=datetime.utcnow(),
    )
    if persist:
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
    return snapshot


def recalculate_stage_snapshots_for_stage(
    session: Session,
    *,
    stage_id: int,
    user_ids: list[int] | None = None,
    persist: bool = True,
) -> list[StageEvaluationSnapshot]:
    stage = session.get(CourseStage, stage_id)
    if stage is None:
        return []
    affected: set[int] = {int(uid) for uid in (user_ids or []) if uid is not None}
    stmt = select(StageImportRecord.user_id).where(StageImportRecord.stage_id == stage_id)
    if user_ids:
        stmt = stmt.where(StageImportRecord.user_id.in_(user_ids))
    affected.update({int(row) for row in session.exec(stmt).all() if row is not None})
    snapshots: list[StageEvaluationSnapshot] = []
    for uid in sorted(affected):
        snapshot = recalculate_stage_snapshot(session, user_id=uid, stage_id=stage_id, persist=persist)
        if snapshot is not None:
            snapshots.append(snapshot)
            sync_profile_snapshot_from_stage(session, user_id=uid, subject=stage.subject, grade=stage.grade, persist=True)
    return snapshots


def resolve_course_id(session: Session, *, subject: str) -> int | None:
    course = session.exec(select(Course).where(Course.title == subject).order_by(desc(Course.created_at))).first()
    return int(course.id) if course and course.id is not None else None


def log_behavior_event(
    session: Session,
    *,
    user_id: int,
    event_type: str,
    subject: str | None = None,
    grade: str | None = None,
    course_id: int | None = None,
    kp_id: int | None = None,
    payload: dict[str, Any] | None = None,
    commit: bool = True,
) -> LearningBehaviorEvent:
    if course_id is None and subject:
        course_id = resolve_course_id(session, subject=subject)
    event = LearningBehaviorEvent(
        user_id=user_id,
        course_id=course_id,
        kp_id=kp_id,
        event_type=event_type,
        value_json=_json_dump(payload or {}),
    )
    session.add(event)
    if commit:
        session.commit()
        session.refresh(event)
    return event


def upsert_persona_override(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    persona_type: PersonaType,
    note: str = "",
    updated_by: str = "",
) -> LearnerPersonaOverride:
    override = session.exec(
        select(LearnerPersonaOverride).where(
            LearnerPersonaOverride.user_id == user_id,
            LearnerPersonaOverride.subject == subject,
            LearnerPersonaOverride.grade == grade,
        )
    ).first()
    if override is None:
        override = LearnerPersonaOverride(
            user_id=user_id,
            subject=subject,
            grade=grade,
            persona_type=persona_type,
            note=note,
            updated_by=updated_by,
        )
    else:
        override.persona_type = persona_type
        override.note = note
        override.updated_by = updated_by
        override.updated_at = datetime.utcnow()
    session.add(override)
    session.commit()
    session.refresh(override)
    return override


def clear_persona_override(session: Session, *, user_id: int, subject: str, grade: str) -> bool:
    override = session.exec(
        select(LearnerPersonaOverride).where(
            LearnerPersonaOverride.user_id == user_id,
            LearnerPersonaOverride.subject == subject,
            LearnerPersonaOverride.grade == grade,
        )
    ).first()
    if override is None:
        return False
    session.delete(override)
    session.commit()
    return True


def _consecutive_days(days: list[date]) -> int:
    if not days:
        return 0
    ordered = sorted(set(days), reverse=True)
    streak = 1
    for idx in range(1, len(ordered)):
        if (ordered[idx - 1] - ordered[idx]).days == 1:
            streak += 1
            continue
        break
    return streak


def _calc_stability(session: Session, *, user_id: int, subject: str, grade: str, current_score: float) -> float:
    history = get_profile_trend(session, user_id=user_id, subject=subject, grade=grade, limit=5)
    scores = [current_score] + [float(item.dynamic_score) for item in history]
    if len(scores) <= 1:
        return 0.6
    deltas = [abs(scores[idx] - scores[idx + 1]) for idx in range(len(scores) - 1)]
    return _clamp01(1.0 - (mean(deltas) / 0.25))


def _classify_persona(
    *,
    engagement: float,
    achievement: float,
    efficiency: float,
    thresholds: dict[str, Any],
) -> PersonaType:
    procrastinating_e = float(thresholds.get("procrastinating_e", 0.4))
    smart_a = float(thresholds.get("smart_a", 0.75))
    smart_f = float(thresholds.get("smart_f", 0.75))
    diligent_e = float(thresholds.get("diligent_e", 0.75))
    diligent_a = float(thresholds.get("diligent_a", 0.6))
    struggling_e = float(thresholds.get("struggling_e", 0.6))
    struggling_a = float(thresholds.get("struggling_a", 0.6))

    if engagement < procrastinating_e:
        return PersonaType.procrastinating
    if achievement >= smart_a and efficiency >= smart_f and engagement >= procrastinating_e:
        return PersonaType.smart
    if engagement >= diligent_e and achievement >= diligent_a and efficiency < smart_f:
        return PersonaType.diligent
    if engagement >= struggling_e and achievement < struggling_a:
        return PersonaType.struggling
    return PersonaType.steady


def _risk_level(dynamic_score: float) -> str:
    if dynamic_score >= 0.85:
        return "优秀"
    if dynamic_score >= 0.70:
        return "良好"
    if dynamic_score >= 0.50:
        return "预警"
    return "风险"


def _course_mastery(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    refresh_mastery: bool = False,
) -> tuple[float, list[KnowledgePoint], dict[int, Mastery]]:
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    kp_ids = [int(k.id) for k in kps if k.id is not None]
    mastery_map: dict[int, Mastery] = {}
    if not kp_ids:
        return 0.0, list(kps), mastery_map

    existing = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id.in_(kp_ids))).all()
    mastery_map = {int(item.kp_id): item for item in existing}

    if refresh_mastery or len(mastery_map) < len(kp_ids):
        from app.services.eval import upsert_mastery

        for kp in kps:
            if kp.id is None:
                continue
            if refresh_mastery or int(kp.id) not in mastery_map:
                mastery_map[int(kp.id)] = upsert_mastery(
                    session,
                    user_id=user_id,
                    kp_id=int(kp.id),
                    subject=subject,
                    grade=grade,
                )

    avg_value = mean(float(mastery_map.get(int(kp.id)).value) if int(kp.id) in mastery_map else 0.0 for kp in kps)
    return _clamp01(avg_value), list(kps), mastery_map


def recalculate_profile_snapshot(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    refresh_mastery: bool = False,
    persist: bool = True,
) -> LearnerProfileSnapshot:
    stage_based = sync_profile_snapshot_from_stage(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        persist=persist,
    )
    if stage_based is not None:
        return stage_based

    now = datetime.utcnow()
    since_30d = now - timedelta(days=30)
    since_14d = now - timedelta(days=14)
    since_7d = now - timedelta(days=7)

    rule = get_or_create_persona_rule(session, subject=subject, grade=grade)
    thresholds = resolve_persona_thresholds(rule)
    weights = resolve_persona_weights(rule)
    engagement_weights = weights.get("engagement", {})
    achievement_weights = weights.get("achievement", {})
    efficiency_weights = weights.get("efficiency", {})
    risk_weights = weights.get("risk", {})
    dynamic_weights = weights.get("dynamic", {})

    course_mastery, kps, mastery_map = _course_mastery(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        refresh_mastery=refresh_mastery,
    )
    kp_ids = [int(k.id) for k in kps if k.id is not None]

    practice_rows = []
    quiz_rows = []
    video_rows = []
    review_rows = []
    if kp_ids:
        practice_rows = session.exec(
            select(PracticeAttempt)
            .where(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.kp_id.in_(kp_ids),
                PracticeAttempt.created_at >= since_30d,
            )
            .order_by(desc(PracticeAttempt.created_at))
        ).all()
        quiz_rows = session.exec(
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.kp_id.in_(kp_ids),
                QuizAttempt.created_at >= since_30d,
            )
            .order_by(desc(QuizAttempt.created_at))
        ).all()
        video_rows = session.exec(
            select(VideoProgress)
            .where(VideoProgress.user_id == user_id, VideoProgress.kp_id.in_(kp_ids))
            .order_by(desc(VideoProgress.updated_at))
        ).all()
        review_rows = session.exec(
            select(ReviewSchedule)
            .where(ReviewSchedule.user_id == user_id, ReviewSchedule.kp_id.in_(kp_ids))
            .order_by(desc(ReviewSchedule.updated_at))
        ).all()

    behavior_rows = session.exec(
        select(LearningBehaviorEvent)
        .where(
            LearningBehaviorEvent.user_id == user_id,
            LearningBehaviorEvent.created_at >= since_30d,
            LearningBehaviorEvent.kp_id.in_(kp_ids) if kp_ids else True,
        )
        .order_by(desc(LearningBehaviorEvent.created_at))
    ).all()

    recent_practice = [row for row in practice_rows if row.created_at >= since_14d]
    recent_quiz = [row for row in quiz_rows if row.created_at >= since_14d]
    recent_behavior = [row for row in behavior_rows if row.created_at >= since_14d]

    activity_days = {
        row.created_at.date()
        for row in recent_practice
    } | {
        row.created_at.date()
        for row in recent_quiz
    } | {
        row.updated_at.date()
        for row in video_rows
        if row.updated_at >= since_14d
    } | {
        row.created_at.date()
        for row in recent_behavior
    }
    learning_frequency = _clamp01(len(activity_days) / 10.0)

    total_study_seconds = (
        sum(max(0, int(row.duration_ms or 0)) for row in recent_practice) / 1000.0
        + sum(max(0, int(row.duration_ms or 0)) for row in recent_quiz) / 1000.0
        + sum(max(0.0, float(row.watched_seconds or 0.0)) for row in video_rows if row.updated_at >= since_14d)
    )
    study_duration = _clamp01(total_study_seconds / (6 * 3600))

    total_video_resources = 0
    if kp_ids:
        total_video_resources = int(
            session.exec(
                select(func.count()).select_from(LearningResource).where(
                    LearningResource.kp_id.in_(kp_ids),
                    LearningResource.type == ResourceType.video,
                )
            ).one()
            or 0
        )
    completed_videos = len([row for row in video_rows if row.completed])
    resource_completion = _clamp01(completed_videos / total_video_resources) if total_video_resources else 0.0
    streak = _clamp01(_consecutive_days(list(activity_days)) / 7.0)

    practice_accuracy = (
        sum(1 for row in practice_rows if row.correct) / len(practice_rows)
        if practice_rows
        else 0.0
    )
    quiz_accuracy = mean(float(row.score) for row in quiz_rows) if quiz_rows else 0.0

    previous_snapshot = get_latest_profile_snapshot(session, user_id=user_id, subject=subject, grade=grade)
    if previous_snapshot is None:
        mastery_growth = _clamp01(course_mastery)
    else:
        mastery_growth = _clamp01((course_mastery - float(previous_snapshot.course_mastery)) / 0.20)

    avg_practice_duration = mean(max(1, int(row.duration_ms or 1)) for row in practice_rows) if practice_rows else 90_000.0
    speed_factor = _clamp01(90_000.0 / avg_practice_duration)
    unit_time_accuracy = _clamp01(practice_accuracy * speed_factor)

    completed_practice = len([kp for kp in kps if kp.id is not None and practice_status(session, user_id=user_id, kp_id=int(kp.id)).get("completed")])
    latest_quiz_by_kp: dict[int, QuizAttempt] = {}
    for item in quiz_rows:
        if int(item.kp_id) not in latest_quiz_by_kp:
            latest_quiz_by_kp[int(item.kp_id)] = item
    passed_quiz_count = len([item for item in latest_quiz_by_kp.values() if item.passed])
    total_kps = max(1, len(kps))
    task_completion = _clamp01(0.5 * (completed_practice / total_kps) + 0.5 * (passed_quiz_count / total_kps))

    total_reviews = len(review_rows)
    overdue_reviews = len([row for row in review_rows if row.due_at <= now and row.last_result != "correct"])
    overdue_rate = _clamp01(overdue_reviews / total_reviews) if total_reviews else 0.0

    wrong_streak = 0
    for attempt in practice_rows:
        if attempt.correct:
            break
        wrong_streak += 1
    wrong_streak_ratio = _clamp01(wrong_streak / 4.0)

    started_videos = len(video_rows)
    incomplete_started = len([row for row in video_rows if not row.completed and row.watched_seconds > 0])
    abandonment_rate = _clamp01(incomplete_started / started_videos) if started_videos else 0.0

    engagement = _clamp01(
        float(engagement_weights.get("learning_frequency", 0.35)) * learning_frequency
        + float(engagement_weights.get("study_duration", 0.35)) * study_duration
        + float(engagement_weights.get("resource_completion", 0.2)) * resource_completion
        + float(engagement_weights.get("streak", 0.1)) * streak
    )
    achievement = _clamp01(
        float(achievement_weights.get("practice_accuracy", 0.5)) * practice_accuracy
        + float(achievement_weights.get("quiz_accuracy", 0.3)) * quiz_accuracy
        + float(achievement_weights.get("mastery_growth", 0.2)) * mastery_growth
    )
    efficiency = _clamp01(
        float(efficiency_weights.get("unit_time_accuracy", 0.6)) * unit_time_accuracy
        + float(efficiency_weights.get("task_completion", 0.4)) * task_completion
    )
    risk = _clamp01(
        float(risk_weights.get("overdue_rate", 0.4)) * overdue_rate
        + float(risk_weights.get("wrong_streak", 0.3)) * wrong_streak_ratio
        + float(risk_weights.get("abandonment_rate", 0.3)) * abandonment_rate
    )

    provisional_dynamic = _clamp01(
        float(dynamic_weights.get("engagement", 0.25)) * engagement
        + float(dynamic_weights.get("achievement", 0.3)) * achievement
        + float(dynamic_weights.get("course_mastery", 0.35)) * course_mastery
    )
    stability = _calc_stability(session, user_id=user_id, subject=subject, grade=grade, current_score=provisional_dynamic)
    dynamic_score = _clamp01(
        float(dynamic_weights.get("engagement", 0.25)) * engagement
        + float(dynamic_weights.get("achievement", 0.3)) * achievement
        + float(dynamic_weights.get("course_mastery", 0.35)) * course_mastery
        + float(dynamic_weights.get("stability", 0.1)) * stability
    )

    persona_type = _classify_persona(
        engagement=engagement,
        achievement=achievement,
        efficiency=efficiency,
        thresholds=thresholds,
    )
    override = session.exec(
        select(LearnerPersonaOverride).where(
            LearnerPersonaOverride.user_id == user_id,
            LearnerPersonaOverride.subject == subject,
            LearnerPersonaOverride.grade == grade,
        )
    ).first()
    override_source = "auto"
    if override is not None:
        persona_type = override.persona_type
        override_source = "manual"

    signals = Counter(
        {
            "参与度偏低": 1 if engagement < 0.4 else 0,
            "学习成效偏弱": 1 if achievement < 0.6 else 0,
            "效率偏低": 1 if efficiency < 0.55 else 0,
            "风险偏高": 1 if risk >= 0.5 else 0,
        }
    )
    top_flags = [label for label, count in signals.most_common() if count > 0]
    if not top_flags:
        top_flags = ["学习状态稳定"]
    reason_summary = (
        f"{persona_label(persona_type)}；课程掌握度 {course_mastery:.2f}；"
        f"主要判断：{'、'.join(top_flags[:2])}"
    )

    snapshot = LearnerProfileSnapshot(
        user_id=user_id,
        subject=subject,
        grade=grade,
        persona_type=persona_type,
        engagement=engagement,
        achievement=achievement,
        efficiency=efficiency,
        risk=risk,
        course_mastery=course_mastery,
        dynamic_score=dynamic_score,
        stability=stability,
        risk_level=_risk_level(dynamic_score),
        override_source=override_source,
        reason_summary=reason_summary,
        updated_at=now,
    )
    if persist:
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
    return snapshot


def recalculate_profiles_for_subject(
    session: Session,
    *,
    subject: str,
    grade: str,
    refresh_mastery: bool = False,
) -> list[LearnerProfileSnapshot]:
    stages = session.exec(
        select(CourseStage)
        .where(CourseStage.subject == subject, CourseStage.grade == grade)
        .order_by(CourseStage.stage_order, CourseStage.id)
    ).all()
    for stage in stages:
        if stage.id is None:
            continue
        recalculate_stage_snapshots_for_stage(session, stage_id=int(stage.id), persist=True)

    students = session.exec(select(User).where(User.role == UserRole.student).order_by(User.id)).all()
    snapshots: list[LearnerProfileSnapshot] = []
    for student in students:
        if student.id is None:
            continue
        snapshots.append(
            recalculate_profile_snapshot(
                session,
                user_id=int(student.id),
                subject=subject,
                grade=grade,
                refresh_mastery=refresh_mastery,
                persist=True,
            )
        )
    return snapshots
