import json
import logging
import re
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from docx import Document
from sqlmodel import Session, select

from app.api.deps import require_role
from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    EvalConfig,
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    ResourceType,
    KpQuestionAssignment,
    ExpressionEvent,
    PracticeAttempt,
    Question,
    Quiz,
    QuizItem,
    User,
    UserRole,
)
from app.db.session import get_session
from sqlalchemy import Integer, func, or_
from app.schemas.admin import (
    KnowledgeEdgeIn,
    KnowledgeEdgeOut,
    KnowledgePointIn,
    KnowledgePointUpdateIn,
    QuestionIn,
    QuestionOut,
    AdminPracticeReportOut,
    AdminExpressionReportOut,
    UserOut,
    UserUpdateIn,
)

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("app.audit")


def _log_action(user: User | None, action: str, detail: str = "") -> None:
    if user is None:
        logger.info("actor=system action=%s detail=%s", action, detail)
        return
    try:
        logger.info("actor=%s role=%s action=%s detail=%s", user.username, user.role.value, action, detail)
    except Exception:
        logger.info("action=%s detail=%s", action, detail)


def _bilibili_embed_url(*, bvid: str, page: int) -> str:
    p = max(1, int(page))
    return f"https://player.bilibili.com/player.html?bvid={bvid}&page={p}"


def _replace_kp_video(*, session: Session, kp: KnowledgePoint, title: str, url: str) -> LearningResource:
    existing = session.exec(
        select(LearningResource).where(LearningResource.kp_id == kp.id, LearningResource.type == ResourceType.video)
    ).all()
    for r in existing:
        session.delete(r)
    session.commit()

    r = LearningResource(subject=kp.subject, grade=kp.grade, kp_id=kp.id, title=title, url=url, type=ResourceType.video)
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name.strip("._") or "video.mp4"


@router.put("/kp-video/bilibili")
def set_kp_bilibili_video(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    bvid = str(payload.get("bvid", "")).strip()
    page = int(payload.get("page", 1))
    title = str(payload.get("title", "")).strip() or f"B站视频 {bvid} P{page}"
    if not bvid:
        raise HTTPException(status_code=400, detail="bvid required")

    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    url = _bilibili_embed_url(bvid=bvid, page=page)
    r = _replace_kp_video(session=session, kp=kp, title=title, url=url)
    _log_action(_admin, "kp_video_bind_bilibili", f"kp_id={kp_id} bvid={bvid} page={page}")
    return {"ok": True, "resource_id": r.id, "url": r.url}


@router.delete("/kp-video")
def clear_kp_video(
    kp_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    existing = session.exec(
        select(LearningResource).where(LearningResource.kp_id == kp_id, LearningResource.type == ResourceType.video)
    ).all()
    for r in existing:
        session.delete(r)
    session.commit()
    _log_action(_admin, "kp_video_clear", f"kp_id={kp_id} deleted={len(existing)}")
    return {"ok": True, "deleted": len(existing)}


@router.post("/kp-video/local")
def upload_kp_video_local(
    kp_id: int = Form(...),
    title: str = Form(""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    filename = _safe_filename(file.filename or "video.mp4")
    ext = Path(filename).suffix.lower()
    if ext not in {".mp4", ".m3u8", ".m4v", ".mov"}:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    media_dir = Path(settings.media_dir)
    video_dir = media_dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_name = f"{kp_id}_{ts}_{filename}"
    dest = video_dir / stored_name
    with dest.open("wb") as f:
        f.write(file.file.read())

    final_title = title.strip() or f"本地视频：{stored_name}"
    url = f"{settings.media_url}/videos/{stored_name}"
    r = _replace_kp_video(session=session, kp=kp, title=final_title, url=url)
    _log_action(_admin, "kp_video_upload_local", f"kp_id={kp_id} file={stored_name}")
    return {"ok": True, "resource_id": r.id, "url": r.url}


@router.put("/kp-video/url")
def set_kp_video_url(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    url = str(payload.get("url", "")).strip()
    title = str(payload.get("title", "")).strip() or "自托管视频"
    if not url:
        raise HTTPException(status_code=400, detail="url required")

    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    r = _replace_kp_video(session=session, kp=kp, title=title, url=url)
    _log_action(_admin, "kp_video_bind_url", f"kp_id={kp_id} url={url}")
    return {"ok": True, "resource_id": r.id, "url": r.url}


@router.post("/users")
def create_user(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    role = payload.get("role", "student")
    full_name = payload.get("full_name", "") or ""
    student_no = payload.get("student_no", "") or ""
    class_name = payload.get("class_name", "") or ""
    phone = payload.get("phone", None)
    if not username or not password:
        raise HTTPException(status_code=400, detail="Invalid user")
    # Password format validation disabled for testing.
    exists = session.exec(select(User).where(User.username == username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    if phone:
        exists_phone = session.exec(select(User).where(User.phone == str(phone).strip())).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="Phone already exists")
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=UserRole(role),
        full_name=str(full_name),
        student_no=str(student_no),
        class_name=str(class_name),
        phone=str(phone).strip() if phone else None,
    )
    session.add(user)
    session.commit()
    _log_action(_admin, "user_create", f"username={username} role={role}")
    return {"ok": True, "user_id": user.id}

@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 15,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    total = session.exec(select(func.count()).select_from(User)).one()
    rows = session.exec(
        select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        UserOut(
            id=u.id,
            username=u.username,
            role=u.role.value,
            full_name=u.full_name,
            student_no=u.student_no,
            class_name=u.class_name,
            phone=u.phone,
            wechat_openid=u.wechat_openid,
        )
        for u in rows
    ]
    return {"items": [i.model_dump() for i in items], "total": int(total or 0), "page": page, "page_size": page_size}


@router.get("/practice/report", response_model=AdminPracticeReportOut)
def practice_report(
    user_id: int,
    kp_id: int | None = None,
    days: int = 14,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    days = max(1, min(180, int(days)))
    since = datetime.utcnow() - timedelta(days=days)

    q = (
        select(PracticeAttempt, Question)
        .join(Question, PracticeAttempt.question_id == Question.id, isouter=True)
        .where(PracticeAttempt.user_id == user_id, PracticeAttempt.created_at >= since)
    )
    if kp_id is not None:
        q = q.where(PracticeAttempt.kp_id == kp_id)
    rows = session.exec(q).all()

    total = len(rows)
    correct = sum(1 for a, _ in rows if a.correct)
    incorrect = total - correct
    accuracy = (correct / total) if total else 0.0

    buckets: dict[str, dict] = {}
    by_kp: dict[int, dict] = {}
    for attempt, _question in rows:
        day = attempt.created_at.date().isoformat()
        if day not in buckets:
            buckets[day] = {"date": day, "total": 0, "correct": 0}
        buckets[day]["total"] += 1
        if attempt.correct:
            buckets[day]["correct"] += 1

        kp = int(attempt.kp_id)
        if kp not in by_kp:
            by_kp[kp] = {"kp_id": kp, "total": 0, "correct": 0}
        by_kp[kp]["total"] += 1
        if attempt.correct:
            by_kp[kp]["correct"] += 1

    daily = []
    for day in sorted(buckets.keys()):
        b = buckets[day]
        daily.append(
            {
                "date": b["date"],
                "total": b["total"],
                "correct": b["correct"],
                "accuracy": (b["correct"] / b["total"]) if b["total"] else 0.0,
            }
        )

    kp_ids = list(by_kp.keys())
    kp_map: dict[int, KnowledgePoint] = {}
    if kp_ids:
        kps = session.exec(select(KnowledgePoint).where(KnowledgePoint.id.in_(kp_ids))).all()
        kp_map = {int(k.id): k for k in kps}
    by_kp_list = []
    for item in by_kp.values():
        kp = kp_map.get(int(item["kp_id"]))
        by_kp_list.append(
            {
                "kp_id": item["kp_id"],
                "kp_code": kp.code if kp else "",
                "kp_title": kp.title if kp else "",
                "total": item["total"],
                "correct": item["correct"],
                "accuracy": (item["correct"] / item["total"]) if item["total"] else 0.0,
            }
        )
    by_kp_list.sort(key=lambda x: x["total"], reverse=True)

    return AdminPracticeReportOut(
        user_id=user_id,
        kp_id=kp_id,
        total=total,
        correct=correct,
        incorrect=incorrect,
        accuracy=accuracy,
        daily=daily,
        by_kp=by_kp_list,
    )


@router.get("/expression/report", response_model=AdminExpressionReportOut)
def expression_report(
    user_id: int,
    kp_id: int | None = None,
    days: int = 14,
    limit: int = 200,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    days = max(1, min(180, int(days)))
    limit = max(1, min(500, int(limit)))
    since = datetime.utcnow() - timedelta(days=days)

    q = select(ExpressionEvent).where(ExpressionEvent.user_id == user_id, ExpressionEvent.created_at >= since)
    if kp_id is not None:
        q = q.where(ExpressionEvent.kp_id == kp_id)
    rows = session.exec(q.order_by(ExpressionEvent.created_at.desc()).limit(limit)).all()

    total = len(rows)
    avg_conf = (sum(r.confidence for r in rows) / total) if total else 0.0
    avg_diff = (sum(r.difficulty for r in rows) / total) if total else 0.0

    by_label: dict[str, dict] = {}
    daily: dict[str, dict] = {}
    for r in rows:
        label = r.label or "unknown"
        if label not in by_label:
            by_label[label] = {"label": label, "total": 0, "avg_confidence": 0.0, "avg_difficulty": 0.0}
        by_label[label]["total"] += 1
        by_label[label]["avg_confidence"] += r.confidence
        by_label[label]["avg_difficulty"] += r.difficulty

        day = r.created_at.date().isoformat()
        if day not in daily:
            daily[day] = {"date": day, "total": 0, "avg_confidence": 0.0, "avg_difficulty": 0.0}
        daily[day]["total"] += 1
        daily[day]["avg_confidence"] += r.confidence
        daily[day]["avg_difficulty"] += r.difficulty

    by_label_list = []
    for item in by_label.values():
        total_l = item["total"]
        by_label_list.append(
            {
                "label": item["label"],
                "total": total_l,
                "avg_confidence": item["avg_confidence"] / total_l if total_l else 0.0,
                "avg_difficulty": item["avg_difficulty"] / total_l if total_l else 0.0,
            }
        )
    by_label_list.sort(key=lambda x: x["total"], reverse=True)

    daily_list = []
    for key in sorted(daily.keys()):
        item = daily[key]
        total_d = item["total"]
        daily_list.append(
            {
                "date": item["date"],
                "total": total_d,
                "avg_confidence": item["avg_confidence"] / total_d if total_d else 0.0,
                "avg_difficulty": item["avg_difficulty"] / total_d if total_d else 0.0,
            }
        )

    items = [
        {
            "id": r.id,
            "kp_id": r.kp_id,
            "label": r.label,
            "confidence": r.confidence,
            "difficulty": r.difficulty,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]

    return AdminExpressionReportOut(
        user_id=user_id,
        kp_id=kp_id,
        total=total,
        avg_confidence=avg_conf,
        avg_difficulty=avg_diff,
        by_label=by_label_list,
        daily=daily_list,
        items=items,
    )


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        u.role = UserRole(payload.role)
    if payload.password is not None and payload.password.strip():
        pw = payload.password.strip()
        if len(pw) < 8 or not re.search(r"[A-Z]", pw) or not re.search(r"[a-z]", pw) or not re.search(r"\d", pw):
            raise HTTPException(status_code=400, detail="密码至少8位，需包含大小写字母和数字")
        u.password_hash = hash_password(pw)
    if payload.full_name is not None:
        u.full_name = payload.full_name
    if payload.student_no is not None:
        u.student_no = payload.student_no
    if payload.class_name is not None:
        u.class_name = payload.class_name
    if payload.phone is not None:
        phone = payload.phone.strip() or None
        u.phone = phone
    session.add(u)
    session.commit()
    session.refresh(u)
    _log_action(_admin, "user_update", f"user_id={user_id}")
    return UserOut(
        id=u.id,
        username=u.username,
        role=u.role.value,
        full_name=u.full_name,
        student_no=u.student_no,
        class_name=u.class_name,
        phone=u.phone,
        wechat_openid=u.wechat_openid,
    )


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(u)
    session.commit()
    _log_action(_admin, "user_delete", f"user_id={user_id} username={u.username}")
    return {"ok": True}


@router.get("/kps")
def list_kps_admin(
    subject: str | None = None,
    grade: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 15,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    q = select(KnowledgePoint).order_by(KnowledgePoint.id.desc())
    q_total = select(func.count()).select_from(KnowledgePoint)
    if subject:
        q = q.where(KnowledgePoint.subject == subject)
        q_total = q_total.where(KnowledgePoint.subject == subject)
    if grade:
        q = q.where(KnowledgePoint.grade == grade)
        q_total = q_total.where(KnowledgePoint.grade == grade)
    if keyword:
        kw = keyword.strip()
        if kw:
            q = q.where(
                or_(
                    KnowledgePoint.code.contains(kw),
                    KnowledgePoint.title.contains(kw),
                    KnowledgePoint.description.contains(kw),
                )
            )
            q_total = q_total.where(
                or_(
                    KnowledgePoint.code.contains(kw),
                    KnowledgePoint.title.contains(kw),
                    KnowledgePoint.description.contains(kw),
                )
            )
    total = session.exec(q_total).one()
    rows = session.exec(q.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [r.model_dump() for r in rows], "total": int(total or 0), "page": page, "page_size": page_size}


@router.post("/kps")
def create_kp(
    payload: KnowledgePointIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code required")
    exists = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if exists:
        raise HTTPException(status_code=400, detail="code already exists")
    kp = KnowledgePoint(
        subject=payload.subject.strip(),
        grade=payload.grade.strip(),
        code=code,
        title=payload.title.strip(),
        description=payload.description.strip(),
    )
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


@router.put("/kps/{kp_id}")
def update_kp(
    kp_id: int,
    payload: KnowledgePointUpdateIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    if payload.code is not None:
        code = payload.code.strip()
        if not code:
            raise HTTPException(status_code=400, detail="code required")
        exists = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code, KnowledgePoint.id != kp_id)).first()
        if exists:
            raise HTTPException(status_code=400, detail="code already exists")
        kp.code = code
    if payload.title is not None:
        kp.title = payload.title
    if payload.description is not None:
        kp.description = payload.description
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


@router.put("/kps/{kp_id}/practice_total")
def update_kp_practice_total(
    kp_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    raw = payload.get("practice_total", None)
    if raw is None:
        kp.practice_total = None
    else:
        try:
            val = int(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="practice_total must be an integer")
        if val < 0:
            raise HTTPException(status_code=400, detail="practice_total must be >= 0")
        kp.practice_total = val
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return {"ok": True, "kp_id": kp.id, "practice_total": kp.practice_total}


@router.delete("/kps/{kp_id}")
def delete_kp(
    kp_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")

    # Safety: block deletion if referenced.
    has_edge = session.exec(
        select(KnowledgeEdge.id).where((KnowledgeEdge.prereq_id == kp_id) | (KnowledgeEdge.next_id == kp_id))
    ).first()
    has_resource = session.exec(select(LearningResource.id).where(LearningResource.kp_id == kp_id)).first()
    has_q = session.exec(select(Question.id).where(Question.kp_id == kp_id)).first()
    if has_edge or has_resource or has_q:
        raise HTTPException(status_code=400, detail="Cannot delete: kp is referenced by edges/resources/questions")

    session.delete(kp)
    session.commit()
    return {"ok": True}


@router.get("/edges")
def list_edges_admin(
    subject: str | None = None,
    grade: str | None = None,
    page: int = 1,
    page_size: int = 15,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    q = select(KnowledgeEdge).order_by(KnowledgeEdge.id.desc())
    q_total = select(func.count()).select_from(KnowledgeEdge)
    if subject:
        q = q.where(KnowledgeEdge.subject == subject)
        q_total = q_total.where(KnowledgeEdge.subject == subject)
    if grade:
        q = q.where(KnowledgeEdge.grade == grade)
        q_total = q_total.where(KnowledgeEdge.grade == grade)
    total = session.exec(q_total).one()
    rows = session.exec(q.offset((page - 1) * page_size).limit(page_size)).all()
    items = [KnowledgeEdgeOut(id=r.id, prereq_id=r.prereq_id, next_id=r.next_id) for r in rows]
    return {"items": [i.model_dump() for i in items], "total": int(total or 0), "page": page, "page_size": page_size}


@router.post("/edges", response_model=KnowledgeEdgeOut)
def create_edge(
    payload: KnowledgeEdgeIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    if payload.prereq_id == payload.next_id:
        raise HTTPException(status_code=400, detail="Invalid edge")
    exists = session.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == payload.prereq_id, KnowledgeEdge.next_id == payload.next_id)
    ).first()
    if exists:
        return KnowledgeEdgeOut(id=exists.id, prereq_id=exists.prereq_id, next_id=exists.next_id)
    edge = KnowledgeEdge(
        subject=payload.subject,
        grade=payload.grade,
        prereq_id=payload.prereq_id,
        next_id=payload.next_id,
    )
    session.add(edge)
    session.commit()
    session.refresh(edge)
    return KnowledgeEdgeOut(id=edge.id, prereq_id=edge.prereq_id, next_id=edge.next_id)


@router.delete("/edges/{edge_id}")
def delete_edge(
    edge_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    edge = session.get(KnowledgeEdge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")
    session.delete(edge)
    session.commit()
    return {"ok": True}


@router.get("/questions")
def list_questions(
    kp_id: int | None = None,
    keyword: str | None = None,
    q_type: str | None = None,
    min_difficulty: float | None = None,
    max_difficulty: float | None = None,
    page: int = 1,
    page_size: int = 15,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    q = select(Question).order_by(Question.id.desc())
    q_total = select(func.count()).select_from(Question)
    if kp_id is not None:
        q = q.where(Question.kp_id == kp_id)
        q_total = q_total.where(Question.kp_id == kp_id)
    if keyword:
        kw = keyword.strip()
        if kw:
            q = q.where(Question.prompt.contains(kw))
            q_total = q_total.where(Question.prompt.contains(kw))
    if q_type:
        q = q.where(Question.type == q_type)
        q_total = q_total.where(Question.type == q_type)
    if min_difficulty is not None:
        q = q.where(Question.difficulty >= float(min_difficulty))
        q_total = q_total.where(Question.difficulty >= float(min_difficulty))
    if max_difficulty is not None:
        q = q.where(Question.difficulty <= float(max_difficulty))
        q_total = q_total.where(Question.difficulty <= float(max_difficulty))
    total = session.exec(q_total).one()
    rows = session.exec(q.offset((page - 1) * page_size).limit(page_size)).all()

    ids = [r.id for r in rows]
    stats_map: dict[int, dict] = {}
    if ids:
        stats = session.exec(
            select(
                PracticeAttempt.question_id,
                func.count().label("attempts"),
                func.avg(func.cast(PracticeAttempt.correct, Integer)).label("correct_rate"),
            )
            .where(PracticeAttempt.question_id.in_(ids))
            .group_by(PracticeAttempt.question_id)
        ).all()
        for qid, attempts, correct_rate in stats:
            stats_map[int(qid)] = {
                "attempts": int(attempts or 0),
                "correct_rate": float(correct_rate) if correct_rate is not None else None,
            }

    items = [
        QuestionOut(
            id=r.id,
            kp_id=r.kp_id,
            type=r.type,
            prompt=r.prompt,
            options=json.loads(r.options_json),
            answer=r.answer,
            explanation=r.explanation,
            difficulty=r.difficulty,
            source=r.source,
            tags=r.tags,
            version=r.version,
            attempts=stats_map.get(r.id, {}).get("attempts"),
            correct_rate=stats_map.get(r.id, {}).get("correct_rate"),
        )
        for r in rows
    ]
    return {"items": [i.model_dump() for i in items], "total": int(total or 0), "page": page, "page_size": page_size}


@router.get("/questions/export")
def export_questions(
    kp_id: int | None = None,
    keyword: str | None = None,
    q_type: str | None = None,
    min_difficulty: float | None = None,
    max_difficulty: float | None = None,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    q = select(Question).order_by(Question.id.desc())
    if kp_id is not None:
        q = q.where(Question.kp_id == kp_id)
    if keyword:
        kw = keyword.strip()
        if kw:
            q = q.where(Question.prompt.contains(kw))
    if q_type:
        q = q.where(Question.type == q_type)
    if min_difficulty is not None:
        q = q.where(Question.difficulty >= float(min_difficulty))
    if max_difficulty is not None:
        q = q.where(Question.difficulty <= float(max_difficulty))

    rows = session.exec(q).all()
    lines = ["id,kp_id,type,prompt,options,answer,explanation,difficulty,source,tags,version"]
    for r in rows:
        prompt = r.prompt.replace('"', "'").replace(",", "，")
        options = r.options_json.replace('"', "'").replace(",", "，")
        answer = r.answer.replace('"', "'").replace(",", "，")
        explanation = r.explanation.replace('"', "'").replace(",", "，")
        source = (r.source or "").replace('"', "'").replace(",", "，")
        tags = (r.tags or "").replace('"', "'").replace(",", "，")
        version = (r.version or "").replace('"', "'").replace(",", "，")
        lines.append(
            f"{r.id},{r.kp_id},{r.type},\"{prompt}\",\"{options}\",\"{answer}\",\"{explanation}\",{r.difficulty},\"{source}\",\"{tags}\",\"{version}\""
        )
    csv = "\n".join(lines)
    return Response(content=csv, media_type="text/csv")


@router.post("/questions/recalibrate-difficulty")
def recalibrate_question_difficulty(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = payload.get("kp_id")
    kp_id = int(kp_id) if kp_id is not None else None
    min_attempts = int(payload.get("min_attempts", 5))
    blend = float(payload.get("blend", 0.7))
    step = float(payload.get("step", 0.1))
    min_attempts = max(1, min(1000, min_attempts))
    blend = max(0.0, min(1.0, blend))
    step = max(0.01, min(0.5, step))

    q = select(Question)
    if kp_id is not None:
        q = q.where(Question.kp_id == kp_id)
    questions = session.exec(q).all()
    if not questions:
        return {"ok": True, "updated": 0}

    ids = [qq.id for qq in questions]
    stats = session.exec(
        select(
            PracticeAttempt.question_id,
            func.count().label("attempts"),
            func.avg(func.cast(PracticeAttempt.correct, Integer)).label("correct_rate"),
        )
        .where(PracticeAttempt.question_id.in_(ids))
        .group_by(PracticeAttempt.question_id)
    ).all()
    stats_map = {int(qid): (int(attempts or 0), float(cr) if cr is not None else None) for qid, attempts, cr in stats}

    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    def quantize(x: float) -> float:
        return round(x / step) * step

    updated = 0
    for qq in questions:
        attempts, correct_rate = stats_map.get(int(qq.id), (0, None))
        if attempts < min_attempts or correct_rate is None:
            continue
        estimated = clamp01(1.0 - float(correct_rate))
        new_value = blend * estimated + (1.0 - blend) * float(qq.difficulty)
        new_value = clamp01(quantize(new_value))
        if abs(float(qq.difficulty) - new_value) >= 1e-6:
            qq.difficulty = float(new_value)
            session.add(qq)
            updated += 1
    session.commit()
    return {"ok": True, "updated": updated, "min_attempts": min_attempts, "blend": blend, "step": step}


@router.get("/kp-questions")
def list_assigned_questions(
    kp_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    assigns = session.exec(
        select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id).order_by(KpQuestionAssignment.order)
    ).all()
    if not assigns:
        return []
    ids = [a.question_id for a in assigns]
    qs = session.exec(select(Question).where(Question.id.in_(ids))).all()
    qmap = {q.id: q for q in qs}
    return [
        {
            "id": a.id,
            "kp_id": a.kp_id,
            "question_id": a.question_id,
            "order": a.order,
            "type": qmap[a.question_id].type if a.question_id in qmap else "",
            "prompt": qmap[a.question_id].prompt if a.question_id in qmap else "",
        }
        for a in assigns
        if a.question_id in qmap
    ]


@router.post("/kp-questions")
def assign_questions(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    question_ids = payload.get("question_ids") or []
    if not isinstance(question_ids, list) or not question_ids:
        raise HTTPException(status_code=400, detail="question_ids required")
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    existing = session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id)).all()
    existing_ids = {e.question_id for e in existing}
    max_order = max([e.order for e in existing], default=0)
    created = 0
    for qid in question_ids:
        qid_i = int(qid)
        if qid_i in existing_ids:
            continue
        max_order += 1
        session.add(KpQuestionAssignment(kp_id=kp_id, question_id=qid_i, order=max_order))
        created += 1
    session.commit()
    return {"ok": True, "created": created}


@router.put("/kp-questions/reorder")
def reorder_questions(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    ordered_ids = payload.get("ordered_question_ids") or []
    if not isinstance(ordered_ids, list) or not ordered_ids:
        raise HTTPException(status_code=400, detail="ordered_question_ids required")
    assigns = session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id)).all()
    amap = {a.question_id: a for a in assigns}
    order = 1
    for qid in ordered_ids:
        qid_i = int(qid)
        if qid_i not in amap:
            continue
        a = amap[qid_i]
        a.order = order
        order += 1
        session.add(a)
    session.commit()
    return {"ok": True}


@router.delete("/kp-questions/{assignment_id}")
def remove_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    a = session.get(KpQuestionAssignment, assignment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    session.delete(a)
    session.commit()
    return {"ok": True}


@router.post("/questions", response_model=QuestionOut)
def create_question(
    payload: QuestionIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp = session.get(KnowledgePoint, payload.kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    qtype = payload.type.strip()
    if qtype not in {"mcq", "blank"}:
        raise HTTPException(status_code=400, detail="Invalid question type")
    options = payload.options if qtype == "mcq" else []
    question = Question(
        subject=kp.subject,
        grade=kp.grade,
        kp_id=payload.kp_id,
        type=qtype,
        prompt=payload.prompt,
        options_json=json.dumps(options, ensure_ascii=False),
        answer=payload.answer,
        explanation=payload.explanation,
        difficulty=float(payload.difficulty),
        source=payload.source.strip(),
        tags=payload.tags.strip(),
        version=payload.version.strip() or "v1",
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return QuestionOut(
        id=question.id,
        kp_id=question.kp_id,
        type=question.type,
        prompt=question.prompt,
        options=options,
        answer=question.answer,
        explanation=question.explanation,
        difficulty=question.difficulty,
        source=question.source,
        tags=question.tags,
        version=question.version,
    )


@router.post("/questions/import-docx")
def import_questions_docx(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    doc = Document(BytesIO(data))
    lines: list[str] = []
    for p in doc.paragraphs:
        if not p.text:
            continue
        for part in p.text.splitlines():
            line = part.strip()
            if line:
                lines.append(line)

    markers = {"题目", "【题目】", "[题目]", "题目开始", "---", "----", "-----"}
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        normalized_line = re.sub(r"^[\\s\\-\\*\\•\\d\\._、)]+", "", line).strip()
        if normalized_line in markers:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    if not blocks and lines:
        blocks = [lines]

    def split_key_value(text: str) -> tuple[str | None, str]:
        m = re.match(r"^([^:：=]+)[:：=]\s*(.*)$", text)
        if not m:
            return None, text.strip()
        key = re.sub(r"^[\\s\\-\\*\\•\\d\\._、)]+", "", m.group(1)).strip()
        return key, m.group(2).strip()

    def normalize_type(value: str) -> str | None:
        v = value.strip().lower()
        if v in {"选择", "选择题", "单选", "mcq"}:
            return "mcq"
        if v in {"填空", "填空题", "blank"}:
            return "blank"
        return None

    key_map = {
        "知识点编码": "kp_code",
        "知识点": "kp_code",
        "kp": "kp_code",
        "KP": "kp_code",
        "编码": "kp_code",
        "题型": "qtype",
        "类型": "qtype",
        "type": "qtype",
        "TYPE": "qtype",
        "题干": "prompt",
        "题目": "prompt",
        "PROMPT": "prompt",
        "答案": "answer",
        "ANSWER": "answer",
        "解析": "explanation",
        "EXPLANATION": "explanation",
        "难度": "difficulty",
        "DIFFICULTY": "difficulty",
        "选项": "options",
    }

    created = 0
    skipped = 0
    errors: list[str] = []
    seen: set[tuple[int, str]] = set()

    for idx, block in enumerate(blocks, start=1):
        data_map: dict[str, str] = {}
        options: list[str] = []
        in_options = False

        for line in block:
            key, value = split_key_value(line)
            if key is None:
                if in_options:
                    m = re.match(r"^([A-H])[\.\:：=]\s*(.+)$", line)
                    if m:
                        options.append(m.group(2).strip())
                        continue
                continue

            mapped = key_map.get(key.strip())
            if mapped == "options":
                in_options = True
                if value:
                    m = re.match(r"^([A-H])[\.\:：=]\s*(.+)$", value)
                    if m:
                        options.append(m.group(2).strip())
                continue

            in_options = False
            if mapped:
                data_map[mapped] = value

        kp_code = (data_map.get("kp_code") or "").strip()
        qtype_raw = data_map.get("qtype") or ""
        qtype = normalize_type(qtype_raw) if qtype_raw else None
        prompt = (data_map.get("prompt") or "").strip()
        answer = (data_map.get("answer") or "").strip()
        explanation = (data_map.get("explanation") or "").strip()
        difficulty_str = (data_map.get("difficulty") or "").strip()

        if not kp_code or not qtype or not prompt or not answer:
            errors.append(f"第{idx}题缺少必填字段（知识点编码/题型/题干/答案）")
            continue

        kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == kp_code)).first()
        if kp is None:
            errors.append(f"第{idx}题知识点编码不存在: {kp_code}")
            continue

        if qtype == "mcq":
            if len(options) < 2:
                errors.append(f"第{idx}题选项不足（至少2个）")
                continue
            if answer:
                m = re.match(r"^[A-H]", answer, re.I)
                if m:
                    answer = m.group(0).upper()
            if answer not in {"A", "B", "C", "D", "E", "F", "G", "H"}:
                errors.append(f"第{idx}题答案必须是 A/B/C/D...")
                continue
        else:
            options = []

        try:
            difficulty = float(difficulty_str) if difficulty_str else 0.4
        except ValueError:
            difficulty = 0.4
        difficulty = min(1.0, max(0.0, difficulty))

        key = (kp.id, prompt)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)

        exists = session.exec(select(Question).where(Question.kp_id == kp.id, Question.prompt == prompt)).first()
        if exists:
            skipped += 1
            continue

        q = Question(
            subject=kp.subject,
            grade=kp.grade,
            kp_id=kp.id,
            type=qtype,
            prompt=prompt,
            options_json=json.dumps(options, ensure_ascii=False),
            answer=answer,
            explanation=explanation,
            difficulty=difficulty,
        )
        session.add(q)
        created += 1

    session.commit()
    _log_action(_admin, "questions_import_docx", f"created={created} skipped={skipped} errors={len(errors)}")
    return {"ok": True, "created": created, "skipped": skipped, "errors": errors[:50]}


@router.put("/questions/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: int,
    payload: QuestionIn,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    q = session.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    qtype = payload.type.strip()
    if qtype not in {"mcq", "blank"}:
        raise HTTPException(status_code=400, detail="Invalid question type")
    q.kp_id = payload.kp_id
    kp = session.get(KnowledgePoint, payload.kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    q.subject = kp.subject
    q.grade = kp.grade
    q.type = qtype
    q.prompt = payload.prompt
    options = payload.options if qtype == "mcq" else []
    q.options_json = json.dumps(options, ensure_ascii=False)
    q.answer = payload.answer
    q.explanation = payload.explanation
    q.difficulty = float(payload.difficulty)
    q.source = payload.source.strip()
    q.tags = payload.tags.strip()
    q.version = payload.version.strip() or "v1"
    session.add(q)
    session.commit()
    session.refresh(q)
    return QuestionOut(
        id=q.id,
        kp_id=q.kp_id,
        type=q.type,
        prompt=q.prompt,
        options=options,
        answer=q.answer,
        explanation=q.explanation,
        difficulty=q.difficulty,
        source=q.source,
        tags=q.tags,
        version=q.version,
    )


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    q = session.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    session.delete(q)
    session.commit()
    return {"ok": True}


@router.get("/quiz")
def get_quiz_admin(
    kp_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    if quiz is None:
        return {"quiz_id": None, "pass_accuracy": 0.8, "items": []}
    items = session.exec(select(QuizItem).where(QuizItem.quiz_id == quiz.id)).all()
    return {
        "quiz_id": quiz.id,
        "pass_accuracy": quiz.pass_accuracy,
        "items": [
            {
                "id": i.id,
                "type": i.type,
                "prompt": i.prompt,
                "options": json.loads(i.options_json),
                "answer": i.answer,
                "explanation": i.explanation,
                "key_item": i.key_item,
            }
            for i in items
        ],
    }


@router.put("/quiz/{kp_id}/pass_accuracy")
def update_quiz_pass_accuracy(
    kp_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    if quiz is None:
        kp = session.get(KnowledgePoint, kp_id)
        if kp is None:
            raise HTTPException(status_code=404, detail="Knowledge point not found")
        quiz = Quiz(subject=kp.subject, grade=kp.grade, kp_id=kp_id, pass_accuracy=0.8)
    pass_accuracy = float(payload.get("pass_accuracy", quiz.pass_accuracy))
    quiz.pass_accuracy = max(0.0, min(1.0, pass_accuracy))
    session.add(quiz)
    session.commit()
    return {"ok": True, "pass_accuracy": quiz.pass_accuracy}


@router.post("/quiz/item")
def create_quiz_item(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    qtype = str(payload.get("type", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    answer = str(payload.get("answer", "")).strip()
    explanation = str(payload.get("explanation", "")).strip()
    key_item = bool(payload.get("key_item", False))
    options = payload.get("options") or []
    if qtype not in {"mcq", "blank"}:
        raise HTTPException(status_code=400, detail="Invalid quiz item type")
    if not prompt or not answer:
        raise HTTPException(status_code=400, detail="prompt/answer required")
    if qtype == "mcq" and (not isinstance(options, list) or len(options) < 2):
        raise HTTPException(status_code=400, detail="mcq options required")

    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    if quiz is None:
        kp = session.get(KnowledgePoint, kp_id)
        if kp is None:
            raise HTTPException(status_code=404, detail="Knowledge point not found")
        quiz = Quiz(subject=kp.subject, grade=kp.grade, kp_id=kp_id, pass_accuracy=0.8)
        session.add(quiz)
        session.commit()
        session.refresh(quiz)

    item = QuizItem(
        quiz_id=quiz.id,
        type=qtype,
        prompt=prompt,
        options_json=json.dumps(options if qtype == "mcq" else [], ensure_ascii=False),
        answer=answer,
        explanation=explanation,
        key_item=key_item,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"ok": True, "item_id": item.id}


@router.post("/quiz/item/from-question")
def create_quiz_item_from_question(
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    kp_id = int(payload.get("kp_id"))
    question_id = int(payload.get("question_id"))
    q = session.get(Question, question_id)
    if q is None or q.kp_id != kp_id:
        raise HTTPException(status_code=400, detail="Question not found for this knowledge point")

    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    if quiz is None:
        kp = session.get(KnowledgePoint, kp_id)
        if kp is None:
            raise HTTPException(status_code=404, detail="Knowledge point not found")
        quiz = Quiz(subject=kp.subject, grade=kp.grade, kp_id=kp_id, pass_accuracy=0.8)
        session.add(quiz)
        session.commit()
        session.refresh(quiz)

    exists = session.exec(
        select(QuizItem).where(QuizItem.quiz_id == quiz.id, QuizItem.prompt == q.prompt)
    ).first()
    if exists:
        return {"ok": True, "item_id": exists.id, "skipped": True}

    item = QuizItem(
        quiz_id=quiz.id,
        type=q.type,
        prompt=q.prompt,
        options_json=q.options_json,
        answer=q.answer,
        explanation=q.explanation,
        key_item=False,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return {"ok": True, "item_id": item.id}


@router.put("/quiz/item/{item_id}")
def update_quiz_item(
    item_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    item = session.get(QuizItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Quiz item not found")
    qtype = str(payload.get("type", item.type)).strip()
    prompt = str(payload.get("prompt", item.prompt)).strip()
    answer = str(payload.get("answer", item.answer)).strip()
    explanation = str(payload.get("explanation", item.explanation)).strip()
    key_item = bool(payload.get("key_item", item.key_item))
    options = payload.get("options") or []
    if qtype not in {"mcq", "blank"}:
        raise HTTPException(status_code=400, detail="Invalid quiz item type")
    if not prompt or not answer:
        raise HTTPException(status_code=400, detail="prompt/answer required")
    if qtype == "mcq" and (not isinstance(options, list) or len(options) < 2):
        raise HTTPException(status_code=400, detail="mcq options required")

    item.type = qtype
    item.prompt = prompt
    item.answer = answer
    item.explanation = explanation
    item.key_item = key_item
    item.options_json = json.dumps(options if qtype == "mcq" else [], ensure_ascii=False)
    session.add(item)
    session.commit()
    return {"ok": True}


@router.delete("/quiz/item/{item_id}")
def delete_quiz_item(
    item_id: int,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    item = session.get(QuizItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Quiz item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}


@router.post("/seed")
def seed_derivative_demo(
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    subject = "\u6570\u636e\u7ed3\u6784"
    grade = "\u901a\u7528"
    kps = [
        ("DS-GEN-001", "\u7ebf\u6027\u8868\u57fa\u7840", "\u7ebf\u6027\u8868\u4e0e\u987a\u5e8f\u5b58\u50a8\u7684\u57fa\u7840\u6982\u5ff5"),
        ("DS-GEN-002", "\u6808\u4e0e\u961f\u5217", "\u987a\u5e8f\u6808\u4e0e\u961f\u5217\u7684\u57fa\u7840\u64cd\u4f5c"),
        ("DS-GEN-003", "\u4e32", "\u5b57\u7b26\u4e32\u7684\u5b9a\u4e49\u4e0e\u57fa\u672c\u64cd\u4f5c"),
    ]
    code_to_id = {}
    for code, title, desc in kps:
        kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
        if kp is None:
            kp = KnowledgePoint(subject=subject, grade=grade, code=code, title=title, description=desc)
            session.add(kp)
            session.commit()
            session.refresh(kp)
        code_to_id[code] = kp.id

    def add_resource(code: str, title: str, url: str, rtype: str):
        kp_id = code_to_id[code]
        exists = session.exec(select(LearningResource).where(LearningResource.kp_id == kp_id, LearningResource.title == title)).first()
        if exists is None:
            session.add(
                LearningResource(
                    subject=subject,
                    grade=grade,
                    kp_id=kp_id,
                    title=title,
                    url=url,
                    type=ResourceType(rtype),
                )
            )
            session.commit()

    def add_question(code: str, qtype: str, prompt: str, options: list[str], answer: str, explanation: str, difficulty: float):
        kp_id = code_to_id[code]
        exists = session.exec(select(Question).where(Question.kp_id == kp_id, Question.prompt == prompt)).first()
        if exists is None:
            session.add(
                Question(
                    subject=subject,
                    grade=grade,
                    kp_id=kp_id,
                    type=qtype,
                    prompt=prompt,
                    options_json=json.dumps(options, ensure_ascii=False),
                    answer=answer,
                    explanation=explanation,
                    difficulty=float(difficulty),
                )
            )
            session.commit()

    add_resource(
        "DS-GEN-001",
        "\u793a\u4f8bMP4\u89c6\u9891",
        "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "video",
    )

    add_question(
        "DS-GEN-001",
        "mcq",
        "\u5173\u4e8e\u7ebf\u6027\u8868\u7684\u8bf4\u6cd5\u6b63\u786e\u7684\u662f\uff1f",
        ["\u53ea\u80fd\u7528\u6570\u7ec4\u5b58\u50a8", "\u53ea\u80fd\u7528\u94fe\u8868\u5b58\u50a8", "\u53ef\u4ee5\u7528\u6570\u7ec4\u6216\u94fe\u8868\u5b58\u50a8", "\u4e0d\u80fd\u904d\u5386"],
        "A",
        "\u7ebf\u6027\u8868\u53ef\u4ee5\u987a\u5e8f\u6216\u94fe\u5f0f\u5b58\u50a8\u3002",
        0.3,
    )
    add_question(
        "DS-GEN-002",
        "blank",
        "\u6808\u7684\u7279\u70b9\u662f____\uff08\u5148\u5165\u540e\u51fa/\u540e\u5165\u5148\u51fa\uff09",
        [],
        "\u5148\u5165\u540e\u51fa",
        "\u6808\u662fLIFO\u7ed3\u6784\u3002",
        0.3,
    )

    _log_action(_admin, "seed_demo", f"subject={subject} kps={len(kps)}")
    return {"ok": True, "kps": len(kps)}


@router.post("/seed/full")
def seed_full_system(
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    """
    Seed a CS-only dataset (4 subjects, no grade) with full question banks.
    Idempotent: safe to run multiple times.
    """

    subjects: list[tuple[str, str, list[tuple[str, str]]]] = [
        (
            "\u6570\u636e\u7ed3\u6784",
            "DS",
            [
                ("DS-GEN-001", "\u7ebf\u6027\u8868\u57fa\u7840"),
                ("DS-GEN-002", "\u6808\u4e0e\u961f\u5217"),
                ("DS-GEN-003", "\u4e32"),
                ("DS-GEN-004", "\u6570\u7ec4\u4e0e\u77e9\u9635"),
                ("DS-GEN-005", "\u6811\u4e0e\u4e8c\u53c9\u6811"),
                ("DS-GEN-006", "\u56fe\u57fa\u7840"),
                ("DS-GEN-007", "\u67e5\u627e"),
                ("DS-GEN-008", "\u6392\u5e8f"),
                ("DS-GEN-009", "\u54c8\u5e0c\u8868"),
                ("DS-GEN-010", "\u5806\u4e0e\u4f18\u5148\u961f\u5217"),
            ],
        ),
        (
            "\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406",
            "CO",
            [
                ("CO-GEN-001", "\u6570\u5236\u4e0e\u7f16\u7801"),
                ("CO-GEN-002", "\u903b\u8f91\u7535\u8def\u57fa\u7840"),
                ("CO-GEN-003", "\u6307\u4ee4\u7cfb\u7edf"),
                ("CO-GEN-004", "CPU\u7ed3\u6784\u4e0e\u63a7\u5236"),
                ("CO-GEN-005", "\u6d41\u6c34\u7ebf"),
                ("CO-GEN-006", "\u5b58\u50a8\u5c42\u6b21"),
                ("CO-GEN-007", "\u8f93\u5165\u8f93\u51fa"),
                ("CO-GEN-008", "\u603b\u7ebf\u4e0e\u63a5\u53e3"),
                ("CO-GEN-009", "\u4e2d\u65ad\u4e0e\u5f02\u5e38"),
                ("CO-GEN-010", "\u6027\u80fd\u4e0e\u5e76\u884c"),
            ],
        ),
        (
            "\u64cd\u4f5c\u7cfb\u7edf",
            "OS",
            [
                ("OS-GEN-001", "\u64cd\u4f5c\u7cfb\u7edf\u6982\u8ff0"),
                ("OS-GEN-002", "\u8fdb\u7a0b\u4e0e\u7ebf\u7a0b"),
                ("OS-GEN-003", "CPU\u8c03\u5ea6"),
                ("OS-GEN-004", "\u540c\u6b65\u4e0e\u4e92\u65a5"),
                ("OS-GEN-005", "\u6b7b\u9501"),
                ("OS-GEN-006", "\u5185\u5b58\u7ba1\u7406"),
                ("OS-GEN-007", "\u865a\u62df\u5185\u5b58"),
                ("OS-GEN-008", "\u6587\u4ef6\u7cfb\u7edf"),
                ("OS-GEN-009", "I/O\u4e0e\u8bbe\u5907"),
                ("OS-GEN-010", "\u5b89\u5168\u4e0e\u4fdd\u62a4"),
            ],
        ),
        (
            "\u8ba1\u7b97\u673a\u7f51\u7edc",
            "CN",
            [
                ("CN-GEN-001", "\u7f51\u7edc\u4f53\u7cfb\u7ed3\u6784"),
                ("CN-GEN-002", "\u7269\u7406\u5c42"),
                ("CN-GEN-003", "\u6570\u636e\u94fe\u8def\u5c42"),
                ("CN-GEN-004", "\u4ecb\u8d28\u8bbf\u95ee\u63a7\u5236"),
                ("CN-GEN-005", "\u7f51\u7edc\u5c42"),
                ("CN-GEN-006", "\u8def\u7531\u4e0e\u8f6c\u53d1"),
                ("CN-GEN-007", "\u4f20\u8f93\u5c42"),
                ("CN-GEN-008", "\u5e94\u7528\u5c42"),
                ("CN-GEN-009", "\u7f51\u7edc\u5b89\u5168"),
                ("CN-GEN-010", "\u65e0\u7ebf\u4e0e\u79fb\u52a8\u7f51\u7edc"),
            ],
        ),
    ]

    grade_name = "\u901a\u7528"

    for username, password, role in [
        ("admin", "admin123", UserRole.admin),
        ("teacher1", "teacher123", UserRole.teacher),
        ("student1", "student123", UserRole.student),
        ("student2", "student123", UserRole.student),
        ("student3", "student123", UserRole.student),
    ]:
        exists = session.exec(select(User).where(User.username == username)).first()
        if exists is None:
            session.add(User(username=username, password_hash=hash_password(password), role=role))
    session.commit()

    def ensure_eval_config(subj: str) -> None:
        cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subj, EvalConfig.grade == grade_name)).first()
        if cfg is None:
            session.add(EvalConfig(subject=subj, grade=grade_name))
            session.commit()

    def ensure_kp(subj: str, code: str, title: str) -> KnowledgePoint:
        kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
        if kp is None:
            kp = KnowledgePoint(
                subject=subj,
                grade=grade_name,
                code=code,
                title=title,
                description=f"{title}\uff08\u793a\u4f8b\uff09",
            )
            session.add(kp)
            session.commit()
            session.refresh(kp)
        return kp

    def ensure_edge(subj: str, prereq_id: int, next_id: int) -> None:
        e = session.exec(
            select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == prereq_id, KnowledgeEdge.next_id == next_id)
        ).first()
        if e is None:
            session.add(KnowledgeEdge(subject=subj, grade=grade_name, prereq_id=prereq_id, next_id=next_id))
            session.commit()

    def ensure_question(
        subj: str,
        kp_id: int,
        qtype: str,
        prompt: str,
        options: list[str],
        answer: str,
        explanation: str,
        difficulty: float,
    ) -> None:
        q = session.exec(select(Question).where(Question.kp_id == kp_id, Question.prompt == prompt)).first()
        if q is None:
            session.add(
                Question(
                    subject=subj,
                    grade=grade_name,
                    kp_id=kp_id,
                    type=qtype,
                    prompt=prompt,
                    options_json=json.dumps(options, ensure_ascii=False),
                    answer=answer,
                    explanation=explanation,
                    difficulty=float(difficulty),
                )
            )
            session.commit()

    def ensure_quiz(kp: KnowledgePoint, pass_accuracy: float = 0.8) -> Quiz:
        quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp.id)).first()
        if quiz is None:
            quiz = Quiz(subject=kp.subject, grade=kp.grade, kp_id=kp.id, pass_accuracy=pass_accuracy)
            session.add(quiz)
            session.commit()
            session.refresh(quiz)
        return quiz

    def ensure_quiz_item(quiz: Quiz, it: dict) -> None:
        exists = session.exec(select(QuizItem).where(QuizItem.quiz_id == quiz.id, QuizItem.prompt == it["prompt"])).first()
        if exists is None:
            session.add(
                QuizItem(
                    quiz_id=quiz.id,
                    type=it["type"],
                    prompt=it["prompt"],
                    options_json=json.dumps(it.get("options", []), ensure_ascii=False),
                    answer=it["answer"],
                    explanation=it.get("explanation", ""),
                    key_item=bool(it.get("key_item", False)),
                )
            )
            session.commit()

    def ensure_resource(kp: KnowledgePoint) -> None:
        title = f"{kp.title} \u793a\u4f8b\u89c6\u9891"
        exists = session.exec(select(LearningResource).where(LearningResource.kp_id == kp.id, LearningResource.title == title)).first()
        if exists is None:
            session.add(
                LearningResource(
                    subject=kp.subject,
                    grade=kp.grade,
                    kp_id=kp.id,
                    title=title,
                    url="https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
                    type=ResourceType.video,
                )
            )
            session.commit()

    created_kp = 0
    created_questions = 0

    difficulties = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]

    for subj_name, _subj_code, kp_list in subjects:
        ensure_eval_config(subj_name)
        kp_objs: list[KnowledgePoint] = []
        for code, title in kp_list:
            kp = ensure_kp(subj_name, code, title)
            kp_objs.append(kp)
            created_kp += 1
            ensure_resource(kp)

        for idx in range(len(kp_objs) - 1):
            ensure_edge(subj_name, kp_objs[idx].id, kp_objs[idx + 1].id)

        for kp in kp_objs:
            base = kp.code
            for i in range(20):
                diff = difficulties[i % len(difficulties)]
                options = [
                    f"{kp.title} \u76f8\u5173\u6982\u5ff5 {i + 1}",
                    f"{kp.title} \u7ed3\u8bba {i + 1}",
                    f"{kp.title} \u65b9\u6cd5 {i + 2}",
                    f"{kp.title} \u5e94\u7528 {i + 3}",
                ]
                answer = "A" if i % 2 == 0 else "B"
                prompt = f"{base}\uff1a\u5173\u4e8e{kp.title}\u7684\u9009\u62e9\u9898{i + 1}"
                ensure_question(subj_name, kp.id, "mcq", prompt, options, answer, "\u793a\u4f8b\u89e3\u6790", diff)
                created_questions += 1

            for i in range(20):
                diff = difficulties[i % len(difficulties)]
                prompt = f"{base}\uff1a{kp.title}\u586b\u7a7a____\uff08{i + 1}\uff09"
                answer = f"\u7b54\u6848{i + 1}"
                ensure_question(subj_name, kp.id, "blank", prompt, [], answer, "\u793a\u4f8b\u89e3\u6790", diff)
                created_questions += 1

            quiz = ensure_quiz(kp, pass_accuracy=0.8)
            ensure_quiz_item(
                quiz,
                {
                    "type": "mcq",
                    "prompt": f"{base}\uff1a\u5c0f\u6d4b\u9898\u76ee1",
                    "options": ["A. \u9009\u98791", "B. \u9009\u98792", "C. \u9009\u98793", "D. \u9009\u98794"],
                    "answer": "B",
                    "explanation": "\u793a\u4f8b\u89e3\u6790",
                    "key_item": True,
                },
            )
            ensure_quiz_item(
                quiz,
                {
                    "type": "mcq",
                    "prompt": f"{base}\uff1a\u5c0f\u6d4b\u9898\u76ee2",
                    "options": ["A. \u9009\u98791", "B. \u9009\u98792", "C. \u9009\u98793", "D. \u9009\u98794"],
                    "answer": "A",
                    "explanation": "\u793a\u4f8b\u89e3\u6790",
                },
            )
            ensure_quiz_item(
                quiz,
                {
                    "type": "blank",
                    "prompt": f"{base}\uff1a\u5c0f\u6d4b\u586b\u7a7a1____",
                    "options": [],
                    "answer": "\u793a\u4f8b\u7b54\u6848",
                    "explanation": "\u793a\u4f8b\u89e3\u6790",
                },
            )
            ensure_quiz_item(
                quiz,
                {
                    "type": "blank",
                    "prompt": f"{base}\uff1a\u5c0f\u6d4b\u586b\u7a7a2____",
                    "options": [],
                    "answer": "\u793a\u4f8b\u7b54\u6848",
                    "explanation": "\u793a\u4f8b\u89e3\u6790",
                },
            )

    _log_action(_admin, "seed_full", f"created_kp={created_kp} created_questions={created_questions}")
    return {"ok": True, "created_kp": created_kp, "created_questions": created_questions}


@router.get("/config")
def get_config(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == grade)).first()
    if cfg is None:
        cfg = EvalConfig(subject=subject, grade=grade)
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    return {
        "weights": json.loads(cfg.weights_json),
        "thresholds": json.loads(cfg.thresholds_json),
        "window": json.loads(cfg.window_json),
    }


@router.put("/config")
def update_config(
    subject: str,
    grade: str,
    payload: dict,
    session: Session = Depends(get_session),
    _admin=Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    cfg = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == grade)).first()
    if cfg is None:
        cfg = EvalConfig(subject=subject, grade=grade)
    cfg.weights_json = json.dumps(payload.get("weights", {}), ensure_ascii=False)
    cfg.thresholds_json = json.dumps(payload.get("thresholds", {}), ensure_ascii=False)
    cfg.window_json = json.dumps(payload.get("window", {}), ensure_ascii=False)
    session.add(cfg)
    session.commit()
    return {"ok": True}