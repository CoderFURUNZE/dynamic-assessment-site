from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.models import (  # noqa: E402
    Course,
    CourseStage,
    Enrollment,
    EnrollmentStatus,
    KpQuestionAssignment,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    PersonaType,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    RecommendationLog,
    ReviewSchedule,
    StageEvaluationSnapshot,
    StageImportBatch,
    StageImportRecord,
    StageMetricType,
    StageTeacherFeedback,
    User,
)
from app.db.session import engine, init_db  # noqa: E402
from app.services.eval import upsert_mastery  # noqa: E402
from app.services.learner_profile import sync_profile_snapshot_from_stage  # noqa: E402


SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM-MIDTERM"
NOW = datetime(2026, 4, 27, 10, 45, 0)

ABILITY_TAGS = [
    "函数建模",
    "极限推理",
    "符号运算",
    "图像分析",
    "综合应用",
]
LITERACY_TAGS = [
    "数学抽象",
    "逻辑推理",
    "数学运算",
    "直观想象",
    "问题解决",
]

STUDENT_PROFILES = {
    "student_demo_1": {
        "persona": PersonaType.struggling,
        "scores": [0.48, 0.53, 0.58, 0.62, 0.65, 0.68, 0.70, 0.72],
        "mastery_base": 0.50,
        "teacher": "基础概念正在补齐，建议继续完成函数、极限和求导基础题，优先保持学习连续性。",
        "target_code": "HM-MID-04",
        "reason": "函数基础、极限直观与极限运算已逐步达标，下一步进入连续性判断。",
    },
    "student_demo_2": {
        "persona": PersonaType.steady,
        "scores": [0.58, 0.63, 0.66, 0.70, 0.74, 0.77, 0.80, 0.82],
        "mastery_base": 0.62,
        "teacher": "主线推进稳定，建议在连续性和导数部分增加综合题训练，保持当前节奏。",
        "target_code": "HM-MID-A2",
        "reason": "主线知识点掌握稳定，系统推荐继续推进到求导法则。",
    },
    "student_demo_3": {
        "persona": PersonaType.smart,
        "scores": [0.68, 0.72, 0.76, 0.80, 0.84, 0.87, 0.90, 0.92],
        "mastery_base": 0.75,
        "teacher": "综合应用能力较强，可直接展示积分应用冲刺路径，同时保留错题复盘。",
        "target_code": "HM-MID-B3",
        "reason": "前置节点掌握充分，系统推荐冲刺积分应用终点。",
    },
}

STAGE_TITLES = [
    "第 1 次评价",
    "第 2 次评价",
    "第 3 次评价",
    "第 4 次评价",
    "第 5 次评价",
    "第 6 次评价",
    "第 7 次评价",
    "第 8 次评价",
]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 4)))


def _json(payload: dict | list) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _course(session: Session) -> Course:
    course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
    if course is None:
        course = Course(code=COURSE_CODE, title=SUBJECT, description="中期答辩演示课程", active=True)
    course.title = SUBJECT
    course.active = True
    course.lifecycle_status = "active"
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _students(session: Session) -> list[User]:
    rows = []
    for username in STUDENT_PROFILES:
        student = session.exec(select(User).where(User.username == username)).first()
        if student is not None and student.id is not None:
            rows.append(student)
    if not rows:
        raise RuntimeError("未找到 student_demo_1/2/3，请先运行中期演示学生种子脚本。")
    return rows


def _ensure_enrollments(session: Session, *, course: Course, students: list[User]) -> None:
    for student in students:
        row = session.exec(
            select(Enrollment).where(Enrollment.course_id == int(course.id), Enrollment.student_id == int(student.id))
        ).first()
        if row is None:
            row = Enrollment(course_id=int(course.id), student_id=int(student.id), status=EnrollmentStatus.active)
        row.status = EnrollmentStatus.active
        session.add(row)
    session.commit()


def _ensure_stages(session: Session, *, course: Course) -> list[CourseStage]:
    stages: list[CourseStage] = []
    base = NOW - timedelta(days=56)
    for index, title in enumerate(STAGE_TITLES, start=1):
        stage = session.exec(
            select(CourseStage).where(CourseStage.course_id == int(course.id), CourseStage.stage_order == index)
        ).first()
        if stage is None:
            stage = CourseStage(course_id=int(course.id), subject=SUBJECT, grade=GRADE, stage_order=index)
        stage.subject = SUBJECT
        stage.grade = GRADE
        stage.title = title
        stage.starts_at = base + timedelta(days=(index - 1) * 7)
        stage.ends_at = base + timedelta(days=index * 7 - 1)
        stage.description = f"中期答辩演示阶段 {index}，用于展示学习画像、动态评价与路径推荐。"
        session.add(stage)
        stages.append(stage)
    session.commit()
    for stage in stages:
        session.refresh(stage)
    return stages


def _reset_demo_rows(session: Session, *, course: Course, students: list[User], kp_ids: list[int]) -> None:
    user_ids = [int(s.id) for s in students if s.id is not None]
    stage_ids = [
        int(row.id)
        for row in session.exec(select(CourseStage).where(CourseStage.course_id == int(course.id))).all()
        if row.id is not None
    ]
    if stage_ids:
        session.exec(delete(StageTeacherFeedback).where(StageTeacherFeedback.user_id.in_(user_ids), StageTeacherFeedback.stage_id.in_(stage_ids)))
        session.exec(delete(StageEvaluationSnapshot).where(StageEvaluationSnapshot.user_id.in_(user_ids), StageEvaluationSnapshot.stage_id.in_(stage_ids)))
        session.exec(delete(StageImportRecord).where(StageImportRecord.user_id.in_(user_ids), StageImportRecord.stage_id.in_(stage_ids)))
        session.exec(delete(StageImportBatch).where(StageImportBatch.course_id == int(course.id), StageImportBatch.stage_id.in_(stage_ids)))
    if kp_ids:
        session.exec(delete(PracticeAttempt).where(PracticeAttempt.user_id.in_(user_ids), PracticeAttempt.kp_id.in_(kp_ids)))
        session.exec(delete(QuizAttempt).where(QuizAttempt.user_id.in_(user_ids), QuizAttempt.kp_id.in_(kp_ids)))
        session.exec(delete(ReviewSchedule).where(ReviewSchedule.user_id.in_(user_ids), ReviewSchedule.kp_id.in_(kp_ids)))
        session.exec(delete(LearningBehaviorEvent).where(LearningBehaviorEvent.user_id.in_(user_ids), LearningBehaviorEvent.kp_id.in_(kp_ids)))
        session.exec(delete(Mastery).where(Mastery.user_id.in_(user_ids), Mastery.kp_id.in_(kp_ids)))
    session.exec(delete(RecommendationLog).where(RecommendationLog.user_id.in_(user_ids), RecommendationLog.subject == SUBJECT, RecommendationLog.grade == GRADE))
    session.commit()


def _tag_kps(session: Session, *, kps: list[KnowledgePoint]) -> None:
    for index, kp in enumerate(kps):
        kp.ability_tag = ",".join([ABILITY_TAGS[index % len(ABILITY_TAGS)], ABILITY_TAGS[(index + 2) % len(ABILITY_TAGS)]])
        kp.literacy_tag = ",".join([LITERACY_TAGS[index % len(LITERACY_TAGS)], LITERACY_TAGS[(index + 1) % len(LITERACY_TAGS)]])
        session.add(kp)
    session.commit()


def _prepare_questions(session: Session, *, kps: list[KnowledgePoint]) -> dict[int, list[Question]]:
    result: dict[int, list[Question]] = {}
    levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
    for kp in kps:
        assigned_ids = [
            int(row.question_id)
            for row in session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == int(kp.id))).all()
            if row.question_id is not None
        ]
        questions = []
        if assigned_ids:
            questions = session.exec(select(Question).where(Question.id.in_(assigned_ids))).all()
        if not questions:
            questions = session.exec(select(Question).where(Question.kp_id == int(kp.id))).all()
        for index, question in enumerate(questions):
            question.kp_id = int(kp.id)
            question.subject = SUBJECT
            question.grade = GRADE
            question.cognitive_level = levels[index % len(levels)]
            question.ability_subtags = kp.ability_tag
            session.add(question)
        result[int(kp.id)] = list(questions[:8])
    session.commit()
    return result


def _dimension_rows(score: float) -> tuple[list[dict], list[dict], dict]:
    engagement = _clamp(score + 0.02)
    achievement = _clamp(score + 0.06)
    habit = _clamp(score - 0.01)
    characteristic = _clamp(score + 0.03)
    dimensions = [
        {"dimension_title": "学习投入", "score": engagement, "available": True},
        {"dimension_title": "学习成效", "score": achievement, "available": True},
        {"dimension_title": "学习习惯", "score": habit, "available": True},
        {"dimension_title": "学习特征", "score": characteristic, "available": True},
    ]
    indicators = [
        {
            "title": "资源学习完成度",
            "score": engagement,
            "available": True,
            "source_type": "auto",
            "weight": 0.25,
            "score_source": "stage_inference",
            "formula_text": "资源访问、资料学习与连续学习行为综合计算。",
            "source_detail": "学习资源访问记录",
            "evidence_metrics": [{"metric_label": "资源访问", "metric_percent": round(engagement * 100), "weight": 0.4}],
        },
        {
            "title": "练习与小测表现",
            "score": achievement,
            "available": True,
            "source_type": "auto",
            "weight": 0.35,
            "score_source": "stage_inference",
            "formula_text": "练习正确率、小测通过率和高阶题表现共同计算。",
            "source_detail": "练习/小测记录",
            "evidence_metrics": [{"metric_label": "正确率", "metric_percent": round(achievement * 100), "weight": 0.5}],
        },
        {
            "title": "按时完成与学习连续性",
            "score": habit,
            "available": True,
            "source_type": "imported",
            "weight": 0.2,
            "score_source": "stage_inference",
            "formula_text": "由阶段任务按时率、出勤与连续学习天数估算。",
            "source_detail": "阶段导入数据",
            "evidence_metrics": [{"metric_label": "按时率", "metric_percent": round(habit * 100), "weight": 0.4}],
        },
        {
            "title": "主动复盘与拓展",
            "score": characteristic,
            "available": True,
            "source_type": "teacher",
            "weight": 0.2,
            "score_source": "teacher_input",
            "formula_text": "教师结合错题复盘、拓展任务与课堂表现补充评价。",
            "source_detail": "教师阶段评价",
            "evidence_metrics": [{"metric_label": "拓展完成", "metric_percent": round(characteristic * 100), "weight": 0.3}],
        },
    ]
    metrics = {
        "activity_frequency": engagement,
        "study_duration": _clamp(score + 0.05),
        "completion": _clamp(score + 0.03),
        "attendance_participation": _clamp(score + 0.04),
        "assignment_score": achievement,
        "quiz_score": _clamp(score + 0.05),
        "task_score": _clamp(score + 0.02),
        "stage_mastery": _clamp(score + 0.01),
        "on_time_rate": habit,
        "attendance_rate": _clamp(score + 0.02),
        "continuity": _clamp(score - 0.02),
        "participation": characteristic,
        "task_completion": _clamp(score + 0.04),
        "resource_initiative": _clamp(score + 0.03),
        "portrait_dimensions": dimensions,
    }
    return dimensions, indicators, metrics


def _create_stage_batches_and_records(
    session: Session,
    *,
    course: Course,
    stages: list[CourseStage],
    students: list[User],
    kps: list[KnowledgePoint],
) -> None:
    metrics = [
        StageMetricType.assignment,
        StageMetricType.quiz,
        StageMetricType.attendance,
        StageMetricType.task,
        StageMetricType.participation,
    ]
    for stage in stages:
        for metric_type in metrics:
            batch = StageImportBatch(
                course_id=int(course.id),
                stage_id=int(stage.id),
                subject=SUBJECT,
                grade=GRADE,
                metric_type=metric_type,
                file_name=f"{stage.title}_{metric_type.value}_demo.csv",
                uploaded_by="teacher_demo",
                total_rows=len(students) * min(3, len(kps)),
                success_rows=len(students) * min(3, len(kps)),
                failed_rows=0,
                error_json="[]",
                created_at=stage.ends_at or NOW,
            )
            session.add(batch)
            session.flush()
            for student_index, student in enumerate(students):
                profile = STUDENT_PROFILES[student.username]
                score = profile["scores"][stage.stage_order - 1]
                for kp in kps[:3]:
                    session.add(
                        StageImportRecord(
                            batch_id=int(batch.id),
                            course_id=int(course.id),
                            stage_id=int(stage.id),
                            user_id=int(student.id),
                            kp_id=int(kp.id),
                            subject=SUBJECT,
                            grade=GRADE,
                            metric_type=metric_type,
                            score_value=_clamp(score + 0.02 * student_index),
                            completion_value=_clamp(score + 0.04),
                            duration_minutes=28 + stage.stage_order * 3 + student_index * 2,
                            attendance_value=_clamp(score + 0.03),
                            submitted_on_time=score >= 0.58,
                            status="completed",
                            note=f"{student.full_name} {stage.title} {metric_type.value} 演示记录",
                            happened_at=(stage.ends_at or NOW) - timedelta(hours=student_index),
                            raw_json=_json({"demo": True, "stage": stage.title, "student": student.username}),
                        )
                    )
    session.commit()


def _create_stage_snapshots(session: Session, *, course: Course, stages: list[CourseStage], students: list[User]) -> None:
    for student in students:
        profile = STUDENT_PROFILES[student.username]
        previous = None
        for stage in stages:
            score = float(profile["scores"][stage.stage_order - 1])
            trend = "进步" if previous is None or score > previous + 0.015 else "持平"
            previous = score
            dimensions, indicators, metrics = _dimension_rows(score)
            snapshot = StageEvaluationSnapshot(
                user_id=int(student.id),
                course_id=int(course.id),
                stage_id=int(stage.id),
                subject=SUBJECT,
                grade=GRADE,
                stage_title=stage.title,
                stage_order=int(stage.stage_order),
                persona_type=profile["persona"],
                engagement=_clamp(score + 0.02),
                achievement=_clamp(score + 0.06),
                habit=_clamp(score - 0.01),
                characteristic=_clamp(score + 0.03),
                efficiency=_clamp(score + 0.01),
                risk=_clamp(1.0 - score),
                course_mastery=_clamp(score + 0.03),
                dynamic_score=_clamp(score),
                trend_label=trend,
                risk_level="优秀" if score >= 0.85 else "良好" if score >= 0.72 else "预警",
                reason_summary=f"{stage.title}：资源学习、练习正确率和阶段导入数据均已纳入动态评价，综合得分 {round(score * 100)}%。",
                dimension_summary_json=_json(metrics),
                indicator_summary_json=_json({"portrait_indicators": indicators}),
                enabled_dimensions_json=_json(
                    {
                        "engagement": True,
                        "achievement": True,
                        "habit": True,
                        "characteristic": True,
                    }
                ),
                updated_at=(stage.ends_at or NOW) + timedelta(hours=2),
            )
            session.add(snapshot)
        latest_stage = stages[-1]
        session.add(
            StageTeacherFeedback(
                user_id=int(student.id),
                course_id=int(course.id),
                stage_id=int(latest_stage.id),
                subject=SUBJECT,
                grade=GRADE,
                feedback_tag="中期建议",
                comment=profile["teacher"],
                updated_by="teacher_demo",
                updated_at=NOW,
            )
        )
    session.commit()
    for student in students:
        sync_profile_snapshot_from_stage(session, user_id=int(student.id), subject=SUBJECT, grade=GRADE, persist=True)


def _create_learning_records(
    session: Session,
    *,
    course: Course,
    students: list[User],
    kps: list[KnowledgePoint],
    questions_by_kp: dict[int, list[Question]],
) -> None:
    for student_index, student in enumerate(students):
        profile = STUDENT_PROFILES[student.username]
        base = float(profile["mastery_base"])
        for kp_index, kp in enumerate(kps):
            kp_id = int(kp.id)
            target = _clamp(base + 0.035 * kp_index)
            if student.username == "student_demo_1" and kp_index > 6:
                target = _clamp(0.45 + 0.02 * (kp_index % 3))
            if student.username == "student_demo_2" and kp_index > 8:
                target = _clamp(0.58 + 0.03 * (kp_index % 4))
            questions = questions_by_kp.get(kp_id, [])[:6]
            for q_index, question in enumerate(questions):
                correct = (q_index / max(1, len(questions))) <= target
                session.add(
                    PracticeAttempt(
                        user_id=int(student.id),
                        question_id=int(question.id),
                        kp_id=kp_id,
                        correct=bool(correct),
                        self_report="sure" if correct else "unsure",
                        duration_ms=36000 + q_index * 5000 + student_index * 2000,
                        created_at=NOW - timedelta(days=(kp_index % 10) + q_index, hours=student_index),
                    )
                )
            quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
            if quiz is not None and quiz.id is not None:
                score = _clamp(target + 0.08)
                session.add(
                    QuizAttempt(
                        user_id=int(student.id),
                        quiz_id=int(quiz.id),
                        kp_id=kp_id,
                        score=score,
                        passed=score >= 0.7,
                        duration_ms=180000 + kp_index * 5000,
                        created_at=NOW - timedelta(days=(kp_index % 8) + 1, minutes=student_index * 10),
                    )
                )
            resource = session.exec(
                select(LearningResource).where(LearningResource.kp_id == kp_id).order_by(LearningResource.id)
            ).first()
            if resource is not None and resource.id is not None:
                for event_index, action in enumerate(["resource_visit", "resource_visit", "resource_download"]):
                    session.add(
                        LearningBehaviorEvent(
                            user_id=int(student.id),
                            course_id=int(course.id),
                            kp_id=kp_id,
                            event_type=action,
                            value_json=_json({"resource_id": int(resource.id), "resource_type": resource.type.value}),
                            created_at=NOW - timedelta(days=(kp_index % 12) + event_index, hours=student_index),
                        )
                    )
            for event_index, event_type in enumerate(["login", "course_view", "practice_view", "recommendation_click"]):
                session.add(
                    LearningBehaviorEvent(
                        user_id=int(student.id),
                        course_id=int(course.id),
                        kp_id=kp_id,
                        event_type=event_type,
                        value_json=_json({"kp_code": kp.code, "demo": True}),
                        created_at=NOW - timedelta(days=(event_index + kp_index) % 14, minutes=kp_index * 3),
                    )
                )
            if questions:
                session.add(
                    ReviewSchedule(
                        user_id=int(student.id),
                        question_id=int(questions[0].id),
                        kp_id=kp_id,
                        interval_days=7,
                        due_at=NOW + timedelta(days=3),
                        last_result="correct" if target >= 0.7 else "wrong",
                        created_at=NOW - timedelta(days=5),
                        updated_at=NOW - timedelta(days=1),
                    )
                )
        session.commit()
        for kp in kps:
            upsert_mastery(session, user_id=int(student.id), kp_id=int(kp.id), subject=SUBJECT, grade=GRADE)
        session.commit()


def _create_recommendations(session: Session, *, students: list[User], kps: list[KnowledgePoint]) -> None:
    by_code = {kp.code: kp for kp in kps}
    for student in students:
        profile = STUDENT_PROFILES[student.username]
        target = by_code.get(profile["target_code"]) or kps[min(3, len(kps) - 1)]
        source = kps[0]
        payload = {
            "target_kp": {"id": int(target.id), "code": target.code, "title": target.title, "chapter": target.chapter},
            "reason_summary": profile["reason"],
            "student_message": profile["reason"],
            "recommendation_stage_label": "中期演示推荐",
            "recommendation_source": "midterm_report_enriched_seed",
        }
        session.add(
            RecommendationLog(
                user_id=int(student.id),
                subject=SUBJECT,
                grade=GRADE,
                source_kp_id=int(source.id),
                target_kp_id=int(target.id),
                persona_type=profile["persona"],
                reason_summary=profile["reason"],
                payload_json=_json(payload),
                created_at=NOW,
            )
        )
    session.commit()


def run() -> None:
    init_db()
    with Session(engine) as session:
        course = _course(session)
        students = _students(session)
        _ensure_enrollments(session, course=course, students=students)
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE, KnowledgePoint.code.startswith("HM-MID-"))
            .order_by(KnowledgePoint.code)
        ).all()
        if not kps:
            raise RuntimeError("未找到高等数学 HM-MID-* 知识图谱节点。")
        _reset_demo_rows(session, course=course, students=students, kp_ids=[int(kp.id) for kp in kps])
        _tag_kps(session, kps=kps)
        questions_by_kp = _prepare_questions(session, kps=kps)
        stages = _ensure_stages(session, course=course)
        _create_stage_batches_and_records(session, course=course, stages=stages, students=students, kps=kps)
        _create_learning_records(session, course=course, students=students, kps=kps, questions_by_kp=questions_by_kp)
        _create_stage_snapshots(session, course=course, stages=stages, students=students)
        _create_recommendations(session, students=students, kps=kps)
        print("已补齐中期答辩学习报告演示数据：")
        print(f"- 学生 {len(students)} 人")
        print(f"- 阶段 {len(stages)} 个")
        print(f"- 知识点 {len(kps)} 个，已补能力/素养标签")
        print("- 已补练习、小测、资源访问、行为时间线、阶段快照、教师建议和推荐记录")


if __name__ == "__main__":
    run()
