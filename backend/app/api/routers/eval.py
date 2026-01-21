from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import KnowledgePoint, Mastery
from app.db.session import get_session
from app.schemas.eval import MasteryOut, ProfileOut
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

