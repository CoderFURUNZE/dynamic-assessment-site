from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import Note, User
from app.db.session import get_session
from app.schemas.notes import NoteCreateIn, NoteOut
from app.services.practice import practice_status

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[NoteOut])
def list_notes(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    st = practice_status(session, user_id=user.id, kp_id=kp_id)
    if not st["completed"]:
        return []

    rows = session.exec(select(Note).where(Note.kp_id == kp_id).order_by(Note.created_at.desc())).all()
    if not rows:
        return []

    user_ids = {r.user_id for r in rows}
    users = session.exec(select(User).where(User.id.in_(user_ids))).all()
    id_to_name = {u.id: u.username for u in users}
    return [
        NoteOut(
            id=r.id,
            kp_id=r.kp_id,
            author=id_to_name.get(r.user_id, "unknown"),
            content=r.content,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/", response_model=NoteOut)
def create_note(
    payload: NoteCreateIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    st = practice_status(session, user_id=user.id, kp_id=payload.kp_id)
    if not st["completed"]:
        raise HTTPException(status_code=403, detail="Complete all practice questions before posting notes")

    content = payload.content.strip()
    if len(content) < 3:
        raise HTTPException(status_code=400, detail="Note too short")

    note = Note(user_id=user.id, kp_id=payload.kp_id, content=content)
    session.add(note)
    session.commit()
    session.refresh(note)
    return NoteOut(
        id=note.id,
        kp_id=note.kp_id,
        author=user.username,
        content=note.content,
        created_at=note.created_at.isoformat(),
    )

