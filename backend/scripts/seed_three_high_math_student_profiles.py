from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

import pymysql


DB = dict(host="localhost", user="root", password="root123", database="dynamic_assessment", charset="utf8mb4")
SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM-VERIFIED-CALCULUS"
STUDENT_USERNAMES = ["student_demo_1", "student_demo_2", "student_demo_3"]
NOW = datetime.now().replace(microsecond=0)


PATH_CODES = {
    "student_demo_1": ["HM-V01-01", "HM-V01-02", "HM-V01-03", "HM-V01-04", "HM-V01-05", "HM-V01-06"],
    "student_demo_2": [
        "HM-V01-01", "HM-V01-02", "HM-V01-03", "HM-V01-04", "HM-V01-05", "HM-V01-06", "HM-V01-07", "HM-V01-08",
        "HM-V02-01", "HM-V02-02", "HM-V02-03", "HM-V02-04", "HM-V02-05",
        "HM-V03-01", "HM-V03-02", "HM-V03-03", "HM-V03-04", "HM-V03-05", "HM-V03-06", "HM-V03-07", "HM-V03-08",
        "HM-V04-01",
    ],
    "student_demo_3": [
        "HM-V01-01", "HM-V01-02", "HM-V01-03", "HM-V01-04", "HM-V01-05", "HM-V01-06", "HM-V01-07", "HM-V01-08",
        "HM-V02-01", "HM-V02-02", "HM-V02-03", "HM-V02-04", "HM-V02-05",
        "HM-V03-01", "HM-V03-02", "HM-V03-03", "HM-V03-04", "HM-V03-05", "HM-V03-06", "HM-V03-07", "HM-V03-08",
        "HM-V04-01", "HM-V04-02", "HM-V04-03",
    ],
}


DEMO_MASTERY_BY_CODE = {
    "student_demo_1": {
        "HM-V01-01": 1.00,
        "HM-V01-02": 1.00,
        "HM-V01-03": 1.00,
        "HM-V01-04": 0.76,
        "HM-V01-05": 0.71,
        "HM-V01-06": 0.66,
    },
    "student_demo_2": {
        "HM-V01-01": 0.96,
        "HM-V01-02": 0.94,
        "HM-V01-03": 0.93,
        "HM-V01-04": 0.91,
        "HM-V01-05": 0.89,
        "HM-V01-06": 0.88,
        "HM-V01-07": 0.9,
        "HM-V01-08": 0.87,
        "HM-V02-01": 0.88,
        "HM-V02-02": 0.86,
        "HM-V02-03": 0.84,
        "HM-V02-04": 0.82,
        "HM-V02-05": 0.83,
        "HM-V03-01": 0.82,
        "HM-V03-02": 0.8,
        "HM-V03-03": 0.78,
        "HM-V03-04": 0.79,
        "HM-V03-05": 0.76,
        "HM-V03-06": 0.74,
        "HM-V03-07": 0.73,
        "HM-V03-08": 0.72,
        "HM-V04-01": 0.64,
    },
    "student_demo_3": {
        "HM-V01-01": 0.86,
        "HM-V01-02": 0.78,
        "HM-V01-03": 0.74,
        "HM-V01-04": 0.71,
        "HM-V01-05": 0.72,
        "HM-V01-06": 0.71,
        "HM-V01-07": 0.72,
        "HM-V01-08": 0.7,
        "HM-V02-01": 0.74,
        "HM-V02-02": 0.72,
        "HM-V02-03": 0.71,
        "HM-V02-04": 0.70,
        "HM-V02-05": 0.70,
        "HM-V03-01": 0.72,
        "HM-V03-02": 0.71,
        "HM-V03-03": 0.70,
        "HM-V03-04": 0.70,
        "HM-V03-05": 0.72,
        "HM-V03-06": 0.71,
        "HM-V03-07": 0.70,
        "HM-V03-08": 0.70,
        "HM-V04-01": 0.72,
        "HM-V04-02": 0.70,
        "HM-V04-03": 0.52,
    },
}

MASTERY_OVERRIDES = DEMO_MASTERY_BY_CODE


PROFILES = {
    "student_demo_1": {
        "label": "基础补救型",
        "persona": "struggling",
        "engagement": 0.76,
        "achievement": 0.48,
        "efficiency": 0.42,
        "risk": 0.62,
        "stability": 0.52,
        "risk_level": "warning",
        "chapters": {
            "函数、极限与连续": 0.66,
            "导数与微分": 0.50,
            "微分中值定理与导数应用": 0.38,
            "不定积分": 0.34,
            "定积分及其应用": 0.28,
        },
        "practice_per_kp": 4,
        "video_ratio": 0.72,
        "reason": "学习投入稳定，但极限到导数应用的迁移仍不牢固，适合基础补救路径。",
    },
    "student_demo_2": {
        "label": "高效掌握型",
        "persona": "smart",
        "engagement": 0.82,
        "achievement": 0.89,
        "efficiency": 0.88,
        "risk": 0.14,
        "stability": 0.86,
        "risk_level": "low",
        "chapters": {
            "函数、极限与连续": 0.94,
            "导数与微分": 0.91,
            "微分中值定理与导数应用": 0.86,
            "不定积分": 0.84,
            "定积分及其应用": 0.82,
            "常微分方程": 0.78,
            "无穷级数": 0.76,
            "多元函数微分法": 0.74,
        },
        "practice_per_kp": 3,
        "video_ratio": 0.58,
        "reason": "正确率高、用时短，能够快速推进主线知识，适合拔高与综合应用任务。",
    },
    "student_demo_3": {
        "label": "拖延波动型",
        "persona": "procrastinating",
        "engagement": 0.38,
        "achievement": 0.58,
        "efficiency": 0.46,
        "risk": 0.72,
        "stability": 0.34,
        "risk_level": "high",
        "chapters": {
            "函数、极限与连续": 0.70,
            "导数与微分": 0.56,
            "不定积分": 0.64,
            "定积分及其应用": 0.62,
            "重积分与曲线曲面积分": 0.44,
        },
        "practice_per_kp": 2,
        "video_ratio": 0.36,
        "reason": "学习行为集中在临近评价前，积分分支有冲刺痕迹，但整体稳定性不足。",
    },
}


def clamp(value: float, low: float = 0.05, high: float = 0.98) -> float:
    return max(low, min(high, value))


def mastery_for(profile: dict, chapter: str, index: int) -> float:
    base = profile["chapters"].get(chapter, 0.18)
    wave = ((index % 5) - 2) * 0.025
    return round(clamp(base + wave), 3)


def status_for(value: float) -> str:
    if value >= 0.85:
        return "mastered"
    if value >= 0.6:
        return "learning"
    if value >= 0.28:
        return "weak"
    return "not_started"


def upsert_mastery(cur, user_id: int, kp_id: int, value: float, reason: str) -> None:
    cur.execute(
        """
        insert into mastery(user_id,kp_id,value,direct_value,status,reason_summary,updated_at)
        values(%s,%s,%s,%s,%s,%s,%s)
        on duplicate key update value=values(value), direct_value=values(direct_value),
        status=values(status), reason_summary=values(reason_summary), updated_at=values(updated_at)
        """,
        (user_id, kp_id, value, value, status_for(value), reason, NOW),
    )


def ensure_course_stages(cur, course_id: int) -> list[tuple[int, str, int]]:
    titles = ["基础诊断", "导数与积分推进", "应用能力形成", "多元与级数拓展", "综合达标"]
    result = []
    base = NOW - timedelta(days=35)
    for i, title in enumerate(titles, 1):
        cur.execute(
            """
            select id from coursestage where course_id=%s and stage_order=%s
            """,
            (course_id, i),
        )
        row = cur.fetchone()
        if row:
            stage_id = row[0]
            cur.execute(
                "update coursestage set title=%s, subject=%s, grade=%s where id=%s",
                (title, SUBJECT, GRADE, stage_id),
            )
        else:
            cur.execute(
                """
                insert into coursestage(course_id,subject,grade,title,stage_order,starts_at,ends_at,description,created_at)
                values(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    course_id,
                    SUBJECT,
                    GRADE,
                    title,
                    i,
                    base + timedelta(days=(i - 1) * 7),
                    base + timedelta(days=i * 7 - 1),
                    "高等数学答辩演示阶段评价数据。",
                    NOW,
                ),
            )
            stage_id = cur.lastrowid
        result.append((stage_id, title, i))
    return result


def main() -> None:
    rng = random.Random(20260509)
    conn = pymysql.connect(**DB, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("select id from course where code=%s", (COURSE_CODE,))
        course = cur.fetchone()
        if not course:
            raise RuntimeError(f"course not found: {COURSE_CODE}")
        course_id = course[0]
        stages = ensure_course_stages(cur, course_id)

        cur.execute(
            "select id, username, full_name from user where username in (%s,%s,%s) order by id",
            STUDENT_USERNAMES,
        )
        students = cur.fetchall()
        if len(students) != 3:
            raise RuntimeError(f"expected 3 demo students, got {len(students)}")

        cur.execute("select id, code, title, chapter from knowledgepoint where subject=%s and grade=%s order by code", (SUBJECT, GRADE))
        kps = cur.fetchall()
        kp_ids = [row[0] for row in kps]

        cur.execute("select kp_id, id from question where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        question_by_kp: dict[int, list[int]] = {}
        for kp_id, qid in cur.fetchall():
            question_by_kp.setdefault(kp_id, []).append(qid)

        cur.execute("select kp_id, id from quiz where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        quiz_by_kp = {kp_id: qid for kp_id, qid in cur.fetchall()}

        cur.execute("select kp_id, id from learningresource where subject=%s and grade=%s order by kp_id,id", (SUBJECT, GRADE))
        resource_by_kp: dict[int, list[int]] = {}
        for kp_id, rid in cur.fetchall():
            resource_by_kp.setdefault(kp_id, []).append(rid)
        kp_by_code = {code: (kp_id, title, chapter) for kp_id, code, title, chapter in kps}

        for user_id, username, full_name in students:
            profile = PROFILES[username]
            enrolled_at = NOW - timedelta(days=42)
            cur.execute(
                "select id from enrollment where student_id=%s and course_id=%s limit 1",
                (user_id, course_id),
            )
            enrollment = cur.fetchone()
            if enrollment:
                cur.execute(
                    "update enrollment set status='active', enrolled_at=%s where id=%s",
                    (enrolled_at, enrollment[0]),
                )
            else:
                cur.execute(
                    """
                    insert into enrollment(student_id,course_id,application_id,status,enrolled_at)
                    values(%s,%s,null,'active',%s)
                    """,
                    (user_id, course_id, enrolled_at),
                )

            p = ",".join(["%s"] * len(kp_ids))
            cur.execute(f"delete from mastery where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from practiceattempt where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from quizattempt where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from videoprogress where user_id=%s and kp_id in ({p})", [user_id, *kp_ids])
            cur.execute(f"delete from learningbehaviorevent where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from learnerprofilesnapshot where user_id=%s and subject=%s and grade=%s", (user_id, SUBJECT, GRADE))
            cur.execute("delete from stageevaluationsnapshot where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from stageteacherfeedback where user_id=%s and course_id=%s", (user_id, course_id))
            cur.execute("delete from teacherfinalscoreconfirmation where user_id=%s and course_id=%s", (user_id, course_id))

            profile_mastery = DEMO_MASTERY_BY_CODE.get(username, {})
            mastered_values = []
            for index, (kp_id, code, title, chapter) in enumerate(kps):
                value = profile_mastery.get(code, 0.0)
                mastered_values.append(value)
                upsert_mastery(cur, user_id, kp_id, value, profile["reason"])

                if value < 0.16:
                    continue
                event_base = NOW - timedelta(days=34 - min(index // 2, 28))
                for qid in question_by_kp.get(kp_id, [])[: profile["practice_per_kp"]]:
                    correct_prob = clamp(value + (0.12 if username == "student_demo_2" else -0.08 if username == "student_demo_3" else 0.0))
                    attempts = 1 if username == "student_demo_2" else 2 if value < 0.55 else 1
                    for attempt in range(attempts):
                        correct = rng.random() < correct_prob
                        duration = int((95 - value * 45 + rng.randint(-12, 18)) * 1000)
                        cur.execute(
                            """
                            insert into practiceattempt(user_id,question_id,kp_id,correct,self_report,duration_ms,created_at)
                            values(%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (user_id, qid, kp_id, int(correct), "sure" if correct else "unsure", duration, event_base + timedelta(hours=attempt)),
                        )

                quiz_id = quiz_by_kp.get(kp_id)
                if quiz_id and value >= 0.24:
                    score = clamp(value + rng.uniform(-0.08, 0.1))
                    cur.execute(
                        """
                        insert into quizattempt(user_id,quiz_id,kp_id,score,passed,duration_ms,created_at)
                        values(%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (user_id, quiz_id, kp_id, round(score, 3), int(score >= 0.6), int((180 + (1 - value) * 180) * 1000), event_base),
                    )

                resources = resource_by_kp.get(kp_id, [])
                if resources and value >= 0.2:
                    ratio = clamp(profile["video_ratio"] + value * 0.25 + rng.uniform(-0.12, 0.08), 0.08, 1.0)
                    duration = 600 + (index % 4) * 180
                    watched = duration * ratio
                    cur.execute(
                        """
                        insert into videoprogress(user_id,kp_id,resource_id,watched_seconds,duration_seconds,last_position_seconds,completed,updated_at)
                        values(%s,%s,%s,%s,%s,%s,%s,%s)
                        on duplicate key update watched_seconds=values(watched_seconds), duration_seconds=values(duration_seconds),
                        last_position_seconds=values(last_position_seconds), completed=values(completed), updated_at=values(updated_at)
                        """,
                        (user_id, kp_id, resources[0], watched, duration, watched, int(ratio >= 0.82), event_base),
                    )

                if value >= 0.25:
                    payload = {
                        "kp_code": code,
                        "kp_title": title,
                        "chapter": chapter,
                        "mastery": value,
                        "profile": profile["label"],
                    }
                    cur.execute(
                        """
                        insert into learningbehaviorevent(user_id,course_id,kp_id,event_type,value_json,created_at)
                        values(%s,%s,%s,%s,%s,%s)
                        """,
                        (user_id, course_id, kp_id, "study_session", json.dumps(payload, ensure_ascii=False), event_base),
                    )

            course_mastery = round(sum(mastered_values) / len(mastered_values), 3)
            for order, code in enumerate(PATH_CODES.get(username, []), 1):
                item = kp_by_code.get(code)
                if item is None:
                    continue
                path_kp_id, title, chapter = item
                payload = {
                    "subject": SUBJECT,
                    "grade": GRADE,
                    "kp_id": path_kp_id,
                    "kp_code": code,
                    "kp_title": title,
                    "chapter": chapter,
                    "source": "seed_three_high_math_student_profiles",
                    "order": order,
                    "profile": profile["label"],
                }
                cur.execute(
                    """
                    insert into learningbehaviorevent(user_id,course_id,kp_id,event_type,value_json,created_at)
                    values(%s,%s,%s,'path_choice',%s,%s)
                    """,
                    (
                        user_id,
                        course_id,
                        path_kp_id,
                        json.dumps(payload, ensure_ascii=False),
                        NOW - timedelta(days=max(1, 28 - order)),
                    ),
                )
            portrait = {
                "画像": profile["label"],
                "主要证据": profile["reason"],
                "课程": SUBJECT,
                "已覆盖知识点": sum(1 for v in mastered_values if v >= 0.25),
                "薄弱知识点": sum(1 for v in mastered_values if v < 0.45),
            }
            cur.execute(
                """
                insert into learnerprofilesnapshot(
                    user_id,subject,grade,persona_type,engagement,achievement,efficiency,risk,course_mastery,
                    dynamic_score,stability,risk_level,override_source,reason_summary,portrait_summary_json,updated_at
                ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'seed',%s,%s,%s)
                """,
                (
                    user_id,
                    SUBJECT,
                    GRADE,
                    profile["persona"],
                    profile["engagement"],
                    profile["achievement"],
                    profile["efficiency"],
                    profile["risk"],
                    course_mastery,
                    round((profile["achievement"] * 0.45 + profile["engagement"] * 0.25 + profile["efficiency"] * 0.2 + (1 - profile["risk"]) * 0.1), 3),
                    profile["stability"],
                    profile["risk_level"],
                    profile["reason"],
                    json.dumps(portrait, ensure_ascii=False),
                    NOW,
                ),
            )

            stage_curves = {
                "student_demo_1": [0.34, 0.39, 0.44, 0.48, 0.52],
                "student_demo_2": [0.62, 0.72, 0.8, 0.86, 0.9],
                "student_demo_3": [0.48, 0.42, 0.5, 0.45, 0.58],
            }[username]
            for idx, (stage_id, title, order) in enumerate(stages):
                mastery = stage_curves[idx]
                trend = "上升" if idx == 0 or mastery >= stage_curves[idx - 1] else "波动"
                risk_level = profile["risk_level"] if idx >= 2 else "warning"
                dimensions = {
                    "engagement": profile["engagement"],
                    "achievement": profile["achievement"],
                    "habit": profile["stability"],
                    "efficiency": profile["efficiency"],
                    "risk": profile["risk"],
                }
                cur.execute(
                    """
                    insert into stageevaluationsnapshot(
                        user_id,course_id,stage_id,subject,grade,stage_title,stage_order,persona_type,
                        engagement,achievement,habit,characteristic,efficiency,risk,course_mastery,dynamic_score,
                        trend_label,risk_level,reason_summary,dimension_summary_json,indicator_summary_json,
                        enabled_dimensions_json,updated_at
                    ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on duplicate key update persona_type=values(persona_type), engagement=values(engagement),
                    achievement=values(achievement), habit=values(habit), characteristic=values(characteristic),
                    efficiency=values(efficiency), risk=values(risk), course_mastery=values(course_mastery),
                    dynamic_score=values(dynamic_score), trend_label=values(trend_label), risk_level=values(risk_level),
                    reason_summary=values(reason_summary), dimension_summary_json=values(dimension_summary_json),
                    indicator_summary_json=values(indicator_summary_json), enabled_dimensions_json=values(enabled_dimensions_json),
                    updated_at=values(updated_at)
                    """,
                    (
                        user_id,
                        course_id,
                        stage_id,
                        SUBJECT,
                        GRADE,
                        title,
                        order,
                        profile["persona"],
                        profile["engagement"],
                        profile["achievement"],
                        profile["stability"],
                        0.72 if username == "student_demo_2" else 0.48 if username == "student_demo_1" else 0.4,
                        profile["efficiency"],
                        profile["risk"],
                        mastery,
                        round(mastery * 0.55 + profile["engagement"] * 0.25 + profile["efficiency"] * 0.2, 3),
                        trend,
                        risk_level,
                        profile["reason"],
                        json.dumps(dimensions, ensure_ascii=False),
                        json.dumps({"profile": profile["label"], "stage": title}, ensure_ascii=False),
                        json.dumps({"achievement": True, "engagement": True, "habit": True, "risk": True}, ensure_ascii=False),
                        NOW - timedelta(days=5 - idx),
                    ),
                )

            cur.execute(
                """
                insert into teacherfinalscoreconfirmation(
                    user_id,course_id,subject,grade,suggested_score,confirmed_score,confirmed_level,comment,
                    recommendation_summary,confirmed_by,confirmed_at,updated_at
                ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,'system-seed',%s,%s)
                """,
                (
                    user_id,
                    course_id,
                    SUBJECT,
                    GRADE,
                    round(course_mastery * 100, 1),
                    round(course_mastery * 100, 1),
                    "优秀" if course_mastery >= 0.82 else "良好" if course_mastery >= 0.62 else "需提升",
                    profile["reason"],
                    f"{profile['label']}：建议按画像生成差异化学习路径。",
                    NOW,
                    NOW,
                ),
            )

            print(f"seeded {username} {full_name}: {profile['label']} mastery={course_mastery}")

        conn.commit()
        print("done")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
