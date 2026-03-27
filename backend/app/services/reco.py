from __future__ import annotations

import json
from statistics import mean

from sqlmodel import Session, select

from app.db.models import (
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    Mastery,
    PersonaType,
    Question,
    RecommendationLog,
    RelationType,
)
from app.services.eval import upsert_mastery
from app.services.learner_profile import build_kp_dimension_summary, get_or_create_persona_rule, persona_label, recalculate_profile_snapshot


def _mastery_value(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str) -> Mastery:
    mastery = session.exec(select(Mastery).where(Mastery.user_id == user_id, Mastery.kp_id == kp_id)).first()
    if mastery is None:
        mastery = upsert_mastery(session, user_id=user_id, kp_id=kp_id, subject=subject, grade=grade)
    return mastery


def _prereq_ids(session: Session, *, kp_id: int) -> list[int]:
    return [
        int(edge.prereq_id)
        for edge in session.exec(
            select(KnowledgeEdge).where(
                KnowledgeEdge.next_id == kp_id,
                KnowledgeEdge.relation_type == RelationType.prerequisite,
            )
        ).all()
    ]


def _next_ids(session: Session, *, kp_id: int) -> list[int]:
    return [
        int(edge.next_id)
        for edge in session.exec(
            select(KnowledgeEdge).where(
                KnowledgeEdge.prereq_id == kp_id,
                KnowledgeEdge.relation_type == RelationType.prerequisite,
            )
        ).all()
    ]


def _related_ids(session: Session, *, kp_id: int) -> list[int]:
    rows = session.exec(
        select(KnowledgeEdge).where(
            ((KnowledgeEdge.prereq_id == kp_id) | (KnowledgeEdge.next_id == kp_id)),
            KnowledgeEdge.relation_type == RelationType.related,
        )
    ).all()
    related: set[int] = set()
    for row in rows:
        if int(row.prereq_id) == kp_id:
            related.add(int(row.next_id))
        else:
            related.add(int(row.prereq_id))
    return sorted(related)


def _resource_priority(persona_type: PersonaType) -> dict[str, int]:
    if persona_type == PersonaType.smart:
        return {"example": 0, "note": 1, "video": 2}
    if persona_type == PersonaType.diligent:
        return {"video": 0, "note": 1, "example": 2}
    if persona_type in {PersonaType.struggling, PersonaType.procrastinating}:
        return {"video": 0, "example": 1, "note": 2}
    return {"video": 0, "note": 1, "example": 2}


def _question_order(persona_type: PersonaType, question: Question) -> tuple[float, int]:
    difficulty = float(question.difficulty)
    if persona_type == PersonaType.smart:
        return (-difficulty, int(question.id or 0))
    if persona_type == PersonaType.diligent:
        return (abs(difficulty - 0.55), int(question.id or 0))
    if persona_type in {PersonaType.struggling, PersonaType.procrastinating}:
        return (difficulty, int(question.id or 0))
    return (abs(difficulty - 0.5), int(question.id or 0))


def _advice_text(persona_type: PersonaType, *, target_title: str, reason: str) -> str:
    if persona_type == PersonaType.smart:
        return f"你当前推进速度较快，建议直接冲刺“{target_title}”的高阶题，保留最少量讲解。{reason}"
    if persona_type == PersonaType.diligent:
        return f"建议按结构化路径推进“{target_title}”，先看资源，再做分层练习。{reason}"
    if persona_type == PersonaType.struggling:
        return f"先把“{target_title}”补牢，优先看短视频和基础题。{reason}"
    if persona_type == PersonaType.procrastinating:
        return f"建议先完成“{target_title}”的最短任务链：1 个资源 + 3 题练习。{reason}"
    return f"继续按标准路径学习“{target_title}”。{reason}"


def recommend_next(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str):
    current_kp = session.get(KnowledgePoint, kp_id)
    if current_kp is None:
        raise ValueError(f"Knowledge point not found: {kp_id}")

    profile = recalculate_profile_snapshot(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        refresh_mastery=False,
        persist=True,
    )
    current_mastery = _mastery_value(session, user_id=user_id, kp_id=kp_id, subject=subject, grade=grade)
    dimension_snapshot = build_kp_dimension_summary(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        kps=[current_kp],
        mastery_map={kp_id: current_mastery},
    ).get("by_kp", {}).get(kp_id, {})
    rule = get_or_create_persona_rule(session, subject=subject, grade=grade)
    strategies = json.loads(rule.strategy_json or "{}")

    blocked_prereqs: list[dict] = []
    for prereq_id in _prereq_ids(session, kp_id=kp_id):
        mastery = _mastery_value(session, user_id=user_id, kp_id=prereq_id, subject=subject, grade=grade)
        if float(mastery.value) < 0.6:
            blocked_prereqs.append({"kp_id": prereq_id, "mastery": float(mastery.value)})
    blocked_prereqs.sort(key=lambda item: item["mastery"])

    next_candidates = _next_ids(session, kp_id=kp_id)
    unlocked_next: list[int] = []
    for candidate_id in next_candidates:
        prereqs = _prereq_ids(session, kp_id=candidate_id)
        if all(_mastery_value(session, user_id=user_id, kp_id=pid, subject=subject, grade=grade).value >= 0.6 for pid in prereqs):
            unlocked_next.append(candidate_id)

    related_candidates = _related_ids(session, kp_id=kp_id)

    target_kp_id = kp_id
    stage = "current"
    if blocked_prereqs:
        target_kp_id = int(blocked_prereqs[0]["kp_id"])
        stage = "blocked_prerequisite"
    elif float(current_mastery.value) < 0.7:
        target_kp_id = kp_id
        stage = "current_remedial"
    elif bool(dimension_snapshot.get("ability_enabled")) and str(dimension_snapshot.get("ability_status")) != "achieved":
        target_kp_id = kp_id
        stage = "ability_strengthen"
    elif bool(dimension_snapshot.get("literacy_enabled")) and str(dimension_snapshot.get("literacy_status")) != "achieved":
        target_kp_id = kp_id
        stage = "literacy_strengthen"
    elif unlocked_next:
        scored = []
        for candidate_id in unlocked_next:
            mastery = _mastery_value(session, user_id=user_id, kp_id=candidate_id, subject=subject, grade=grade)
            scored.append((float(mastery.value), candidate_id))
        scored.sort(key=lambda item: item[0])
        target_kp_id = scored[0][1]
        stage = "next_unlocked"
    elif related_candidates:
        scored = []
        for candidate_id in related_candidates:
            mastery = _mastery_value(session, user_id=user_id, kp_id=candidate_id, subject=subject, grade=grade)
            scored.append((float(mastery.value), candidate_id))
        scored.sort(key=lambda item: item[0])
        target_kp_id = scored[0][1]
        stage = "related_extension"

    target_kp = session.get(KnowledgePoint, target_kp_id)
    target_mastery = _mastery_value(session, user_id=user_id, kp_id=target_kp_id, subject=subject, grade=grade)

    reason_map = {
        "blocked_prerequisite": f"当前知识点依赖的前置点还不稳，先补“{target_kp.title}”更有效。",
        "current_remedial": f"当前知识点“{target_kp.title}”掌握度仍偏低，需要继续补强。",
        "ability_strengthen": f"知识掌握度已达标，但能力目标尚未达成，建议围绕“{target_kp.title}”再做一轮能力强化。",
        "literacy_strengthen": f"知识掌握度已达标，但素养目标尚未达成，建议围绕“{target_kp.title}”补齐学习行为证据。",
        "next_unlocked": f"前置条件已满足，可以推进到下一知识点“{target_kp.title}”。",
        "related_extension": f"主线已较稳定，建议通过相关知识点“{target_kp.title}”做扩展巩固。",
        "current": f"继续围绕“{target_kp.title}”进行标准学习。",
    }
    stage_label_map = {
        "blocked_prerequisite": "先补前置",
        "current_remedial": "当前补救",
        "ability_strengthen": "强化能力",
        "literacy_strengthen": "补齐素养",
        "next_unlocked": "继续推进",
        "related_extension": "拓展学习",
        "current": "当前推荐",
    }
    reason_summary = reason_map.get(stage, reason_map["current"])

    resources = session.exec(select(LearningResource).where(LearningResource.kp_id == target_kp_id)).all()
    resource_rank = _resource_priority(profile.persona_type)
    resources = sorted(resources, key=lambda item: (resource_rank.get(item.type.value, 9), int(item.id or 0)))[:3]
    resource_list = [
        {"id": int(item.id), "title": item.title, "url": item.url, "type": item.type.value}
        for item in resources
        if item.id is not None
    ]

    questions = session.exec(select(Question).where(Question.kp_id == target_kp_id)).all()
    questions = sorted(questions, key=lambda item: _question_order(profile.persona_type, item))[:5]
    practice_list = [
        {
            "question_id": int(item.id),
            "type": item.type,
            "difficulty": float(item.difficulty),
            "prompt": item.prompt,
        }
        for item in questions
        if item.id is not None
    ]

    strategy_tag = strategies.get(profile.persona_type.value, persona_label(profile.persona_type))
    advice_text = _advice_text(profile.persona_type, target_title=target_kp.title, reason=reason_summary)

    can_unlock_next = bool(unlocked_next) and float(current_mastery.value) >= 0.7
    evidence_items = {
        "参与度达标": float(profile.engagement) >= 0.4,
        "当前掌握度达标": float(current_mastery.value) >= 0.7,
        "前置知识稳定": len(blocked_prereqs) == 0,
        "课程状态良好": float(profile.dynamic_score) >= 0.7,
    }
    evidence_missing = [label for label, ok in evidence_items.items() if not ok]

    payload = {
        "target_kp": {
            "id": int(target_kp.id),
            "code": target_kp.code,
            "title": target_kp.title,
            "chapter": target_kp.chapter,
            "mastery": float(target_mastery.value),
        },
        "reason_summary": reason_summary,
        "recommendation_stage": stage,
        "recommendation_stage_label": stage_label_map.get(stage, stage_label_map["current"]),
        "triple": {
            "knowledge": {
                "label": str(dimension_snapshot.get("knowledge_label") or target_kp.title),
                "status": str(dimension_snapshot.get("knowledge_status") or "not_started"),
            },
            "ability": {
                "labels": list(dimension_snapshot.get("ability_labels") or []),
                "status": str(dimension_snapshot.get("ability_status") or "not_started"),
            },
            "literacy": {
                "labels": list(dimension_snapshot.get("literacy_labels") or []),
                "status": str(dimension_snapshot.get("literacy_status") or "not_started"),
            },
        },
        "resource_list": resource_list,
        "practice_list": practice_list,
        "advice_text": advice_text,
        "persona_strategy_tag": strategy_tag,
        "persona_type": profile.persona_type.value,
        "persona_label": persona_label(profile.persona_type),
        "dynamic_score": float(profile.dynamic_score),
        "risk_level": profile.risk_level,
        "diagnosis": {
            "kp_id": kp_id,
            "mastery": float(current_mastery.value),
            "status": current_mastery.status,
            "reason_summary": current_mastery.reason_summary,
            "blocked_prereq_count": len(blocked_prereqs),
        },
        "evidence": {
            "items": evidence_items,
            "missing": evidence_missing,
            "score": float(mean(1.0 if ok else 0.0 for ok in evidence_items.values())) if evidence_items else 0.0,
        },
        "remedy": {
            "action": stage,
            "persona": profile.persona_type.value,
            "reason_summary": reason_summary,
        },
        "remedy_path": {
            "blocked_prereqs": [int(item["kp_id"]) for item in blocked_prereqs],
            "path": [int(item["kp_id"]) for item in blocked_prereqs] + [int(target_kp.id)],
        },
        "resources": resource_list,
        "practice": practice_list,
        "unlock": {
            "can_unlock_next": can_unlock_next,
            "next_candidates": [int(item) for item in unlocked_next],
        },
    }

    session.add(
        RecommendationLog(
            user_id=user_id,
            subject=subject,
            grade=grade,
            source_kp_id=kp_id,
            target_kp_id=int(target_kp.id),
            persona_type=profile.persona_type,
            reason_summary=reason_summary,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
    )
    session.commit()
    return payload
