from __future__ import annotations

from collections.abc import Iterable

from sqlmodel import Session, select

from app.db.models import KnowledgePoint


def _set_csv(value: str, items: Iterable[str]) -> str:
    existing = [x.strip() for x in (value or "").replace("；", ",").replace("、", ",").split(",") if x.strip()]
    merged: list[str] = []
    for item in existing + [str(x).strip() for x in items if str(x).strip()]:
        if item and item not in merged:
            merged.append(item)
    return "、".join(merged)


def _infer_knowledge_tag(kp: KnowledgePoint) -> str:
    base = (kp.title or "").strip()
    if not base:
        base = (kp.code or "").strip()
    return base or "知识点"


def _infer_ability_tags(kp: KnowledgePoint) -> list[str]:
    title = f"{kp.chapter} {kp.title}".strip()
    tags: list[str] = []
    rules: list[tuple[list[str], list[str]]] = [
        (["调度", "算法", "置换", "并发", "同步", "互斥"], ["算法设计", "系统分析"]),
        (["死锁", "竞态", "临界区"], ["问题定位", "系统分析"]),
        (["内存", "虚拟", "分页", "分段"], ["抽象建模", "系统分析"]),
        (["文件", "磁盘", "I/O", "设备"], ["系统分析", "工程实践"]),
        (["安全", "保护", "权限", "攻击"], ["安全意识", "问题定位"]),
        (["网络", "协议", "路由", "拥塞"], ["系统分析", "抽象建模"]),
        (["树", "图", "查找", "排序", "哈希"], ["算法设计", "逻辑推理"]),
        (["流水线", "指令", "存储层次", "Cache"], ["系统分析", "抽象建模"]),
    ]
    for keywords, add in rules:
        if any(k.lower() in title.lower() for k in keywords):
            for item in add:
                if item not in tags:
                    tags.append(item)
    if not tags:
        tags = ["系统分析"]
    return tags[:3]


def _infer_literacy_tags(kp: KnowledgePoint) -> list[str]:
    title = f"{kp.chapter} {kp.title}".strip()
    tags: list[str] = []
    rules: list[tuple[list[str], list[str]]] = [
        (["实验", "实践", "实现", "项目"], ["实践能力", "规范意识"]),
        (["安全", "保护", "权限"], ["安全意识", "责任意识"]),
        (["调试", "排错", "诊断"], ["问题意识", "自主学习"]),
        (["协作", "团队", "沟通"], ["合作沟通", "责任意识"]),
        (["复习", "总结", "反思"], ["反思改进", "自主学习"]),
    ]
    for keywords, add in rules:
        if any(k.lower() in title.lower() for k in keywords):
            for item in add:
                if item not in tags:
                    tags.append(item)
    if not tags:
        tags = ["自主学习"]
    return tags[:3]


def auto_tag_knowledge_points(
    session: Session,
    *,
    subject: str,
    grade: str,
    overwrite: bool = False,
) -> dict[str, int]:
    rows = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade).order_by(KnowledgePoint.id)
    ).all()
    updated = 0
    for kp in rows:
        changed = False
        if overwrite or not (kp.knowledge_tag or "").strip():
            next_value = _infer_knowledge_tag(kp)
            if next_value != kp.knowledge_tag:
                kp.knowledge_tag = next_value
                changed = True
        if overwrite or not (kp.ability_tag or "").strip():
            next_value = _set_csv(kp.ability_tag, _infer_ability_tags(kp))
            if next_value != kp.ability_tag:
                kp.ability_tag = next_value
                changed = True
        if overwrite or not (kp.literacy_tag or "").strip():
            next_value = _set_csv(kp.literacy_tag, _infer_literacy_tags(kp))
            if next_value != kp.literacy_tag:
                kp.literacy_tag = next_value
                changed = True
        if changed:
            updated += 1
            session.add(kp)
    session.commit()
    return {"updated": updated, "total": len(rows)}

