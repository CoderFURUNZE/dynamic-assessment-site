from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import (
    ExpressionEvent,
    KnowledgePoint,
    Mastery,
    PracticeAttempt,
    QuizAttempt,
    ReviewSchedule,
    VideoProgress,
)
from app.db.session import get_session
from app.schemas.eval import (
    MasteryMapItem,
    MasteryOut,
    OverviewOut,
    OverviewPracticeOut,
    OverviewRecentOut,
    OverviewSummaryOut,
    ProfileOut,
)
from app.services.eval import upsert_mastery

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/mastery", response_model=MasteryOut)
def mastery(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    m = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp_id)).first()
    if m is None:
        kp = session.get(KnowledgePoint, kp_id)
        m = upsert_mastery(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
    label = "mastered" if m.value >= 0.85 else "needs_practice" if m.value >= 0.5 else "not_mastered"
    return MasteryOut(kp_id=kp_id, value=m.value, label=label)


@router.get("/profile", response_model=ProfileOut)
def profile(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kps = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
    ).all()
    mastery_map = []
    weak_points = []
    for kp in kps:
        m = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp.id)).first()
        value = m.value if m else 0.0
        mastery_map.append({"kp_id": kp.id, "value": value})
        if value < 0.5:
            weak_points.append(kp.id)
    return ProfileOut(user_id=user.id, subject=subject, grade=grade, mastery_map=mastery_map, weak_points=weak_points)


@router.get("/overview", response_model=OverviewOut)
def overview(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kps = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
    ).all()
    kp_ids = [int(k.id) for k in kps if k.id is not None]

    mastery_rows = []
    if kp_ids:
        mastery_rows = session.exec(
            select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id.in_(kp_ids))
        ).all()
    mastery_map = {int(m.kp_id): float(m.value) for m in mastery_rows}

    items: list[MasteryMapItem] = []
    for kp in kps:
        value = float(mastery_map.get(int(kp.id), 0.0)) if kp.id is not None else 0.0
        items.append(MasteryMapItem(kp_id=int(kp.id), code=kp.code, title=kp.title, mastery=value))

    total_kps = len(items)
    mastered = len([i for i in items if i.mastery >= 0.85])
    in_progress = len([i for i in items if 0.5 <= i.mastery < 0.85])
    not_mastered = len([i for i in items if i.mastery < 0.5])
    avg_mastery = (sum(i.mastery for i in items) / total_kps) if total_kps else 0.0

    weak_points = sorted(items, key=lambda x: x.mastery)[:5]

    last_practice_at = None
    last_quiz_at = None
    last_video_at = None
    last_expression_at = None
    if kp_ids:
        last_practice_at = session.exec(
            select(func.max(PracticeAttempt.created_at)).where(
                PracticeAttempt.user_id == user.id, PracticeAttempt.kp_id.in_(kp_ids)
            )
        ).one()
        last_quiz_at = session.exec(
            select(func.max(QuizAttempt.created_at)).where(
                QuizAttempt.user_id == user.id, QuizAttempt.kp_id.in_(kp_ids)
            )
        ).one()
        last_video_at = session.exec(
            select(func.max(VideoProgress.updated_at)).where(
                VideoProgress.user_id == user.id, VideoProgress.kp_id.in_(kp_ids)
            )
        ).one()
        last_expression_at = session.exec(
            select(func.max(ExpressionEvent.created_at)).where(
                ExpressionEvent.user_id == user.id, ExpressionEvent.kp_id.in_(kp_ids)
            )
        ).one()

    since = datetime.utcnow() - timedelta(days=7)
    practice_rows = []
    if kp_ids:
        practice_rows = session.exec(
            select(PracticeAttempt.correct).where(
                PracticeAttempt.user_id == user.id,
                PracticeAttempt.kp_id.in_(kp_ids),
                PracticeAttempt.created_at >= since,
            )
        ).all()
    practice_total = len(practice_rows)
    practice_correct = len([r for r in practice_rows if bool(r)])
    practice_accuracy = (practice_correct / practice_total) if practice_total else 0.0
    review_due = 0
    if kp_ids:
        review_due = int(
            session.exec(
                select(func.count()).select_from(ReviewSchedule).where(
                    ReviewSchedule.user_id == user.id,
                    ReviewSchedule.kp_id.in_(kp_ids),
                    ReviewSchedule.due_at <= datetime.utcnow(),
                )
            ).one()
            or 0
        )

    return OverviewOut(
        subject=subject,
        grade=grade,
        summary=OverviewSummaryOut(
            total_kps=total_kps,
            mastered=mastered,
            in_progress=in_progress,
            not_mastered=not_mastered,
            avg_mastery=avg_mastery,
        ),
        mastery_map=items,
        weak_points=weak_points,
        recent_activity=OverviewRecentOut(
            last_practice_at=last_practice_at.isoformat() if last_practice_at else None,
            last_quiz_at=last_quiz_at.isoformat() if last_quiz_at else None,
            last_video_at=last_video_at.isoformat() if last_video_at else None,
            last_expression_at=last_expression_at.isoformat() if last_expression_at else None,
        ),
        practice_7d=OverviewPracticeOut(
            total=practice_total,
            correct=practice_correct,
            accuracy=practice_accuracy,
        ),
        review_due=review_due,
    )
