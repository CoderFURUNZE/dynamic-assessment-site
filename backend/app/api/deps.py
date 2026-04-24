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
    CourseCompletionRecord,
    CourseTeacherActivation,
    CourseLifecycleStatus,
    Enrollment,
    EnrollmentStatus,
    KnowledgePoint,
    TeacherCourseStatus,
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
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

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
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin cannot access course-content APIs",
                )
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
    return bool(course.active) and lifecycle == CourseLifecycleStatus.active.value


def assert_student_subject_access(session: Session, user_id: int, subject: str) -> None:
    normalized_subject = str(subject or "").strip()
    courses = [
        course
        for course in session.exec(select(Course).order_by(Course.created_at.desc())).all()
        if str(course.title or "").strip() == normalized_subject
    ]
    if not courses:
        raise HTTPException(status_code=403, detail="当前账号尚未加入这门课程，暂时无法进入课程学习")

    student = session.get(User, user_id)
    has_closed_course = False
    has_completed_course = False
    for course in courses:
        if course.id is None:
            continue
        completed = session.exec(
            select(CourseCompletionRecord.id).where(
                CourseCompletionRecord.student_id == user_id,
                CourseCompletionRecord.course_id == int(course.id),
            )
        ).first()
        if completed is not None:
            has_completed_course = True
            continue

        enrollment = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == user_id,
                Enrollment.course_id == int(course.id),
                Enrollment.status == EnrollmentStatus.active,
            )
        ).first()
        if enrollment is not None and is_course_open_for_students(session, course):
            return

        if student is not None and str(student.class_name or "").strip() and str(course.target_class or "").strip() and is_course_open_for_students(session, course):
            if str(student.class_name).strip() == str(course.target_class).strip():
                return

        approved = session.exec(
            select(CourseApplication.id).where(
                CourseApplication.student_id == user_id,
                CourseApplication.course_id == int(course.id),
                CourseApplication.status == ApplicationStatus.approved,
            )
        ).first()
        if approved is not None and is_course_open_for_students(session, course):
            return

        if not is_course_open_for_students(session, course):
            has_closed_course = True

    if has_completed_course:
        raise HTTPException(status_code=403, detail="课程已完成，当前仅可查看学习报告，不能继续进入课程学习")
    if has_closed_course:
        raise HTTPException(status_code=403, detail="课程尚未开放学习，暂时无法进入")
    raise HTTPException(status_code=403, detail="当前账号尚未加入这门课程，暂时无法进入课程学习")


def assert_student_kp_access(session: Session, user_id: int, kp_id: int) -> KnowledgePoint:
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="知识点不存在")
    assert_student_subject_access(session, user_id, kp.subject)
    return kp


def get_teacher_activated_course_ids(session: Session, teacher_id: int) -> set[int]:
    rows = session.exec(
        select(CourseTeacherActivation.course_id).where(
            CourseTeacherActivation.teacher_id == teacher_id,
            CourseTeacherActivation.teaching_status != TeacherCourseStatus.not_started,
        )
    ).all()
    return {int(row) for row in rows if row is not None}


def get_teacher_course_activation_map(session: Session, teacher_id: int) -> dict[int, CourseTeacherActivation]:
    rows = session.exec(
        select(CourseTeacherActivation).where(
            CourseTeacherActivation.teacher_id == teacher_id,
        )
    ).all()
    return {
        int(row.course_id): row
        for row in rows
        if row.course_id is not None
    }


def course_has_teaching_teacher(session: Session, course_id: int) -> bool:
    row = session.exec(
        select(CourseTeacherActivation.id).where(
            CourseTeacherActivation.course_id == course_id,
            CourseTeacherActivation.teaching_status == TeacherCourseStatus.teaching,
        )
    ).first()
    return row is not None


def is_course_open_for_students(session: Session, course: Course | None) -> bool:
    if not _is_course_learning_available(course):
        return False
    if course is None or course.id is None:
        return False
    return course_has_teaching_teacher(session, int(course.id))


def teacher_has_course_access(session: Session, teacher_id: int, course: Course | None) -> bool:
    if course is None or course.id is None:
        return False
    return int(course.id) in get_teacher_activated_course_ids(session, int(teacher_id))
