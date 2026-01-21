from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.models import KnowledgePoint
from app.db.session import get_session
from app.schemas.reco import RecommendationOut
from app.services.reco import recommend_next

router = APIRouter(prefix="/reco", tags=["reco"])


@router.get("/", response_model=RecommendationOut)
def reco(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, kp_id)
    return RecommendationOut(
        **recommend_next(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
    )

