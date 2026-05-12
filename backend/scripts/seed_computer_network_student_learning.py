from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings


SUBJECT = "计算机网络"
GRADE = "通用"
COURSE_CODE = "CS-NETWORK-001"
STUDENTS = {
    "student1": {
        "days": 30,
        "label": "基础补救型",
        "persona": "struggling",
        "risk_level": "warning",
        "learned_codes": [
            "CN-01-01", "CN-01-02", "CN-01-03", "CN-01-04", "CN-01-05",
            "CN-02-01", "CN-02-02", "CN-02-03", "CN-02-04", "CN-02-05", "CN-02-06", "CN-02-07",
        ],
        "tail_learning": {"CN-02-07": 0.62},
        "scores": {"engagement": 0.72, "achievement": 0.48, "efficiency": 0.43, "risk": 0.58, "stability": 0.52},
        "reason": "学习路径推进到数据链路层，基础概念掌握较稳，但以太网与交换机仍需继续练习。",
    },
    "student2": {
        "days": 60,
        "label": "稳步推进型",
        "persona": "steady",
        "risk_level": "low",
        "learned_codes": [
            "CN-01-01", "CN-01-02", "CN-01-03", "CN-01-04", "CN-01-05",
            "CN-02-01", "CN-02-02", "CN-02-03", "CN-02-04", "CN-02-05", "CN-02-06", "CN-02-07",
            "CN-03-01", "CN-03-02", "CN-03-03", "CN-03-04", "CN-03-05", "CN-03-06", "CN-03-07",
        ],
        "tail_learning": {"CN-03-06": 0.68, "CN-03-07": 0.65},
        "scores": {"engagement": 0.8, "achievement": 0.7, "efficiency": 0.64, "risk": 0.28, "stability": 0.76},
        "reason": "学习路径推进到网络层，地址规划与路由协议表现稳定，IPv6和路由协议细节仍需巩固。",
    },
    "student3": {
        "days": 90,
        "label": "高效掌握型",
        "persona": "smart",
        "risk_level": "low",
        "learned_codes": [
            "CN-01-01", "CN-01-02", "CN-01-03", "CN-01-04", "CN-01-05",
            "CN-02-01", "CN-02-02", "CN-02-03", "CN-02-04", "CN-02-05", "CN-02-06", "CN-02-07",
            "CN-03-01", "CN-03-02", "CN-03-03", "CN-03-04", "CN-03-05", "CN-03-06", "CN-03-07",
            "CN-04-01", "CN-04-02", "CN-04-03", "CN-04-04", "CN-04-05", "CN-04-06",
            "CN-05-01", "CN-05-02", "CN-05-03", "CN-05-04", "CN-05-05", "CN-05-06",
        ],
        "tail_learning": {"CN-05-04": 0.69, "CN-05-05": 0.67, "CN-05-06": 0.65},
        "scores": {"engagement": 0.74, "achievement": 0.82, "efficiency": 0.78, "risk": 0.18, "stability": 0.83},
        "reason": "学习路径推进到应用层，协议分析能力较强，后续可进入网络安全与综合抓包分析。",
    },
}


def db_config() -> dict[str, object]:
    url = settings.database_url
    # Project default is mysql+pymysql://root:root123@localhost:3306/dynamic_assessment?charset=utf8mb4
    return {
        "host": "localhost",
        "user": "root",
        "password": "root123",
        "database": "dynamic_assessment",
        "charset": "utf8mb4",
        "autocommit": False,
    }


def mastery_status(value: float) -> str:
    if value >= 0.85:
        return "mastered"
    if value >= 0.6:
        return "learning"
    if value > 0:
        return "weak"
    return "not_started"


def mastery_for_position(username: str, code: str, index: int, total: int) -> float:
    tail = STUDENTS[username].get("tail_learning", {})
    if code in tail:
        return float(tail[code])
    base = {"student1": 0.78, "student2": 0.82, "student3": 0.88}[username]
    value = base + (index % 4) * 0.025
    if index > total * 0.7:
        value -= 0.04
    return round(min(value, 0.96), 3)


def compact_payload(**items: object) -> str:
    text = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    return text[:250]


def main() -> None:
    rng = random.Random(20260510)
    now = datetime.now().replace(microsecond=0)
    conn = pymysql.connect(**db_config())
    cur = conn.cursor()
    try:
        cur.execute("select id from course where code=%s", (COURSE_CODE,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("未找到计算机网络课程")
        course_id = int(row[0])

        stage_windows = [
            (1, now - timedelta(days=89), now - timedelta(days=68)),
            (2, now - timedelta(days=67), now - timedelta(days=45)),
            (3, now - timedelta(days=44), now - timedelta(days=22)),
            (4, now - timedelta(days=21), now),
        ]
        for order, starts_at, ends_at in stage_windows:
            cur.execute(
                "update coursestage set starts_at=%s, ends_at=%s where course_id=%s and stage_order=%s",
                (starts_at, ends_at, course_id, order),
            )

        cur.execute("select id,code,title,chapter from knowledgepoint where subject=%s and grade=%s order by code", (SUBJECT, GRADE))
        kps = cur.fetchall()
        if not kps:
            raise RuntimeError("未找到计算机网络知识点")
        kp_by_code = {code: (int(kp_id), title, chapter) for kp_id, code, title, chapter in kps}
        kp_ids = [int(row[0]) for row in kps]

        cur.execute(
            """
            select p.code,n.code from knowledgeedge e
            join knowledgepoint p on p.id=e.prereq_id
            join knowledgepoint n on n.id=e.next_id
            where e.subject=%s and e.grade=%s and e.relation_type='prerequisite'
            """,
            (SUBJECT, GRADE),
        )
        edges = cur.fetchall()

        cur.execute("select kp_id,id from question where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        questions_by_kp: dict[int, list[int]] = {}
        for kp_id, qid in cur.fetchall():
            questions_by_kp.setdefault(int(kp_id), []).append(int(qid))

        cur.execute("select kp_id,id from quiz where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        quiz_by_kp = {int(kp_id): int(qid) for kp_id, qid in cur.fetchall()}

        cur.execute("select kp_id,id from learningresource where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        resource_by_kp: dict[int, int] = {}
        for kp_id, rid in cur.fetchall():
            resource_by_kp.setdefault(int(kp_id), int(rid))

        cur.execute("select id,title,stage_order from coursestage where course_id=%s order by stage_order", (course_id,))
        stages = [(int(sid), title, int(order)) for sid, title, order in cur.fetchall()]
        if len(stages) != 4:
            raise RuntimeError("计算机网络课程阶段不是 4 个，请先设置阶段")

        all_student_ids = []
        for username in STUDENTS:
            cur.execute("select id from user where username=%s and role='student'", (username,))
            user_row = cur.fetchone()
            if not user_row:
                raise RuntimeError(f"未找到学生账号 {username}")
            all_student_ids.append(int(user_row[0]))

        p = ",".join(["%s"] * len(kp_ids))
        for username, profile in STUDENTS.items():
            cur.execute("select id from user where username=%s", (username,))
            user_id = int(cur.fetchone()[0])
            days = int(profile["days"])
            learned_codes = list(profile["learned_codes"])
            learned_set = set(learned_codes)
            learned_values: dict[str, float] = {}
            for index, code in enumerate(learned_codes):
                learned_values[code] = mastery_for_position(username, code, index, len(learned_codes))

            bad = []
            for prereq_code, next_code in edges:
                if next_code in learned_set and prereq_code not in learned_set:
                    bad.append((prereq_code, next_code))
                if next_code in learned_set and learned_values.get(prereq_code, 0) < 0.7:
                    bad.append((prereq_code, next_code))
            if bad:
                raise RuntimeError(f"{username} 路径前置不闭合: {bad[:5]}")

            cur.execute(f"delete from mastery where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from practiceattempt where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from quizattempt where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from videoprogress where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute("delete from learningbehaviorevent where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from learnerprofilesnapshot where user_id=%s and subject=%s and grade=%s", (user_id, SUBJECT, GRADE))
            cur.execute("delete from stageevaluationsnapshot where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from stageteacherfeedback where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from teacherfinalscoreconfirmation where user_id=%s and course_id=%s", (user_id, course_id))

            course_start = now - timedelta(days=days)
            mastery_values = []
            for kp_id, code, title, chapter in kps:
                kp_id = int(kp_id)
                value = float(learned_values.get(code, 0.0))
                mastery_values.append(value)
                status = mastery_status(value)
                reason = profile["reason"] if value > 0 else "尚未进入该知识点学习路径。"
                cur.execute(
                    """
                    insert into mastery(user_id,kp_id,value,direct_value,status,reason_summary,updated_at)
                    values(%s,%s,%s,%s,%s,%s,%s)
                    on duplicate key update value=values(value),direct_value=values(direct_value),
                    status=values(status),reason_summary=values(reason_summary),updated_at=values(updated_at)
                    """,
                    (user_id, kp_id, value, value, status, reason, now),
                )
                if value <= 0:
                    continue

                path_index = learned_codes.index(code)
                event_time = course_start + timedelta(days=min(days - 1, max(0, int((path_index + 1) * days / len(learned_codes)))))
                cur.execute(
                    """
                    insert into learningbehaviorevent(user_id,course_id,kp_id,event_type,value_json,created_at)
                    values(%s,%s,%s,'path_choice',%s,%s)
                    """,
                    (
                        user_id,
                        course_id,
                        kp_id,
                        compact_payload(subject=SUBJECT, grade=GRADE, kp_id=kp_id, order=path_index + 1, profile=profile["label"]),
                        event_time,
                    ),
                )
                cur.execute(
                    """
                    insert into learningbehaviorevent(user_id,course_id,kp_id,event_type,value_json,created_at)
                    values(%s,%s,%s,'study_session',%s,%s)
                    """,
                    (
                        user_id,
                        course_id,
                        kp_id,
                        compact_payload(kp=code, mastery=round(value, 2), days=days),
                        event_time + timedelta(hours=1),
                    ),
                )

                for q_index, question_id in enumerate(questions_by_kp.get(kp_id, [])[:2]):
                    correct = value >= 0.7 or (q_index == 0 and value >= 0.6)
                    cur.execute(
                        """
                        insert into practiceattempt(user_id,question_id,kp_id,correct,self_report,duration_ms,created_at)
                        values(%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            user_id,
                            question_id,
                            kp_id,
                            int(correct),
                            "sure" if correct else "unsure",
                            int((120 - value * 45 + rng.randint(-10, 12)) * 1000),
                            event_time + timedelta(hours=2 + q_index),
                        ),
                    )

                quiz_id = quiz_by_kp.get(kp_id)
                if quiz_id:
                    score = max(0.35, min(0.98, value + rng.uniform(-0.05, 0.06)))
                    cur.execute(
                        """
                        insert into quizattempt(user_id,quiz_id,kp_id,score,passed,duration_ms,created_at)
                        values(%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (user_id, quiz_id, kp_id, round(score, 3), int(score >= 0.6), int((220 - value * 80) * 1000), event_time + timedelta(hours=4)),
                    )

                resource_id = resource_by_kp.get(kp_id)
                if resource_id:
                    duration = 900.0
                    watched = duration * max(0.45, min(1.0, value + 0.08))
                    cur.execute(
                        """
                        insert into videoprogress(user_id,kp_id,resource_id,watched_seconds,duration_seconds,last_position_seconds,completed,updated_at)
                        values(%s,%s,%s,%s,%s,%s,%s,%s)
                        on duplicate key update watched_seconds=values(watched_seconds),duration_seconds=values(duration_seconds),
                        last_position_seconds=values(last_position_seconds),completed=values(completed),updated_at=values(updated_at)
                        """,
                        (user_id, kp_id, resource_id, watched, duration, watched, int(watched / duration >= 0.82), event_time + timedelta(hours=3)),
                    )

            course_mastery = round(sum(mastery_values) / len(mastery_values), 3)
            scores = profile["scores"]
            portrait = {
                "画像": profile["label"],
                "学习天数": days,
                "路径终点": learned_codes[-1],
                "主要证据": profile["reason"],
            }
            cur.execute(
                """
                insert into learnerprofilesnapshot(
                    user_id,subject,grade,persona_type,engagement,achievement,efficiency,risk,course_mastery,
                    dynamic_score,stability,risk_level,override_source,reason_summary,portrait_summary_json,updated_at
                ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'seed_computer_network_student_learning',%s,%s,%s)
                """,
                (
                    user_id,
                    SUBJECT,
                    GRADE,
                    profile["persona"],
                    scores["engagement"],
                    scores["achievement"],
                    scores["efficiency"],
                    scores["risk"],
                    course_mastery,
                    round(scores["achievement"] * 0.45 + scores["engagement"] * 0.25 + scores["efficiency"] * 0.3, 3),
                    scores["stability"],
                    profile["risk_level"],
                    profile["reason"],
                    json.dumps(portrait, ensure_ascii=False),
                    now,
                ),
            )

            stage_curve = {
                "student1": [0.42, 0.52, 0.57, 0.6],
                "student2": [0.5, 0.6, 0.68, 0.72],
                "student3": [0.56, 0.68, 0.76, 0.82],
            }[username]
            for idx, (stage_id, stage_title, stage_order) in enumerate(stages):
                stage_mastery = stage_curve[idx]
                stage_start = next(start for order, start, _ in stage_windows if order == stage_order)
                stage_end = next(end for order, _, end in stage_windows if order == stage_order)
                learning_start = course_start
                learning_end = now
                if learning_end < stage_start:
                    snapshot_time = stage_end
                elif learning_start > stage_end:
                    snapshot_time = stage_end
                else:
                    snapshot_time = min(stage_end, max(stage_start, learning_start + (min(6, days) * timedelta(days=1) / max(1, min(6, days)))))
                indicator = {
                    "学习路径": learned_codes[-1],
                    "学习天数": days,
                    "阶段掌握度": stage_mastery,
                }
                cur.execute(
                    """
                    insert into stageevaluationsnapshot(
                        user_id,course_id,stage_id,subject,grade,stage_title,stage_order,persona_type,
                        engagement,achievement,habit,characteristic,efficiency,risk,course_mastery,dynamic_score,
                        trend_label,risk_level,reason_summary,dimension_summary_json,indicator_summary_json,
                        enabled_dimensions_json,updated_at
                    ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        user_id,
                        course_id,
                        stage_id,
                        SUBJECT,
                        GRADE,
                        stage_title,
                        stage_order,
                        profile["persona"],
                        scores["engagement"],
                        scores["achievement"],
                        scores["stability"],
                        scores["achievement"],
                        scores["efficiency"],
                        scores["risk"],
                        stage_mastery,
                        round(stage_mastery * 0.55 + scores["engagement"] * 0.25 + scores["efficiency"] * 0.2, 3),
                        "上升" if idx == 0 or stage_curve[idx] >= stage_curve[idx - 1] else "波动",
                        profile["risk_level"],
                        profile["reason"],
                        json.dumps({"综合表现": stage_mastery}, ensure_ascii=False),
                        json.dumps(indicator, ensure_ascii=False),
                        json.dumps(["学习投入", "知识掌握", "学习效率", "风险预警"], ensure_ascii=False),
                        snapshot_time,
                    ),
                )

            suggested = round(course_mastery * 100, 1)
            level = "优秀" if suggested >= 80 else "良好" if suggested >= 60 else "需提升"
            cur.execute(
                """
                insert into teacherfinalscoreconfirmation(
                    user_id,course_id,subject,grade,suggested_score,confirmed_score,confirmed_level,comment,
                    recommendation_summary,confirmed_by,confirmed_at,updated_at
                ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,'teacher',%s,%s)
                """,
                (
                    user_id,
                    course_id,
                    SUBJECT,
                    GRADE,
                    suggested,
                    suggested,
                    level,
                    profile["reason"],
                    f"{profile['label']}，当前路径终点 {learned_codes[-1]}。",
                    now,
                    now,
                ),
            )

        conn.commit()
        print({username: {"days": data["days"], "path_nodes": len(data["learned_codes"]), "profile": data["label"]} for username, data in STUDENTS.items()})
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
