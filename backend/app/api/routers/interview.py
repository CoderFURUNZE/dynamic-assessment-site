import json
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import InterviewAnswer, InterviewSession, KnowledgePoint, Question
from app.db.session import get_session
from app.schemas.interview import (
    InterviewFinishIn,
    InterviewFinishOut,
    InterviewQuestionOut,
    InterviewStartIn,
    InterviewStartOut,
    InterviewSubmitIn,
    InterviewSubmitOut,
)

router = APIRouter(prefix="/interview", tags=["interview"])


def _session_question_ids(session_row: InterviewSession) -> list[int]:
    try:
        raw = json.loads(session_row.question_ids_json or "[]")
        return [int(x) for x in raw]
    except Exception:
        return []


@router.post("/start", response_model=InterviewStartOut)
def start(
    payload: InterviewStartIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, payload.kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    count = max(1, min(50, int(payload.count)))
    duration = max(5, min(180, int(payload.duration_minutes)))

    questions = session.exec(select(Question).where(Question.kp_id == payload.kp_id)).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")

    rng = random.Random(user.id * 1009 + payload.kp_id * 97)
    rng.shuffle(questions)
    picked = questions[:count]
    q_ids = [int(q.id) for q in picked if q.id is not None]

    interview = InterviewSession(
        user_id=user.id,
        subject=kp.subject,
        grade=kp.grade,
        kp_id=payload.kp_id,
        duration_minutes=duration,
        total_questions=len(q_ids),
        question_ids_json=json.dumps(q_ids),
    )
    session.add(interview)
    session.commit()
    session.refresh(interview)

    out_questions = [
        InterviewQuestionOut(
            id=int(q.id),
            kp_id=q.kp_id,
            type=q.type,
            prompt=q.prompt,
            options=json.loads(q.options_json),
            difficulty=float(q.difficulty),
        )
        for q in picked
    ]

    return InterviewStartOut(
        session_id=interview.id,
        total=len(out_questions),
        duration_minutes=duration,
        questions=out_questions,
    )


@router.post("/submit", response_model=InterviewSubmitOut)
def submit(
    payload: InterviewSubmitIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    interview = session.get(InterviewSession, payload.session_id)
    if interview is None or interview.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if interview.completed:
        raise HTTPException(status_code=400, detail="Session already completed")

    q_ids = _session_question_ids(interview)
    if payload.question_id not in q_ids:
        raise HTTPException(status_code=400, detail="Question not in session")

    q = session.get(Question, payload.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    answer = payload.answer.strip()
    is_correct = answer.upper() == q.answer.strip().upper()

    existing = session.exec(
        select(InterviewAnswer).where(
            InterviewAnswer.session_id == interview.id, InterviewAnswer.question_id == q.id
        )
    ).first()
    if existing is None:
        existing = InterviewAnswer(
            session_id=interview.id,
            question_id=q.id,
            kp_id=q.kp_id,
            answer=answer,
            correct=is_correct,
            rationale=payload.rationale.strip(),
        )
    else:
        existing.answer = answer
        existing.correct = is_correct
        existing.rationale = payload.rationale.strip()
        existing.created_at = datetime.utcnow()

    session.add(existing)
    session.commit()
    return InterviewSubmitOut(correct=is_correct, explanation=q.explanation)


@router.post("/finish", response_model=InterviewFinishOut)
def finish(
    payload: InterviewFinishIn,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    interview = session.get(InterviewSession, payload.session_id)
    if interview is None or interview.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = session.exec(
        select(InterviewAnswer).where(InterviewAnswer.session_id == interview.id)
    ).all()
    correct = sum(1 for r in rows if r.correct)
    total = interview.total_questions or len(rows)
    accuracy = (correct / total) if total else 0.0

    interview.completed = True
    interview.completed_at = datetime.utcnow()
    session.add(interview)
    session.commit()

    return InterviewFinishOut(total=total, correct=correct, accuracy=accuracy)
