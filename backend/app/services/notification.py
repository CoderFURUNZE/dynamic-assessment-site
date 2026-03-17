from datetime import datetime

from sqlmodel import Session

from app.db.models import CourseNotification, NotificationStatus


def push_course_notification(session: Session, user_id: int, title: str, content: str, notice_type: str = "COURSE") -> None:
    notice = CourseNotification(
        user_id=user_id,
        type=notice_type,
        title=title,
        content=content,
        status=NotificationStatus.unread,
        created_at=datetime.utcnow(),
    )
    session.add(notice)
