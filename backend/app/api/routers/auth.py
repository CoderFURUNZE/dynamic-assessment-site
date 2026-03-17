import re

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User, UserRole
from app.db.session import get_session
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterStudentRequest,
    RegisterTeacherRequest,
    Token,
    WechatBindRequest,
    WechatLoginRequest,
)
from app.services.learner_profile import log_behavior_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    value = re.sub(r"\D", "", phone)
    if not value:
        return None
    if len(value) != 11:
        raise HTTPException(status_code=400, detail="手机号格式不正确（需 11 位数字）")
    return value


def _validate_password(password: str):
    if len(password or "") < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")


@router.post("/register")
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    _validate_password(payload.password)
    exists = session.exec(select(User).where(User.username == payload.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=UserRole.student)
    session.add(user)
    session.commit()
    return {"ok": True, "user_id": user.id}


@router.post("/register/student")
def register_student(payload: RegisterStudentRequest, session: Session = Depends(get_session)):
    _validate_password(payload.password)
    exists = session.exec(select(User).where(User.username == payload.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    phone = _normalize_phone(payload.phone)
    if phone:
        exists_phone = session.exec(select(User).where(User.phone == phone)).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已被使用")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.student,
        phone=phone,
    )
    session.add(user)
    session.commit()
    return {"ok": True, "user_id": user.id}


@router.post("/register/teacher")
def register_teacher(payload: RegisterTeacherRequest, session: Session = Depends(get_session)):
    _validate_password(payload.password)
    exists = session.exec(select(User).where(User.username == payload.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    phone = _normalize_phone(payload.phone)
    if phone:
        exists_phone = session.exec(select(User).where(User.phone == phone)).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已被使用")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.teacher,
        phone=phone,
    )
    session.add(user)
    session.commit()
    return {"ok": True, "user_id": user.id}


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    if not bool(user.active):
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token(subject=user.username, role=user.role.value)
    log_behavior_event(session, user_id=user.id, event_type="login", commit=True)
    return Token(access_token=token, role=user.role.value)


@router.post("/login/student", response_model=Token)
def login_student(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    if user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Not a student account")
    if not bool(user.active):
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token(subject=user.username, role=user.role.value)
    log_behavior_event(session, user_id=user.id, event_type="login", commit=True)
    return Token(access_token=token, role=user.role.value)


@router.post("/login/admin", response_model=Token)
def login_admin(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    if user.role not in {UserRole.admin, UserRole.teacher}:
        raise HTTPException(status_code=403, detail="Not an admin/teacher account")
    if not bool(user.active):
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token(subject=user.username, role=user.role.value)
    log_behavior_event(session, user_id=user.id, event_type="login", commit=True)
    return Token(access_token=token, role=user.role.value)


@router.post("/wechat/login")
def wechat_login(payload: WechatLoginRequest, session: Session = Depends(get_session)):
    openid = payload.openid.strip()
    if not openid:
        raise HTTPException(status_code=400, detail="openid required")
    phone = _normalize_phone(payload.phone)
    user = session.exec(select(User).where(User.wechat_openid == openid)).first()
    if user and not user.phone and not phone:
        return {"ok": True, "need_bind_phone": True}
    if user and not user.phone and phone:
        exists_phone = session.exec(select(User).where(User.phone == phone)).first()
        if exists_phone and exists_phone.id != user.id:
            raise HTTPException(status_code=400, detail="手机号已被使用")
        user.phone = phone
        session.add(user)
        session.commit()
    if user is None:
        if not phone:
            return {"ok": True, "need_bind_phone": True}
        exists_phone = session.exec(select(User).where(User.phone == phone)).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已被使用")
        user = User(
            username=f"wx_{openid[:10]}",
            password_hash=hash_password(openid),
            role=UserRole.student,
            phone=phone,
            wechat_openid=openid,
        )
        session.add(user)
        session.commit()
    token = create_access_token(subject=user.username, role=user.role.value)
    log_behavior_event(session, user_id=user.id, event_type="login", commit=True)
    return {"ok": True, "need_bind_phone": False, "access_token": token, "role": user.role.value}


@router.post("/wechat/bind")
def wechat_bind(payload: WechatBindRequest, session: Session = Depends(get_session)):
    openid = payload.openid.strip()
    if not openid:
        raise HTTPException(status_code=400, detail="openid required")
    phone = _normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")
    exists_phone = session.exec(select(User).where(User.phone == phone)).first()
    if exists_phone and exists_phone.wechat_openid != openid:
        raise HTTPException(status_code=400, detail="手机号已被使用")
    user = session.exec(select(User).where(User.wechat_openid == openid)).first()
    if user is None:
        user = User(
            username=f"wx_{openid[:10]}",
            password_hash=hash_password(openid),
            role=UserRole.student,
            phone=phone,
            wechat_openid=openid,
        )
    else:
        user.phone = phone
    session.add(user)
    session.commit()
    token = create_access_token(subject=user.username, role=user.role.value)
    log_behavior_event(session, user_id=user.id, event_type="login", commit=True)
    return {"ok": True, "access_token": token, "role": user.role.value}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value,
        "active": bool(user.active),
        "full_name": user.full_name,
        "student_no": user.student_no,
        "class_name": user.class_name,
        "phone": user.phone,
    }
