from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import KnowledgeEdge, KnowledgePoint
from app.db.session import get_session
from app.schemas.graph import GraphPathOut, KnowledgeEdgeOut, KnowledgePointOut

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/kps", response_model=list[KnowledgePointOut])
def list_kps(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    return session.exec(
        select(KnowledgePoint).where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
    ).all()


@router.get("/edges", response_model=list[KnowledgeEdgeOut])
def list_edges(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    edges = session.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.subject == subject, KnowledgeEdge.grade == grade)
    ).all()
    return [KnowledgeEdgeOut(prereq_id=e.prereq_id, next_id=e.next_id) for e in edges]


@router.get("/path/{kp_id}", response_model=GraphPathOut)
def path(
    kp_id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    prereqs = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.next_id == kp_id)).all()
    prereq_ids = [p.prereq_id for p in prereqs]
    next_edges = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == kp_id)).all()
    next_ids = [e.next_id for e in next_edges]
    return GraphPathOut(
        kp_id=kp_id,
        prereq_chain=prereq_ids + [kp_id],
        blocked_prereqs=prereq_ids,
        next_candidates=next_ids,
    )

