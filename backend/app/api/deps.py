from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.models import User, UserRole
from app.db.session import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not bool(user.active):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return user


def require_role(*roles: UserRole):
    def _inner(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        # 管理员端职责收口：管理员不可直接访问课程内容管理接口
        if user.role == UserRole.admin:
            path = request.url.path
            admin_content_prefixes = (
                "/api/admin/courses",
                "/api/admin/kps",
                "/api/admin/edges",
                "/api/admin/questions",
                "/api/admin/kp-resources",
                "/api/admin/kp-tasks",
                "/api/admin/seed",
                "/api/admin/practice/report",
                "/api/admin/audit",
            )
            if path.startswith(admin_content_prefixes):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin cannot access course-content APIs")
        return user

    return _inner
