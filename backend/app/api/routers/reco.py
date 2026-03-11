from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.models import KnowledgePoint
from app.db.session import get_session
from app.schemas.reco import RecommendationOut
from app.services.learner_profile import log_behavior_event
from app.services.reco import recommend_next

router = APIRouter(prefix="/reco", tags=["reco"])


@router.get("/", response_model=RecommendationOut)
def reco(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, kp_id)
    result = recommend_next(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
    log_behavior_event(
        session,
        user_id=user.id,
        event_type="recommend_click",
        subject=kp.subject,
        grade=kp.grade,
        kp_id=kp_id,
        payload={"target_kp_id": result["target_kp"]["id"]},
    )
    return RecommendationOut(**result)
