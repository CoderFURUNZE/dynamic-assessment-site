from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import assert_student_kp_access, get_current_user
from app.db.models import KnowledgePoint
from app.db.session import get_session
from app.schemas.reco import RecommendationOut
from app.services.learner_profile import log_behavior_event
from app.services.reco import recommend_next

router = APIRouter(prefix="/reco", tags=["reco"])


def _handle_reco(
    *,
    kp_id: int,
    session: Session,
    user,
):
    if getattr(user, "role", None) == "student":
        kp = assert_student_kp_access(session, int(user.id), kp_id)
    else:
        kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Knowledge point not found")
    result = recommend_next(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
    log_behavior_event(
        session,
        user_id=user.id,
        event_type="recommendation_click",
        subject=kp.subject,
        grade=kp.grade,
        kp_id=kp_id,
        payload={"target_kp_id": result["target_kp"]["id"]},
    )
    return RecommendationOut(**result)


@router.get("", response_model=RecommendationOut)
@router.get("/", response_model=RecommendationOut)
def reco(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    return _handle_reco(kp_id=kp_id, session=session, user=user)
