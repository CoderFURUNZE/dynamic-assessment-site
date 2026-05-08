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
    Course,
    CourseCompletionRecord,
)
from app.services.bailian_reco import bailian_available, enhance_recommendation_with_bailian
from app.services.eval import upsert_mastery
from app.services.learner_profile import (
    build_kp_dimension_summary,
    get_or_create_persona_rule,
    persona_label,
    recalculate_profile_snapshot,
)


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


def _kp_summary(session: Session, kp_ids: list[int], mastery_by_id: dict[int, float] | None = None) -> list[dict]:
    items: list[dict] = []
    seen: set[int] = set()
    for kp_id in kp_ids:
        if kp_id in seen:
            continue
        seen.add(kp_id)
        kp = session.get(KnowledgePoint, kp_id)
        if kp is None or kp.id is None:
            continue
        items.append(
            {
                "id": int(kp.id),
                "code": kp.code,
                "title": kp.title,
                "chapter": kp.chapter,
                "mastery": mastery_by_id.get(int(kp.id)) if mastery_by_id else None,
                "is_terminal": bool(kp.is_terminal),
            }
        )
    return items


def _teacher_route_context(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    target_kp_id: int,
) -> list[dict]:
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.code, KnowledgePoint.id)
    ).all()
    kp_by_id = {int(kp.id): kp for kp in kps if kp.id is not None}
    target = kp_by_id.get(int(target_kp_id))
    if target is None:
        return []

    prereq_edges = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.subject == subject,
            KnowledgeEdge.grade == grade,
            KnowledgeEdge.relation_type == RelationType.prerequisite,
        )
    ).all()
    prereqs_by_next: dict[int, list[int]] = {}
    next_by_prereq: dict[int, list[int]] = {}
    for edge in prereq_edges:
        prereqs_by_next.setdefault(int(edge.next_id), []).append(int(edge.prereq_id))
        next_by_prereq.setdefault(int(edge.prereq_id), []).append(int(edge.next_id))

    def mainline_rank(kp: KnowledgePoint) -> tuple[int, str, int]:
        code = str(kp.code or "")
        if code == "HM-MID-01":
            return (0, code, int(kp.id or 0))
        if code.startswith("HM-MID-0"):
            return (1, code, int(kp.id or 0))
        if bool(kp.is_terminal):
            return (9, code, int(kp.id or 0))
        return (5, code, int(kp.id or 0))

    chain: list[int] = []
    seen: set[int] = set()
    cursor = int(target.id)
    while cursor and cursor not in seen:
        seen.add(cursor)
        chain.append(cursor)
        candidates = [
            kp_by_id[pid]
            for pid in prereqs_by_next.get(cursor, [])
            if pid in kp_by_id and not bool(kp_by_id[pid].is_terminal)
        ]
        if not candidates:
            break
        candidates.sort(key=mainline_rank, reverse=True)
        cursor = int(candidates[0].id)
    chain.reverse()

    if int(target.id) not in chain:
        chain.append(int(target.id))

    if not bool(target.is_terminal):
        successors = [
            kp_by_id[nid]
            for nid in next_by_prereq.get(int(target.id), [])
            if nid in kp_by_id and not bool(kp_by_id[nid].is_terminal) and str(kp_by_id[nid].code or "").startswith("HM-MID-0")
        ]
        successors.sort(key=mainline_rank)
        if successors and int(successors[0].id) not in chain:
            chain.append(int(successors[0].id))

    terminal = next((kp for kp in kps if str(kp.code or "") == "HM-MID-C2"), None)
    if terminal is None:
        terminal = next((kp for kp in kps if bool(kp.is_terminal)), None)
    if terminal is not None and terminal.id is not None and int(terminal.id) not in chain:
        chain.append(int(terminal.id))

    mastery_by_id = {
        kp_id: float(_mastery_value(session, user_id=user_id, kp_id=kp_id, subject=subject, grade=grade).value)
        for kp_id in chain
    }
    return _kp_summary(session, chain, mastery_by_id)


def _branch_route_context(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    source_kp_id: int,
    target_kp_id: int,
) -> dict:
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.code, KnowledgePoint.id)
    ).all()
    kp_by_id = {int(kp.id): kp for kp in kps if kp.id is not None}
    if source_kp_id not in kp_by_id:
        return {}

    edges = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.subject == subject,
            KnowledgeEdge.grade == grade,
            KnowledgeEdge.relation_type == RelationType.prerequisite,
        )
    ).all()
    prereqs_by_next: dict[int, list[int]] = {}
    next_by_prereq: dict[int, list[int]] = {}
    for edge in edges:
        prereqs_by_next.setdefault(int(edge.next_id), []).append(int(edge.prereq_id))
        next_by_prereq.setdefault(int(edge.prereq_id), []).append(int(edge.next_id))

    def kp_rank(kp_id: int) -> tuple[int, str, int]:
        kp = kp_by_id.get(kp_id)
        if kp is None:
            return (9, "", kp_id)
        if bool(kp.is_terminal):
            return (8, str(kp.code or ""), kp_id)
        return (0, str(kp.code or ""), kp_id)

    def is_available(kp_id: int) -> bool:
        kp = kp_by_id.get(kp_id)
        if kp is not None and bool(kp.is_terminal):
            return True
        prereqs = prereqs_by_next.get(kp_id, [])
        return all(
            float(_mastery_value(session, user_id=user_id, kp_id=pid, subject=subject, grade=grade).value) >= 0.7
            for pid in prereqs
        )

    direct_next_ids = sorted(
        [item for item in next_by_prereq.get(source_kp_id, []) if item in kp_by_id],
        key=kp_rank,
    )
    terminal_ids = sorted(
        [int(kp.id) for kp in kps if kp.id is not None and bool(kp.is_terminal)],
        key=kp_rank,
    )
    display_ids: list[int] = []
    for candidate_id in [source_kp_id, *direct_next_ids, target_kp_id, *terminal_ids]:
        if candidate_id in kp_by_id and candidate_id not in display_ids:
            display_ids.append(candidate_id)

    mastery_by_id = {
        kp_id: float(_mastery_value(session, user_id=user_id, kp_id=kp_id, subject=subject, grade=grade).value)
        for kp_id in display_ids
    }

    def enrich(items: list[dict]) -> list[dict]:
        result: list[dict] = []
        for item in items:
            kp_item_id = int(item.get("id") or item.get("kp_id") or 0)
            if not kp_item_id:
                continue
            available = is_available(kp_item_id) or kp_item_id == source_kp_id
            result.append(
                {
                    **item,
                    "available": available,
                    "locked": not available,
                    "recommended": kp_item_id == int(target_kp_id),
                }
            )
        return result

    display_nodes = enrich(_kp_summary(session, display_ids, mastery_by_id))
    next_options = enrich(_kp_summary(session, direct_next_ids, mastery_by_id))
    terminal_options = enrich(_kp_summary(session, terminal_ids, mastery_by_id))
    return {
        "mode": "branch_select",
        "current_id": int(source_kp_id),
        "recommended_target_id": int(target_kp_id),
        "display_nodes": display_nodes,
        "next_options": next_options,
        "terminal_options": terminal_options,
        "available_ids": [int(item["id"]) for item in display_nodes if bool(item.get("available"))],
        "terminal_ids": terminal_ids,
        "explain": "系统高亮当前推荐节点；遇到分支时会同时展示可选节点，学生可以自主选择路径，也可以挑战终点节点。",
    }


def _advice_text(persona_type: PersonaType, *, target_title: str, reason: str) -> str:
    if persona_type == PersonaType.smart:
        return f"你当前推进速度较快，建议直接挑战“{target_title}”的高阶题，并保留少量讲解复盘。{reason}"
    if persona_type == PersonaType.diligent:
        return f"建议按结构化路径推进“{target_title}”，先看资源，再做分层练习。{reason}"
    if persona_type == PersonaType.struggling:
        return f"先把“{target_title}”补稳，优先看短视频和基础题。{reason}"
    if persona_type == PersonaType.procrastinating:
        return f"建议先完成“{target_title}”的最短任务链：1 个资源 + 3 道练习。{reason}"
    return f"继续按标准路径学习“{target_title}”。{reason}"


def _apply_bailian_enhancement(payload: dict, enhancement: dict) -> dict:
    if not enhancement:
        payload["recommendation_source"] = "local_rule"
        payload["ai_enhanced"] = {"provider": "bailian", "enabled": bailian_available(), "ok": False}
        return payload

    payload["ai_enhanced"] = enhancement
    if not enhancement.get("ok"):
        payload["recommendation_source"] = "local_rule"
        return payload

    target_id = int(payload["target_kp"]["id"])
    try:
        enhanced_target_id = int(enhancement.get("target_kp_id") or target_id)
    except (TypeError, ValueError):
        enhanced_target_id = target_id
    if enhanced_target_id == target_id:
        reason = str(enhancement.get("reason_summary") or "").strip()
        advice = str(enhancement.get("advice_text") or "").strip()
        if reason:
            payload["reason_summary"] = reason
            payload["remedy"]["reason_summary"] = reason
        if advice:
            payload["advice_text"] = advice
    payload["recommendation_source"] = "bailian"
    payload["personalized_path"] = enhancement.get("personalized_path") or payload["remedy_path"].get("nodes", [])
    payload["student_message"] = enhancement.get("student_message") or payload["advice_text"]
    payload["teacher_explanation"] = enhancement.get("teacher_explanation") or payload["reason_summary"]
    return payload


def _apply_seeded_demo_path(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
    source_kp_id: int,
    payload: dict,
) -> dict:
    logs = session.exec(
        select(RecommendationLog)
        .where(
            RecommendationLog.user_id == user_id,
            RecommendationLog.subject == subject,
            RecommendationLog.grade == grade,
        )
        .order_by(RecommendationLog.created_at.desc())
    ).all()
    for log in logs[:20]:
        try:
            seeded = json.loads(log.payload_json or "{}")
        except Exception:
            continue
        if seeded.get("recommendation_source") != "midterm_demo_seed":
            continue
        seeded_path = seeded.get("personalized_path")
        path_ids: list[int] = []
        if isinstance(seeded_path, list) and seeded_path:
            path_ids = [
                int(item.get("kp_id") or item.get("id"))
                for item in seeded_path
                if item.get("kp_id") or item.get("id")
            ]
            payload["personalized_path"] = seeded_path
            payload["remedy_path"]["nodes"] = seeded_path
            payload["remedy_path"]["path"] = path_ids

        next_target_id = int(payload.get("target_kp", {}).get("id") or 0)
        if path_ids:
            current_mastery = _mastery_value(
                session,
                user_id=user_id,
                kp_id=source_kp_id,
                subject=subject,
                grade=grade,
            )
            if source_kp_id in path_ids and float(current_mastery.value) >= 0.7:
                current_index = path_ids.index(source_kp_id)
                for candidate_id in path_ids[current_index + 1 :]:
                    candidate_mastery = _mastery_value(
                        session,
                        user_id=user_id,
                        kp_id=candidate_id,
                        subject=subject,
                        grade=grade,
                    )
                    if float(candidate_mastery.value) < 0.7:
                        next_target_id = candidate_id
                        break
                if not next_target_id and current_index + 1 < len(path_ids):
                    next_target_id = path_ids[current_index + 1]

        target_override_id = next_target_id
        target_override = session.get(KnowledgePoint, target_override_id) if target_override_id else None
        if target_override is not None and target_override.id is not None:
            target_mastery = _mastery_value(
                session,
                user_id=user_id,
                kp_id=int(target_override.id),
                subject=subject,
                grade=grade,
            )
            payload["target_kp"] = {
                **payload["target_kp"],
                "id": int(target_override.id),
                "code": target_override.code,
                "title": target_override.title,
                "chapter": target_override.chapter,
                "mastery": float(target_mastery.value),
                "is_terminal": bool(target_override.is_terminal),
            }
            if source_kp_id in path_ids and target_override_id != source_kp_id:
                payload["reason_summary"] = f"当前知识点已达标，可以推进到下一个知识点“{target_override.title}”。"
                payload["advice_text"] = f"建议进入“{target_override.title}”，继续沿个性化路径推进。"
                payload["student_message"] = payload["advice_text"]
                payload["teacher_explanation"] = payload["reason_summary"]
                payload["recommendation_stage_label"] = "继续推进"
        for key in ("reason_summary", "advice_text", "student_message", "teacher_explanation"):
            if seeded.get(key) and target_override_id == source_kp_id:
                payload[key] = seeded[key]
        if target_override_id == source_kp_id:
            payload["recommendation_stage_label"] = seeded.get("recommendation_stage_label") or payload.get("recommendation_stage_label")
        payload["recommendation_source"] = "local_rule"
        return payload
    return payload


def _sync_course_completion(
    session: Session,
    *,
    user_id: int,
    subject: str,
    grade: str,
) -> dict:
    terminal_kps = session.exec(
        select(KnowledgePoint).where(
            KnowledgePoint.subject == subject,
            KnowledgePoint.grade == grade,
            KnowledgePoint.is_terminal == True,  # noqa: E712
        )
    ).all()
    if not terminal_kps:
        return {"enabled": False, "completed": False, "terminal_kps": []}

    terminal_items: list[dict] = []
    completed_terminal: KnowledgePoint | None = None
    for kp in terminal_kps:
        if kp.id is None:
            continue
        mastery = _mastery_value(session, user_id=user_id, kp_id=int(kp.id), subject=subject, grade=grade)
        item = {
            "kp_id": int(kp.id),
            "title": kp.title,
            "mastery": float(mastery.value),
            "completed": float(mastery.value) >= 0.7,
        }
        terminal_items.append(item)
        if item["completed"] and completed_terminal is None:
            completed_terminal = kp

    if completed_terminal is None:
        return {"enabled": True, "completed": False, "terminal_kps": terminal_items}

    course = session.exec(select(Course).where(Course.title == subject).order_by(Course.created_at.desc())).first()
    if course is None or course.id is None:
        return {"enabled": True, "completed": True, "terminal_kps": terminal_items, "recorded": False}

    existing = session.exec(
        select(CourseCompletionRecord).where(
            CourseCompletionRecord.course_id == int(course.id),
            CourseCompletionRecord.student_id == user_id,
        )
    ).first()
    if existing is None:
        session.add(
            CourseCompletionRecord(
                course_id=int(course.id),
                student_id=user_id,
                note=f"完成终点知识点：{completed_terminal.title}",
            )
        )
        session.flush()
    return {
        "enabled": True,
        "completed": True,
        "recorded": True,
        "course_id": int(course.id),
        "terminal_kps": terminal_items,
        "completed_terminal_kp_id": int(completed_terminal.id),
        "completed_terminal_title": completed_terminal.title,
    }


def recommend_next(session: Session, *, user_id: int, kp_id: int, subject: str, grade: str, enable_ai: bool = False):
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
        if float(mastery.value) < 0.7:
            blocked_prereqs.append({"kp_id": prereq_id, "mastery": float(mastery.value)})
    blocked_prereqs.sort(key=lambda item: item["mastery"])

    next_candidates = _next_ids(session, kp_id=kp_id)
    unlocked_next: list[int] = []
    for candidate_id in next_candidates:
        prereqs = _prereq_ids(session, kp_id=candidate_id)
        if all(_mastery_value(session, user_id=user_id, kp_id=pid, subject=subject, grade=grade).value >= 0.7 for pid in prereqs):
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
            candidate = session.get(KnowledgePoint, candidate_id)
            if candidate is None:
                continue
            mastery = _mastery_value(session, user_id=user_id, kp_id=candidate_id, subject=subject, grade=grade)
            scored.append((bool(candidate.is_terminal), str(candidate.code or ""), float(mastery.value), candidate_id))
        scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        target_kp_id = scored[0][3]
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
    if target_kp is None or target_kp.id is None:
        raise ValueError(f"Recommendation target not found: {target_kp_id}")
    target_mastery = _mastery_value(session, user_id=user_id, kp_id=target_kp_id, subject=subject, grade=grade)

    reason_map = {
        "blocked_prerequisite": f"当前知识点依赖的前置点还不稳，先补“{target_kp.title}”更有效。",
        "current_remedial": f"当前知识点“{target_kp.title}”掌握度仍偏低，需要继续补强。",
        "ability_strengthen": f"知识掌握度已达标，但能力目标尚未达成，建议围绕“{target_kp.title}”再做一轮能力强化。",
        "literacy_strengthen": f"知识掌握度已达标，但素养目标尚未达成，建议围绕“{target_kp.title}”补齐学习证据。",
        "next_unlocked": f"前置条件已满足，可以推进到下一个知识点“{target_kp.title}”。",
        "related_extension": f"主线已较稳定，建议通过相关知识点“{target_kp.title}”做拓展巩固。",
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
    remedy_path_ids = [int(item["kp_id"]) for item in blocked_prereqs] + [int(target_kp.id)]
    candidate_ids = [kp_id, int(target_kp.id), *[int(item["kp_id"]) for item in blocked_prereqs], *unlocked_next, *related_candidates]
    mastery_by_id: dict[int, float] = {}
    for candidate_id in candidate_ids:
        mastery_by_id[candidate_id] = float(
            _mastery_value(session, user_id=user_id, kp_id=candidate_id, subject=subject, grade=grade).value
        )

    payload = {
        "target_kp": {
            "id": int(target_kp.id),
            "code": target_kp.code,
            "title": target_kp.title,
            "chapter": target_kp.chapter,
            "mastery": float(target_mastery.value),
            "is_terminal": bool(target_kp.is_terminal),
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
            "path": remedy_path_ids,
            "nodes": _kp_summary(session, remedy_path_ids, mastery_by_id),
        },
        "personalized_path": _kp_summary(session, remedy_path_ids, mastery_by_id),
        "recommendation_source": "local_rule",
        "ai_enhanced": {"provider": "bailian", "enabled": bailian_available(), "ok": False},
        "student_message": advice_text,
        "teacher_explanation": reason_summary,
        "course_completion": {"enabled": False, "completed": False},
        "resources": resource_list,
        "practice": practice_list,
        "unlock": {
            "can_unlock_next": can_unlock_next,
            "next_candidates": [int(item) for item in unlocked_next],
        },
    }

    if enable_ai and bailian_available():
        context = {
            "student_profile": {
                "persona_type": profile.persona_type.value,
                "persona_label": persona_label(profile.persona_type),
                "dynamic_score": float(profile.dynamic_score),
                "engagement": float(profile.engagement),
                "risk_level": profile.risk_level,
                "strategy_tag": strategy_tag,
            },
            "local_recommendation": {
                "target_kp": payload["target_kp"],
                "stage": stage,
                "stage_label": payload["recommendation_stage_label"],
                "reason_summary": reason_summary,
                "advice_text": advice_text,
            },
            "current_kp": _kp_summary(session, [kp_id], mastery_by_id)[0],
            "graph_candidates": {
                "blocked_prereqs": _kp_summary(session, [int(item["kp_id"]) for item in blocked_prereqs], mastery_by_id),
                "unlocked_next": _kp_summary(session, unlocked_next, mastery_by_id),
                "related": _kp_summary(session, related_candidates, mastery_by_id),
                "remedy_path": payload["remedy_path"]["nodes"],
            },
            "evidence": payload["evidence"],
            "triple": payload["triple"],
            "resources": [{"id": item["id"], "title": item["title"], "type": item["type"]} for item in resource_list],
            "practice": [
                {"question_id": item["question_id"], "type": item["type"], "difficulty": item["difficulty"]}
                for item in practice_list
            ],
        }
        payload = _apply_bailian_enhancement(payload, enhance_recommendation_with_bailian(context))

    payload = _apply_seeded_demo_path(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        source_kp_id=kp_id,
        payload=payload,
    )
    route_options = _branch_route_context(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
        source_kp_id=kp_id,
        target_kp_id=int(payload["target_kp"]["id"]),
    )
    if route_options:
        route_nodes = list(route_options.get("display_nodes") or [])
        route_ids = [int(item["id"]) for item in route_nodes if item.get("id")]
        payload["route_options"] = route_options
        payload["personalized_path"] = route_nodes
        payload["remedy_path"]["nodes"] = route_nodes
        payload["remedy_path"]["path"] = route_ids

    payload["course_completion"] = _sync_course_completion(
        session,
        user_id=user_id,
        subject=subject,
        grade=grade,
    )

    session.add(
        RecommendationLog(
            user_id=user_id,
            subject=subject,
            grade=grade,
            source_kp_id=kp_id,
            target_kp_id=int(payload["target_kp"]["id"]),
            persona_type=profile.persona_type,
            reason_summary=payload["reason_summary"],
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
    )
    session.commit()
    return payload
