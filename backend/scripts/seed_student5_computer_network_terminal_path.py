from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.seed_student4_computer_network_full_path as seed
from sqlmodel import Session, select

from app.db.models import (
    Course,
    CourseCompletionRecord,
    KnowledgeEdge,
    KnowledgePoint,
    LearnerProfileSnapshot,
    LearningBehaviorEvent,
    Mastery,
    PracticeAttempt,
    QuizAttempt,
    RelationType,
    StageEvaluationSnapshot,
    VideoProgress,
)
from app.db.session import engine
from app.services.learner_profile import recalculate_stage_snapshots_for_stage, sync_profile_snapshot_from_stage


USERNAME = "student5"
PASSWORD = "123456"
FULL_NAME = "学生5"
STUDENT_NO = "2026005"
CLASS_NAME = "计算机网络演示班"
SEED_USER = "seed_student5_terminal_path"


def prerequisite_closure_path(kps: list[KnowledgePoint], edges: list[KnowledgeEdge]) -> list[KnowledgePoint]:
    kp_by_id = {int(kp.id): kp for kp in kps if kp.id is not None}
    terminal = next((kp for kp in kps if kp.is_terminal or kp.title == "课程综合达标"), None)
    if terminal is None or terminal.id is None:
        raise RuntimeError("terminal kp not found")

    parents: dict[int, list[int]] = defaultdict(list)
    children: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        if edge.relation_type != RelationType.prerequisite:
            continue
        prereq_id = int(edge.prereq_id)
        next_id = int(edge.next_id)
        if prereq_id not in kp_by_id or next_id not in kp_by_id:
            continue
        parents[next_id].append(prereq_id)
        children[prereq_id].append(next_id)

    required: set[int] = set()
    stack = [int(terminal.id)]
    while stack:
        current = stack.pop()
        if current in required:
            continue
        required.add(current)
        stack.extend(parents.get(current, []))

    indegree = {kp_id: 0 for kp_id in required}
    for prereq_id in required:
        for next_id in children.get(prereq_id, []):
            if next_id in required:
                indegree[next_id] += 1

    queue = deque(sorted(kp_id for kp_id, value in indegree.items() if value == 0))
    ordered: list[int] = []
    while queue:
        current = queue.popleft()
        ordered.append(current)
        for next_id in sorted(children.get(current, [])):
            if next_id not in required:
                continue
            indegree[next_id] -= 1
            if indegree[next_id] == 0:
                queue.append(next_id)

    return [kp_by_id[kp_id] for kp_id in ordered if kp_id in kp_by_id]


def configure_seed_module() -> None:
    seed.USERNAME = USERNAME
    seed.PASSWORD = PASSWORD
    seed.FULL_NAME = FULL_NAME
    seed.STUDENT_NO = STUDENT_NO
    seed.CLASS_NAME = CLASS_NAME
    seed.SEED_USER = SEED_USER


def main() -> None:
    configure_seed_module()
    with Session(engine) as session:
        course = session.exec(select(Course).where(Course.code == seed.COURSE_CODE)).first()
        if course is None or course.id is None:
            raise RuntimeError(f"course not found: {seed.COURSE_CODE}")

        stages = session.exec(
            select(seed.CourseStage)
            .where(seed.CourseStage.course_id == int(course.id), seed.CourseStage.subject == seed.SUBJECT, seed.CourseStage.grade == seed.GRADE)
            .order_by(seed.CourseStage.stage_order)
        ).all()
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == seed.SUBJECT, KnowledgePoint.grade == seed.GRADE)
            .order_by(KnowledgePoint.id)
        ).all()
        edges = session.exec(
            select(KnowledgeEdge).where(KnowledgeEdge.subject == seed.SUBJECT, KnowledgeEdge.grade == seed.GRADE)
        ).all()
        kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
        path = prerequisite_closure_path(list(kps), list(edges))
        if len(path) >= len(kps):
            raise RuntimeError("student5 path unexpectedly covers every graph node")

        user = seed.upsert_student(session)
        seed.upsert_enrollment(session, user_id=int(user.id), course_id=int(course.id))
        seed.clear_student_course_data(
            session,
            user_id=int(user.id),
            course_id=int(course.id),
            kp_ids=kp_ids,
            stage_ids=[int(stage.id) for stage in stages],
        )

        kps_by_stage = seed.seed_path_learning(session, user=user, course=course, kps=list(kps), path=path, stages=list(stages))
        seed.seed_stage_records(session, user=user, course=course, stages=list(stages), kps_by_stage=kps_by_stage)
        seed.seed_recent_followup(session, user=user, course=course, path=path)

        for stage in stages:
            recalculate_stage_snapshots_for_stage(session, stage_id=int(stage.id), user_ids=[int(user.id)], persist=True)
        snapshot = sync_profile_snapshot_from_stage(session, user_id=int(user.id), subject=seed.SUBJECT, grade=seed.GRADE, persist=True)
        if snapshot is None:
            raise RuntimeError("profile snapshot not generated")

        session.add(
            CourseCompletionRecord(
                course_id=int(course.id),
                student_id=int(user.id),
                note="未覆盖全部知识点，但已按前置闭包路径通过终点：课程综合达标。",
            )
        )
        session.commit()

        mastered = {
            int(row.kp_id)
            for row in session.exec(select(Mastery).where(Mastery.user_id == int(user.id))).all()
            if float(row.value or 0.0) >= 0.85 or row.status == "mastered"
        }
        errors = seed.validate_path(path, list(edges), mastered)
        if errors:
            raise RuntimeError("; ".join(errors[:5]))

        counts = {
            "user_id": int(user.id),
            "username": USERNAME,
            "password": PASSWORD,
            "graph_nodes": len(kps),
            "path_nodes": len(path),
            "uncovered_nodes": len(kps) - len(path),
            "terminal": path[-1].title if path else "",
            "mastery": len(mastered),
            "video_progress": len(session.exec(select(VideoProgress).where(VideoProgress.user_id == int(user.id))).all()),
            "practice_attempts": len(session.exec(select(PracticeAttempt).where(PracticeAttempt.user_id == int(user.id))).all()),
            "quiz_attempts": len(session.exec(select(QuizAttempt).where(QuizAttempt.user_id == int(user.id))).all()),
            "behavior_events": len(session.exec(select(LearningBehaviorEvent).where(LearningBehaviorEvent.user_id == int(user.id))).all()),
            "stage_snapshots": len(session.exec(select(StageEvaluationSnapshot).where(StageEvaluationSnapshot.user_id == int(user.id))).all()),
            "profile_snapshots": len(session.exec(select(LearnerProfileSnapshot).where(LearnerProfileSnapshot.user_id == int(user.id))).all()),
            "dynamic_score": round(float(snapshot.dynamic_score), 4),
            "course_mastery": round(float(snapshot.course_mastery), 4),
            "path_codes": [kp.code for kp in path],
        }
        print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
