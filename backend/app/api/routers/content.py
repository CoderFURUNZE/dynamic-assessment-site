import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import EvalConfig, LearningResource, Quiz, QuizAttempt, QuizItem, VideoProgress
from app.db.session import get_session
from app.schemas.content import (
    QuizOut,
    ResourceVisitIn,
    QuizSubmitIn,
    QuizSubmitOut,
    ResourceOut,
    VideoProgressIn,
    VideoProgressOut,
)
from app.services.eval import upsert_mastery
from app.services.learner_profile import log_behavior_event, recalculate_profile_snapshot
from app.services.resource_files import build_resource_payload

router = APIRouter(prefix="/content", tags=["content"])


def _get_video_complete_ratio(session: Session, *, subject: str, grade: str) -> float:
    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == grade)).first()
    if cfg is None:
        return 0.8
    window = json.loads(cfg.window_json)
    return float(window.get("video_complete_ratio", 0.8))


@router.get("/resources", response_model=list[ResourceOut])
def list_resources(
    kp_id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    res = session.exec(select(LearningResource).where(LearningResource.kp_id == kp_id)).all()
    return [ResourceOut(**build_resource_payload(r)) for r in res if r.id is not None]


@router.post("/resource/visit")
def track_resource_visit(
    payload: ResourceVisitIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    resource = session.get(LearningResource, payload.resource_id)
    if resource is None or resource.kp_id != payload.kp_id:
        raise HTTPException(status_code=400, detail="Invalid resource")
    event_type = "resource_download" if str(payload.action or "").strip() == "download" else "resource_visit"
    log_behavior_event(
        session,
        user_id=user.id,
        event_type=event_type,
        subject=resource.subject,
        grade=resource.grade,
        kp_id=resource.kp_id,
        payload={"resource_id": int(resource.id), "resource_type": resource.type.value},
    )
    recalculate_profile_snapshot(
        session,
        user_id=user.id,
        subject=resource.subject,
        grade=resource.grade,
        refresh_mastery=False,
        persist=True,
    )
    return {"ok": True}


@router.get("/quiz/{kp_id}", response_model=QuizOut)
def get_quiz(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    items = session.exec(select(QuizItem).where(QuizItem.quiz_id == quiz.id)).all()
    include_answer = getattr(user, "role", None) != "student"
    return QuizOut(
        quiz_id=quiz.id,
        kp_id=kp_id,
        items=[
            {
                "id": i.id,
                "type": i.type,
                "prompt": i.prompt,
                "options": json.loads(i.options_json),
                "answer": i.answer if include_answer else None,
                "explanation": i.explanation if include_answer else None,
            }
            for i in items
        ],
    )


@router.post("/quiz/submit", response_model=QuizSubmitOut)
def submit_quiz(
    payload: QuizSubmitIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    quiz = session.get(Quiz, payload.quiz_id)
    if quiz is None or quiz.kp_id != payload.kp_id:
        raise HTTPException(status_code=400, detail="Invalid quiz")
    items = session.exec(select(QuizItem).where(QuizItem.quiz_id == quiz.id)).all()
    item_map = {i.id: i for i in items}

    correct_count = 0
    details = []
    for ans in payload.answers:
        item = item_map.get(int(ans.get("item_id")))
        if item is None:
            continue
        answer = str(ans.get("answer", "")).strip()
        is_correct = answer.upper() == item.answer.strip().upper()
        if is_correct:
            correct_count += 1
        details.append(
            {
                "item_id": item.id,
                "correct": is_correct,
                # Always return the correct answer & hint so the student can review after submitting.
                "correct_answer": item.answer,
                "hint": item.explanation,
            }
        )

    accuracy = correct_count / max(1, len(items))
    passed = accuracy >= quiz.pass_accuracy
    session.add(
        QuizAttempt(
            user_id=user.id,
            quiz_id=quiz.id,
            kp_id=quiz.kp_id,
            score=accuracy,
            passed=passed,
            duration_ms=payload.duration_ms,
        )
    )
    session.commit()
    upsert_mastery(session, user_id=user.id, kp_id=quiz.kp_id, subject=quiz.subject, grade=quiz.grade)
    log_behavior_event(
        session,
        user_id=user.id,
        event_type="quiz_submit",
        subject=quiz.subject,
        grade=quiz.grade,
        kp_id=quiz.kp_id,
        payload={"accuracy": accuracy, "passed": passed},
    )
    recalculate_profile_snapshot(
        session,
        user_id=user.id,
        subject=quiz.subject,
        grade=quiz.grade,
        refresh_mastery=False,
        persist=True,
    )
    return QuizSubmitOut(passed=passed, accuracy=accuracy, details=details)


@router.post("/video/progress", response_model=VideoProgressOut)
def upsert_video_progress(
    payload: VideoProgressIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    resource = session.get(LearningResource, payload.resource_id)
    if resource is None or resource.kp_id != payload.kp_id or resource.type.value != "video":
        raise HTTPException(status_code=400, detail="Invalid video resource")

    progress = session.exec(
        select(VideoProgress).where(VideoProgress.user_id == user.id, VideoProgress.resource_id == payload.resource_id)
    ).first()
    if progress is None:
        progress = VideoProgress(
            user_id=user.id,
            kp_id=payload.kp_id,
            resource_id=payload.resource_id,
        )

    progress.duration_seconds = max(progress.duration_seconds, float(payload.duration_seconds or 0.0))
    progress.last_position_seconds = float(max(0.0, payload.position_seconds))
    progress.watched_seconds = float(max(0.0, progress.watched_seconds + float(payload.watched_delta_seconds or 0.0)))

    if progress.duration_seconds > 0:
        ratio = progress.watched_seconds / progress.duration_seconds
        complete_ratio = _get_video_complete_ratio(session, subject=resource.subject, grade=resource.grade)
        progress.completed = ratio >= complete_ratio
    session.add(progress)
    session.commit()
    session.refresh(progress)
    upsert_mastery(session, user_id=user.id, kp_id=progress.kp_id, subject=resource.subject, grade=resource.grade)
    log_behavior_event(
        session,
        user_id=user.id,
        event_type="video_progress",
        subject=resource.subject,
        grade=resource.grade,
        kp_id=progress.kp_id,
        payload={
            "resource_id": progress.resource_id,
            "watched_seconds": progress.watched_seconds,
            "duration_seconds": progress.duration_seconds,
            "completed": progress.completed,
        },
    )
    recalculate_profile_snapshot(
        session,
        user_id=user.id,
        subject=resource.subject,
        grade=resource.grade,
        refresh_mastery=False,
        persist=True,
    )
    return VideoProgressOut(
        kp_id=progress.kp_id,
        resource_id=progress.resource_id,
        watched_seconds=progress.watched_seconds,
        duration_seconds=progress.duration_seconds,
        completed=progress.completed,
    )


@router.get("/video/progress", response_model=list[VideoProgressOut])
def list_video_progress(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    rows = session.exec(
        select(VideoProgress).where(VideoProgress.user_id == user.id, VideoProgress.kp_id == kp_id)
    ).all()
    return [
        VideoProgressOut(
            kp_id=r.kp_id,
            resource_id=r.resource_id,
            watched_seconds=r.watched_seconds,
            duration_seconds=r.duration_seconds,
            completed=r.completed,
        )
        for r in rows
    ]
