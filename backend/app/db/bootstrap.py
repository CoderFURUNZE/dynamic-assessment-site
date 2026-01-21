from sqlmodel import Session, select

from app.core.security import hash_password
from app.db.models import EvalConfig, User, UserRole
from app.db.session import engine


def bootstrap_defaults() -> None:
    with Session(engine) as session:
        any_user = session.exec(select(User.id)).first()
        if not any_user:
            session.add(User(username="admin", password_hash=hash_password("admin123"), role=UserRole.admin))
            session.add(User(username="teacher1", password_hash=hash_password("teacher123"), role=UserRole.teacher))
            session.add(User(username="student1", password_hash=hash_password("student123"), role=UserRole.student))
            session.commit()

        cfg = session.exec(
            select(EvalConfig).where(EvalConfig.subject == "数学", EvalConfig.grade == "高二")
        ).first()
        if cfg is None:
            session.add(EvalConfig(subject="数学", grade="高二"))
            session.commit()

