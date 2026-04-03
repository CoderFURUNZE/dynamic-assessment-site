from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.models import (
    ApplicationStatus,
    Course,
    CourseApplication,
    CourseLifecycleStatus,
    Enrollment,
    EnrollmentStatus,
    KnowledgePoint,
    User,
    UserRole,
)
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
        # Limit a small set of teacher-owned content APIs for admin accounts.
        if user.role == UserRole.admin:
            path = request.url.path
            admin_content_prefixes = (
                "/api/admin/edges",
                "/api/admin/kp-resources",
                "/api/admin/kp-tasks",
                "/api/admin/practice/report",
                "/api/admin/questions",
                "/api/admin/seed",
            )
            if path.startswith(admin_content_prefixes):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin cannot access course-content APIs")
        return user

    return _inner


def _course_lifecycle_value(course: Course | None) -> str:
    if course is None:
        return CourseLifecycleStatus.draft.value
    value = getattr(course, "lifecycle_status", CourseLifecycleStatus.draft)
    return value.value if hasattr(value, "value") else str(value or CourseLifecycleStatus.draft.value)


def _is_course_learning_available(course: Course | None) -> bool:
    if course is None:
        return False
    lifecycle = _course_lifecycle_value(course)
    if not bool(course.active) or lifecycle != CourseLifecycleStatus.active.value:
        return False
    return True


def assert_student_subject_access(session: Session, user_id: int, subject: str) -> None:
    normalized_subject = str(subject or "").strip()
    courses = [
        course
        for course in session.exec(select(Course).order_by(Course.created_at.desc())).all()
        if str(course.title or "").strip() == normalized_subject
    ]
    if not courses:
        raise HTTPException(status_code=403, detail="浣犲皻鏈€氳繃璇ヨ绋嬪鏍革紝鏆傛椂鏃犳硶杩涘叆璇剧▼")

    student = session.get(User, user_id)
    has_closed_course = False
    for course in courses:
        if course.id is None:
            continue

        enrollment = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == user_id,
                Enrollment.course_id == int(course.id),
                Enrollment.status == EnrollmentStatus.active,
            )
        ).first()
        if enrollment is not None:
            return

        if student is not None and str(student.class_name or "").strip() and str(course.target_class or "").strip():
            if str(student.class_name).strip() == str(course.target_class).strip():
                return

        approved = session.exec(
            select(CourseApplication.id).where(
                CourseApplication.student_id == user_id,
                CourseApplication.course_id == int(course.id),
                CourseApplication.status == ApplicationStatus.approved,
            )
        ).first()
        if approved is not None:
            return

        if not _is_course_learning_available(course):
            has_closed_course = True

    if has_closed_course:
        raise HTTPException(status_code=403, detail="璇剧▼灏氭湭寮€璇撅紝鏆傛棤娉曞涔?")
    raise HTTPException(status_code=403, detail="浣犲皻鏈€氳繃璇ヨ绋嬪鏍革紝鏆傛椂鏃犳硶杩涘叆璇剧▼")


def assert_student_kp_access(session: Session, user_id: int, kp_id: int) -> KnowledgePoint:
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="鐭ヨ瘑鐐逛笉瀛樺湪")
    assert_student_subject_access(session, user_id, kp.subject)
    return kp
