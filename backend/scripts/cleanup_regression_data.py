#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete
from sqlmodel import Session, select

from app.db.models import (
    Course,
    CourseApplication,
    CourseCompletionRecord,
    CourseNotification,
    CoursePortraitIndicatorSelection,
    CoursePrerequisite,
    CourseStage,
    Enrollment,
    LearnerPersonaOverride,
    LearnerProfileSnapshot,
    LearningBehaviorEvent,
    Mastery,
    Note,
    PracticeAttempt,
    QuestionnairePortraitIndicatorInput,
    QuizAttempt,
    RecommendationLog,
    ReviewSchedule,
    StageEvaluationSnapshot,
    StageImportBatch,
    StageImportRecord,
    StageTeacherFeedback,
    TeacherFinalScoreConfirmation,
    TeacherPortraitIndicatorInput,
    User,
    VideoProgress,
)
from app.db.session import engine


def _delete_by_ids(session: Session, model, column, ids: list[int]) -> None:
    if not ids:
        return
    session.exec(delete(model).where(column.in_(ids)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean regression-only users/courses and related records.")
    parser.add_argument("--user-prefix", default="e2e_")
    parser.add_argument("--course-prefix", default="E2E")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with Session(engine) as session:
        users = session.exec(select(User).where(User.username.startswith(args.user_prefix))).all()
        courses = session.exec(select(Course).where(Course.code.startswith(args.course_prefix))).all()

        user_ids = [int(item.id) for item in users if item.id is not None]
        course_ids = [int(item.id) for item in courses if item.id is not None]
        application_ids = [
            int(item.id)
            for item in session.exec(select(CourseApplication).where(CourseApplication.course_id.in_(course_ids))).all()
            if item.id is not None
        ] if course_ids else []
        stage_ids = [
            int(item.id)
            for item in session.exec(select(CourseStage).where(CourseStage.course_id.in_(course_ids))).all()
            if item.id is not None
        ] if course_ids else []
        batch_ids = [
            int(item.id)
            for item in session.exec(select(StageImportBatch).where(StageImportBatch.course_id.in_(course_ids))).all()
            if item.id is not None
        ] if course_ids else []

        summary = {
            "users": len(user_ids),
            "courses": len(course_ids),
            "stages": len(stage_ids),
            "stage_batches": len(batch_ids),
            "applications": len(application_ids),
        }

        if args.dry_run:
            print(f"[DRY-RUN] {summary}")
            return 0

        _delete_by_ids(session, PracticeAttempt, PracticeAttempt.user_id, user_ids)
        _delete_by_ids(session, ReviewSchedule, ReviewSchedule.user_id, user_ids)
        _delete_by_ids(session, QuizAttempt, QuizAttempt.user_id, user_ids)
        _delete_by_ids(session, Note, Note.user_id, user_ids)
        _delete_by_ids(session, VideoProgress, VideoProgress.user_id, user_ids)
        _delete_by_ids(session, Mastery, Mastery.user_id, user_ids)
        _delete_by_ids(session, LearnerProfileSnapshot, LearnerProfileSnapshot.user_id, user_ids)
        _delete_by_ids(session, LearnerPersonaOverride, LearnerPersonaOverride.user_id, user_ids)
        _delete_by_ids(session, QuestionnairePortraitIndicatorInput, QuestionnairePortraitIndicatorInput.user_id, user_ids)
        _delete_by_ids(session, TeacherPortraitIndicatorInput, TeacherPortraitIndicatorInput.user_id, user_ids)
        _delete_by_ids(session, StageEvaluationSnapshot, StageEvaluationSnapshot.user_id, user_ids)
        _delete_by_ids(session, StageTeacherFeedback, StageTeacherFeedback.user_id, user_ids)
        _delete_by_ids(session, TeacherFinalScoreConfirmation, TeacherFinalScoreConfirmation.user_id, user_ids)
        _delete_by_ids(session, LearningBehaviorEvent, LearningBehaviorEvent.user_id, user_ids)
        _delete_by_ids(session, RecommendationLog, RecommendationLog.user_id, user_ids)
        _delete_by_ids(session, CourseNotification, CourseNotification.user_id, user_ids)
        _delete_by_ids(session, Enrollment, Enrollment.student_id, user_ids)
        _delete_by_ids(session, CourseApplication, CourseApplication.student_id, user_ids)
        _delete_by_ids(session, CourseCompletionRecord, CourseCompletionRecord.student_id, user_ids)

        _delete_by_ids(session, TeacherPortraitIndicatorInput, TeacherPortraitIndicatorInput.course_id, course_ids)
        _delete_by_ids(session, QuestionnairePortraitIndicatorInput, QuestionnairePortraitIndicatorInput.course_id, course_ids)
        _delete_by_ids(session, StageEvaluationSnapshot, StageEvaluationSnapshot.course_id, course_ids)
        _delete_by_ids(session, StageTeacherFeedback, StageTeacherFeedback.course_id, course_ids)
        _delete_by_ids(session, TeacherFinalScoreConfirmation, TeacherFinalScoreConfirmation.course_id, course_ids)
        _delete_by_ids(session, LearningBehaviorEvent, LearningBehaviorEvent.course_id, course_ids)
        _delete_by_ids(session, CoursePortraitIndicatorSelection, CoursePortraitIndicatorSelection.course_id, course_ids)
        _delete_by_ids(session, Enrollment, Enrollment.course_id, course_ids)
        _delete_by_ids(session, CourseApplication, CourseApplication.course_id, course_ids)
        _delete_by_ids(session, CourseCompletionRecord, CourseCompletionRecord.course_id, course_ids)
        _delete_by_ids(session, CoursePrerequisite, CoursePrerequisite.course_id, course_ids)
        _delete_by_ids(session, CoursePrerequisite, CoursePrerequisite.prerequisite_course_id, course_ids)
        _delete_by_ids(session, StageImportRecord, StageImportRecord.batch_id, batch_ids)
        _delete_by_ids(session, StageImportRecord, StageImportRecord.stage_id, stage_ids)
        _delete_by_ids(session, StageImportBatch, StageImportBatch.id, batch_ids)
        _delete_by_ids(session, TeacherPortraitIndicatorInput, TeacherPortraitIndicatorInput.stage_id, stage_ids)
        _delete_by_ids(session, StageEvaluationSnapshot, StageEvaluationSnapshot.stage_id, stage_ids)
        _delete_by_ids(session, StageTeacherFeedback, StageTeacherFeedback.stage_id, stage_ids)
        _delete_by_ids(session, CourseStage, CourseStage.id, stage_ids)
        _delete_by_ids(session, Course, Course.id, course_ids)
        _delete_by_ids(session, User, User.id, user_ids)

        session.commit()
        print(f"[DONE] cleaned regression data: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
