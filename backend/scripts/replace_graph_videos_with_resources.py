from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.models import KnowledgePoint, LearningResource, ResourceType, VideoProgress  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402


SUBJECTS = {"高等数学", "楂樼瓑鏁板"}
GRADES = {"通用", "閫氱敤"}

RESOURCE_TEMPLATES = [
    {
        "title": "知识点讲义：概念与公式梳理",
        "url": "https://openstax.org/books/calculus-volume-1/pages/1-introduction",
        "type": ResourceType.link,
        "category": "learning",
        "description": "用于课堂演示的文字讲义资源，包含概念、公式和基础例题，适合替代视频作为学习证据。",
        "detected_resource_type": "link",
        "preview_type": "external_link",
        "tags": "midterm_demo,lecture_note,non_video",
    },
    {
        "title": "配套练习：典型题与答案解析",
        "url": "https://tutorial.math.lamar.edu/Classes/CalcI/CalcI.aspx",
        "type": ResourceType.link,
        "category": "recommend",
        "description": "用于中期答辩展示的拓展练习资源，学生访问后可作为资源学习行为参与掌握度计算。",
        "detected_resource_type": "link",
        "preview_type": "external_link",
        "tags": "midterm_demo,practice_set,non_video",
    },
]


def _is_demo_kp(kp: KnowledgePoint) -> bool:
    code = str(kp.code or "")
    return (
        code.startswith("HM-")
        or str(kp.subject or "") in SUBJECTS
        or str(kp.grade or "") in GRADES
    )


def _upsert_resource(session: Session, *, kp: KnowledgePoint, index: int) -> None:
    template = RESOURCE_TEMPLATES[index]
    title = f"{template['title']} - {kp.title}"
    row = session.exec(
        select(LearningResource).where(
            LearningResource.kp_id == int(kp.id),
            LearningResource.title == title,
        )
    ).first()
    if row is None:
        row = LearningResource(
            subject=kp.subject,
            grade=kp.grade,
            kp_id=int(kp.id),
            title=title,
        )
    row.subject = kp.subject
    row.grade = kp.grade
    row.url = str(template["url"])
    row.type = template["type"]
    row.category = str(template["category"])
    row.description = str(template["description"])
    row.tags = f"{template['tags']},{kp.code}"
    row.detected_resource_type = str(template["detected_resource_type"])
    row.preview_type = str(template["preview_type"])
    row.preview_status = "ready"
    row.preview_error = ""
    row.original_file_url = row.url
    row.converted_preview_url = ""
    row.source_kind = "external"
    row.updated_at = datetime.utcnow()
    session.add(row)


def run() -> None:
    init_db()
    with Session(engine) as session:
        kps = [kp for kp in session.exec(select(KnowledgePoint)).all() if kp.id is not None and _is_demo_kp(kp)]
        kp_ids = [int(kp.id) for kp in kps]
        if not kp_ids:
            print("没有找到高等数学图谱知识点，未修改资源。")
            return

        video_rows = session.exec(
            select(LearningResource).where(
                LearningResource.kp_id.in_(kp_ids),
                LearningResource.type == ResourceType.video,
            )
        ).all()
        video_ids = [int(row.id) for row in video_rows if row.id is not None]
        if video_ids:
            session.exec(delete(VideoProgress).where(VideoProgress.resource_id.in_(video_ids)))
            session.exec(delete(LearningResource).where(LearningResource.id.in_(video_ids)))

        for kp in kps:
            _upsert_resource(session, kp=kp, index=0)
            existing_non_video = session.exec(
                select(LearningResource)
                .where(
                    LearningResource.kp_id == int(kp.id),
                    LearningResource.type != ResourceType.video,
                )
                .order_by(LearningResource.id)
            ).all()
            if len(existing_non_video) < 2:
                _upsert_resource(session, kp=kp, index=1)

        session.commit()

        remaining_videos = session.exec(
            select(LearningResource).where(
                LearningResource.kp_id.in_(kp_ids),
                LearningResource.type == ResourceType.video,
            )
        ).all()
        print(f"已处理知识点 {len(kps)} 个，删除视频资源 {len(video_ids)} 条。")
        print(f"当前图谱剩余视频资源 {len(remaining_videos)} 条。")


if __name__ == "__main__":
    run()
