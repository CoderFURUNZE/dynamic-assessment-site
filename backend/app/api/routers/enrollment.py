from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_role
from app.db.models import (
    ApplicationStatus,
    Course,
    CourseLifecycleStatus,
    CourseApplication,
    CourseCompletionRecord,
    CourseEnrollStatus,
    CourseNotification,
    CoursePrerequisite,
    Enrollment,
    EnrollmentStatus,
    NotificationStatus,
    User,
    UserRole,
)
from app.db.session import get_session
from app.services.notification import push_course_notification

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


def _course_active_for_student_join(course: Course | None) -> bool:
    """与图谱学习校验一致：仅开课中且在开课周期内的课程允许加入。"""
    if course is None or not bool(course.active):
        return False
    lifecycle_raw = course.lifecycle_status
    lifecycle = lifecycle_raw.value if isinstance(lifecycle_raw, CourseLifecycleStatus) else str(lifecycle_raw or "")
    if lifecycle != CourseLifecycleStatus.active.value:
        return False
    now = datetime.utcnow()
    if course.start_at and now < course.start_at:
        return False
    if course.end_at and now > course.end_at:
        return False
    if course.enroll_status == CourseEnrollStatus.closed:
        return False
    return True


def _course_open_status(course: Course, enrolled_count: int) -> str:
    now = datetime.utcnow()
    if course.apply_deadline is not None and now > course.apply_deadline:
        return CourseEnrollStatus.expired.value
    if course.enroll_status == CourseEnrollStatus.closed:
        return CourseEnrollStatus.closed.value
    if enrolled_count >= int(course.max_students or 0):
        return CourseEnrollStatus.full.value
    return CourseEnrollStatus.open.value


def _assert_student_course_access(session: Session, student_id: int, course_id: int) -> None:
    enrollment = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.active,
        )
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")
    if enrollment.application_id is None:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")
    application = session.get(CourseApplication, enrollment.application_id)
    if application is None or application.status != ApplicationStatus.approved:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")


@router.get("/courses/enrollable")
def list_enrollable_courses(
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    courses = session.exec(select(Course).where(Course.active == True).order_by(Course.created_at.desc())).all()  # noqa: E712
    teacher_ids = [int(item.teacher_id) for item in courses if item.teacher_id is not None]
    teacher_map = {}
    if teacher_ids:
        teachers = session.exec(select(User).where(User.id.in_(teacher_ids))).all()
        teacher_map = {int(t.id): (t.full_name or t.username) for t in teachers if t.id is not None}
    my_apps = session.exec(select(CourseApplication).where(CourseApplication.student_id == user.id)).all()
    app_map = {int(item.course_id): item for item in my_apps}
    enrollment_rows = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == user.id,
            Enrollment.status == EnrollmentStatus.active,
        )
    ).all()
    enrollment_map = {int(item.course_id): item for item in enrollment_rows if item.course_id is not None}
    data = []
    for course in courses:
        if course.id is None:
            continue
        enrolled_count = len(
            session.exec(
                select(Enrollment.id).where(
                    Enrollment.course_id == int(course.id),
                    Enrollment.status == EnrollmentStatus.active,
                )
            ).all()
        )
        status = _course_open_status(course, enrolled_count)
        app = app_map.get(int(course.id))
        enrollment = enrollment_map.get(int(course.id))
        class_bound = bool(str(course.target_class or "").strip()) and str(course.target_class or "").strip() == str(user.class_name or "").strip()
        lifecycle = course.lifecycle_status.value if isinstance(course.lifecycle_status, CourseLifecycleStatus) else str(course.lifecycle_status or "draft")
        if enrollment is not None and enrollment.application_id is None:
            app_status = "linked"
        else:
            app_status = app.status.value if app else None
        data.append(
            {
                "id": int(course.id),
                "code": course.code,
                "title": course.title,
                "description": course.description,
                "teacher_id": course.teacher_id,
                "teacher_name": teacher_map.get(int(course.teacher_id or 0), ""),
                "max_students": int(course.max_students or 0),
                "enrolled_count": enrolled_count,
                "apply_deadline": course.apply_deadline.isoformat() if course.apply_deadline else None,
                "enroll_status": status,
                "application_status": app_status,
                "enrollment_mode": "class_auto" if class_bound else "manual_apply",
                "target_class": course.target_class,
                "lifecycle_status": lifecycle,
                "start_at": course.start_at.isoformat() if course.start_at else None,
                "end_at": course.end_at.isoformat() if course.end_at else None,
            }
        )
    return {"items": data}


@router.post("/courses/join-by-code")
def join_course_by_code(
    payload: dict,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    """校内场景：学生凭管理员公布的课程代码加入，无需教师逐人审核（与行政导入/班级自动关联并列）。"""
    raw = str(payload.get("join_code") or payload.get("code") or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="请输入课程代码")
    course = session.exec(select(Course).where(Course.code == raw)).first()
    if course is None or course.id is None:
        raise HTTPException(status_code=404, detail="课程代码不存在")
    if not bool(course.active):
        raise HTTPException(status_code=400, detail="该课程未启用")
    if not _course_active_for_student_join(course):
        raise HTTPException(status_code=400, detail="课程当前不在加入周期内（未开课、已结课或暂不开放）")
    cid = int(course.id)
    enrolled_count = len(
        session.exec(
            select(Enrollment.id).where(
                Enrollment.course_id == cid,
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
    )
    open_status = _course_open_status(course, enrolled_count)
    if open_status == CourseEnrollStatus.full.value:
        raise HTTPException(status_code=400, detail="课程名额已满")
    existing = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == int(user.id),
            Enrollment.course_id == cid,
        )
    ).first()
    if existing is not None:
        if existing.status == EnrollmentStatus.active:
            return {
                "ok": True,
                "course_id": cid,
                "title": course.title,
                "already_enrolled": True,
            }
        existing.status = EnrollmentStatus.active
        existing.application_id = None
        session.add(existing)
        push_course_notification(
            session,
            user_id=int(user.id),
            title=f"已重新加入《{course.title}》",
            content="选课状态已恢复，可直接学习。",
        )
        session.commit()
        return {"ok": True, "course_id": cid, "title": course.title, "reactivated": True}

    session.add(
        Enrollment(
            student_id=int(user.id),
            course_id=cid,
            application_id=None,
            status=EnrollmentStatus.active,
        )
    )
    push_course_notification(
        session,
        user_id=int(user.id),
        title=f"已加入《{course.title}》",
        content="你已通过课程代码加入该课程，无需等待教师审核。",
    )
    session.commit()
    return {"ok": True, "course_id": cid, "title": course.title}


@router.post("/courses/{course_id}/apply")
def apply_course(
    course_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    reason = str(payload.get("apply_reason") or "").strip()
    course = session.get(Course, course_id)
    if course is None or not bool(course.active):
        raise HTTPException(status_code=404, detail="课程不存在")
    existing = session.exec(
        select(CourseApplication).where(CourseApplication.course_id == course_id, CourseApplication.student_id == user.id)
    ).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="你已报名该课程，请勿重复提交")
    enrolled_count = len(
        session.exec(
            select(Enrollment.id).where(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
    )
    open_status = _course_open_status(course, enrolled_count)
    if open_status == CourseEnrollStatus.full.value:
        raise HTTPException(status_code=400, detail="课程名额已满")
    if open_status == CourseEnrollStatus.closed.value:
        raise HTTPException(status_code=400, detail="当前课程已关闭报名")
    if open_status == CourseEnrollStatus.expired.value:
        raise HTTPException(status_code=400, detail="已超过报名截止时间")

    prereqs = session.exec(select(CoursePrerequisite).where(CoursePrerequisite.course_id == course_id)).all()
    if prereqs:
        prereq_ids = [int(item.prerequisite_course_id) for item in prereqs]
        done_rows = session.exec(
            select(CourseCompletionRecord.course_id).where(
                CourseCompletionRecord.student_id == user.id,
                CourseCompletionRecord.course_id.in_(prereq_ids),
            )
        ).all()
        done_ids = {int(item) for item in done_rows}
        missing = [pid for pid in prereq_ids if pid not in done_ids]
        if missing:
            raise HTTPException(status_code=400, detail=f"未完成前置课程：{', '.join(str(item) for item in missing)}")

    application = CourseApplication(
        course_id=course_id,
        student_id=user.id,
        apply_reason=reason,
        status=ApplicationStatus.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(application)
    push_course_notification(
        session,
        user_id=user.id,
        title=f"《{course.title}》报名已提交",
        content="当前状态：审核中",
    )
    session.commit()
    session.refresh(application)
    return {"ok": True, "application_id": int(application.id), "status": application.status.value}


@router.get("/my/applications")
def my_applications(
    status: Optional[ApplicationStatus] = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    stmt = select(CourseApplication).where(CourseApplication.student_id == user.id).order_by(CourseApplication.created_at.desc())
    if status is not None:
        stmt = stmt.where(CourseApplication.status == status)
    rows = session.exec(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    course_ids = [int(item.course_id) for item in rows]
    course_map = {}
    if course_ids:
        course_rows = session.exec(select(Course).where(Course.id.in_(course_ids))).all()
        course_map = {int(item.id): item for item in course_rows if item.id is not None}
    items = []
    for row in rows:
        course = course_map.get(int(row.course_id))
        items.append(
            {
                "id": int(row.id),
                "course_id": int(row.course_id),
                "course_title": course.title if course else "",
                "status": row.status.value,
                "apply_reason": row.apply_reason,
                "review_remark": row.review_remark,
                "reject_reason": row.reject_reason,
                "created_at": row.created_at.isoformat(),
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            }
        )
    return {"items": items, "page": page, "page_size": page_size}


@router.get("/my/notifications")
def my_notifications(
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    rows = session.exec(
        select(CourseNotification).where(CourseNotification.user_id == user.id).order_by(CourseNotification.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": int(item.id),
                "type": item.type,
                "title": item.title,
                "content": item.content,
                "status": item.status.value,
                "created_at": item.created_at.isoformat(),
            }
            for item in rows
        ]
    }


@router.post("/my/notifications/{notice_id}/read")
def mark_notification_read(
    notice_id: int,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    notice = session.get(CourseNotification, notice_id)
    if notice is None or int(notice.user_id) != int(user.id):
        raise HTTPException(status_code=404, detail="通知不存在")
    notice.status = NotificationStatus.read
    session.add(notice)
    session.commit()
    return {"ok": True}


@router.get("/teacher/applications")
def teacher_applications(
    status: Optional[str] = Query(default=None),
    course_id: Optional[int] = Query(default=None),
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.teacher)),
):
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    course_stmt = select(Course.id).where(Course.teacher_id == user.id)
    if course_id is not None:
        course_stmt = course_stmt.where(Course.id == course_id)
    owned_course_ids = session.exec(course_stmt).all()
    if not owned_course_ids:
        return {"items": [], "page": page, "page_size": page_size}
    stmt = select(CourseApplication).where(CourseApplication.course_id.in_(owned_course_ids))
    if status is not None:
        normalized_status = status.strip().lower()
        try:
            stmt = stmt.where(CourseApplication.status == ApplicationStatus(normalized_status))
        except ValueError:
            raise HTTPException(status_code=422, detail="状态参数无效")
    stmt = stmt.order_by(CourseApplication.created_at.desc())
    rows = session.exec(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    course_rows = session.exec(select(Course).where(Course.id.in_(owned_course_ids))).all()
    course_map = {int(item.id): item for item in course_rows if item.id is not None}
    student_ids = [int(item.student_id) for item in rows]
    student_rows = session.exec(select(User).where(User.id.in_(student_ids))).all() if student_ids else []
    student_map = {int(item.id): item for item in student_rows if item.id is not None}
    items = []
    for row in rows:
        course = course_map.get(int(row.course_id))
        student = student_map.get(int(row.student_id))
        items.append(
            {
                "id": int(row.id),
                "course_id": int(row.course_id),
                "course_title": course.title if course else "",
                "student_id": int(row.student_id),
                "student_name": (student.full_name or student.username) if student else "",
                "status": row.status.value,
                "apply_reason": row.apply_reason,
                "review_remark": row.review_remark,
                "reject_reason": row.reject_reason,
                "created_at": row.created_at.isoformat(),
            }
        )
    return {"items": items, "page": page, "page_size": page_size}


@router.post("/teacher/applications/{application_id}/approve")
def approve_application(
    application_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.teacher)),
):
    remark = str(payload.get("review_remark") or "").strip()
    app = session.get(CourseApplication, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="报名申请不存在")
    course = session.get(Course, app.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    if int(course.teacher_id or 0) != int(user.id):
        raise HTTPException(status_code=403, detail="你只能审核自己课程的报名")
    if app.status != ApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="该申请已处理，不能重复审核")

    enrolled_count = len(
        session.exec(
            select(Enrollment.id).where(
                Enrollment.course_id == int(course.id),
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
    )
    if _course_open_status(course, enrolled_count) == CourseEnrollStatus.full.value:
        raise HTTPException(status_code=400, detail="课程名额已满，无法通过该申请")

    existed = session.exec(
        select(Enrollment).where(Enrollment.course_id == app.course_id, Enrollment.student_id == app.student_id)
    ).first()
    if existed is not None and existed.status == EnrollmentStatus.active:
        raise HTTPException(status_code=400, detail="该学生已在课程中，无需重复通过")

    app.status = ApplicationStatus.approved
    app.review_remark = remark
    app.reject_reason = ""
    app.reviewed_by = user.id
    app.reviewed_at = datetime.utcnow()
    app.updated_at = datetime.utcnow()
    session.add(app)
    if existed is None:
        session.add(
            Enrollment(
                student_id=app.student_id,
                course_id=app.course_id,
                application_id=app.id,
                status=EnrollmentStatus.active,
                enrolled_at=datetime.utcnow(),
            )
        )
    else:
        existed.application_id = app.id
        existed.status = EnrollmentStatus.active
        existed.enrolled_at = datetime.utcnow()
        session.add(existed)
    push_course_notification(
        session,
        user_id=app.student_id,
        title=f"《{course.title}》报名审核通过",
        content="你现在可以进入课程学习。",
    )
    session.commit()
    return {"ok": True}


@router.post("/teacher/applications/{application_id}/reject")
def reject_application(
    application_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.teacher)),
):
    reason = str(payload.get("reject_reason") or "").strip()
    remark = str(payload.get("review_remark") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="拒绝原因不能为空")
    app = session.get(CourseApplication, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="报名申请不存在")
    course = session.get(Course, app.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    if int(course.teacher_id or 0) != int(user.id):
        raise HTTPException(status_code=403, detail="你只能审核自己课程的报名")
    if app.status != ApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="该申请已处理，不能重复审核")

    app.status = ApplicationStatus.rejected
    app.review_remark = remark
    app.reject_reason = reason
    app.reviewed_by = user.id
    app.reviewed_at = datetime.utcnow()
    app.updated_at = datetime.utcnow()
    session.add(app)
    push_course_notification(
        session,
        user_id=app.student_id,
        title=f"《{course.title}》报名未通过",
        content=f"原因：{reason}",
    )
    session.commit()
    return {"ok": True}


@router.get("/courses/{course_id}/access-check")
def check_course_access(
    course_id: int,
    session: Session = Depends(get_session),
    user=Depends(require_role(UserRole.student)),
):
    _assert_student_course_access(session, user.id, course_id)
    return {"ok": True}
