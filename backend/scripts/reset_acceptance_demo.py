from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, SQLModel, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.bootstrap import bootstrap_defaults  # noqa: E402
from app.db.models import (  # noqa: E402
    ApplicationStatus,
    ChapterEdge,
    Course,
    CourseApplication,
    CourseEnrollStatus,
    CourseLifecycleStatus,
    CourseNotification,
    CoursePortraitIndicatorSelection,
    CourseStage,
    Enrollment,
    EnrollmentStatus,
    EvalConfig,
    KpQuestionAssignment,
    KpTask,
    KpTaskType,
    KnowledgeEdge,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    Note,
    PersonaType,
    PortraitDimension,
    PortraitIndicator,
    PortraitIndicatorSourceType,
    PracticeAttempt,
    Question,
    QuestionnairePortraitIndicatorInput,
    RecommendationLog,
    RelationType,
    ResourceType,
    ReviewSchedule,
    StageImportBatch,
    StageImportRecord,
    StageMetricType,
    StageTeacherFeedback,
    TeacherFinalScoreConfirmation,
    TeacherPortraitIndicatorInput,
    User,
    UserRole,
    VideoProgress,
)
from app.db.session import engine, init_db  # noqa: E402
from app.services.learner_profile import recalculate_profiles_for_subject, recalculate_stage_snapshots_for_stage  # noqa: E402


GRADE = "通用"
NOW = datetime(2026, 3, 16, 12, 0, 0)


def _resolve_sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    raw = database_url.removeprefix("sqlite:///")
    path = Path(raw)
    return (path if path.is_absolute() else (BASE_DIR / path)).resolve()


def _reset_database() -> None:
    db_path = _resolve_sqlite_path(settings.database_url)
    if db_path and db_path.exists():
        os.remove(db_path)
        print(f"Deleted sqlite db: {db_path}")
        return
    SQLModel.metadata.drop_all(engine)
    print("Dropped all tables.")


def _ensure_eval_config(session: Session, subject: str) -> None:
    row = session.exec(select(EvalConfig).where(EvalConfig.subject == subject, EvalConfig.grade == GRADE)).first()
    if row is None:
        session.add(EvalConfig(subject=subject, grade=GRADE))
        session.commit()


def _user(session: Session, username: str, *, password: str, role: UserRole, full_name: str, student_no: str = "", class_name: str = "") -> User:
    row = session.exec(select(User).where(User.username == username)).first()
    if row is None:
        row = User(username=username, password_hash=hash_password(password), role=role)
    row.password_hash = hash_password(password)
    row.role = role
    row.active = True
    row.full_name = full_name
    row.student_no = student_no
    row.class_name = class_name
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _course(session: Session, *, code: str, title: str, description: str, teacher_id: int, max_students: int = 120) -> Course:
    row = session.exec(select(Course).where(Course.code == code)).first()
    if row is None:
        row = Course(code=code, title=title)
    row.title = title
    row.description = description
    row.teacher_id = teacher_id
    row.active = True
    row.lifecycle_status = CourseLifecycleStatus.active
    row.start_at = NOW - timedelta(days=30)
    row.end_at = NOW + timedelta(days=365)
    row.max_students = max_students
    row.enroll_status = CourseEnrollStatus.open
    row.apply_deadline = NOW + timedelta(days=20)
    session.add(row)
    session.commit()
    session.refresh(row)
    _ensure_eval_config(session, title)
    return row


def _stage(session: Session, *, course: Course, order: int, title: str, starts_at: datetime, ends_at: datetime, description: str) -> CourseStage:
    row = session.exec(
        select(CourseStage).where(CourseStage.course_id == int(course.id), CourseStage.stage_order == order)
    ).first()
    if row is None:
        row = CourseStage(course_id=int(course.id), subject=course.title, grade=GRADE, stage_order=order, title=title)
    row.subject = course.title
    row.grade = GRADE
    row.title = title
    row.starts_at = starts_at
    row.ends_at = ends_at
    row.description = description
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _kp(
    session: Session,
    *,
    subject: str,
    code: str,
    title: str,
    chapter: str,
    description: str,
    x: float,
    y: float,
    difficulty: float,
    importance: float,
) -> KnowledgePoint:
    row = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if row is None:
        row = KnowledgePoint(subject=subject, grade=GRADE, code=code, title=title)
    row.subject = subject
    row.grade = GRADE
    row.title = title
    row.chapter = chapter
    row.description = description
    row.pos_x = x
    row.pos_y = y
    row.difficulty = difficulty
    row.importance = importance
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _edge(session: Session, *, subject: str, source_id: int, target_id: int, relation_type: RelationType) -> None:
    row = session.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == source_id, KnowledgeEdge.next_id == target_id)
    ).first()
    if row is None:
        row = KnowledgeEdge(subject=subject, grade=GRADE, prereq_id=source_id, next_id=target_id)
    row.subject = subject
    row.grade = GRADE
    row.relation_type = relation_type
    session.add(row)
    session.commit()


def _chapter_edge(session: Session, *, subject: str, source: str, target: str, relation_type: RelationType = RelationType.related) -> None:
    row = session.exec(
        select(ChapterEdge).where(
            ChapterEdge.subject == subject,
            ChapterEdge.grade == GRADE,
            ChapterEdge.source_chapter == source,
            ChapterEdge.target_chapter == target,
        )
    ).first()
    if row is None:
        row = ChapterEdge(subject=subject, grade=GRADE, source_chapter=source, target_chapter=target)
    row.relation_type = relation_type
    session.add(row)
    session.commit()


def _resource(
    session: Session,
    *,
    kp: KnowledgePoint,
    title: str,
    resource_type: ResourceType,
    category: str,
    url: str,
    description: str,
    tags: str = "",
    original_file_name: str = "",
    file_extension: str = "",
    detected_mime_type: str = "",
    detected_resource_type: str = "",
    preview_type: str = "",
    preview_status: str = "ready",
    converted_preview_url: str = "",
    original_file_url: str = "",
    source_kind: str = "external",
) -> LearningResource:
    row = session.exec(select(LearningResource).where(LearningResource.kp_id == int(kp.id), LearningResource.title == title)).first()
    if row is None:
        row = LearningResource(subject=kp.subject, grade=kp.grade, kp_id=int(kp.id), title=title, url=url, type=resource_type)
    row.subject = kp.subject
    row.grade = kp.grade
    row.kp_id = int(kp.id)
    row.title = title
    row.url = url
    row.type = resource_type
    row.category = category
    row.description = description
    row.tags = tags
    row.original_file_name = original_file_name
    row.file_extension = file_extension
    row.detected_mime_type = detected_mime_type
    row.detected_resource_type = detected_resource_type
    row.preview_type = preview_type
    row.preview_status = preview_status
    row.converted_preview_url = converted_preview_url
    row.original_file_url = original_file_url
    row.source_kind = source_kind
    row.updated_at = NOW
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _question(
    session: Session,
    *,
    kp: KnowledgePoint,
    prompt: str,
    answer: str,
    options: list[str],
    difficulty: float,
    explanation: str,
    cognitive_level: str = "understand",
    ability_subtags: str = "",
) -> Question:
    row = session.exec(select(Question).where(Question.kp_id == int(kp.id), Question.prompt == prompt)).first()
    if row is None:
        row = Question(subject=kp.subject, grade=kp.grade, kp_id=int(kp.id), type="mcq", prompt=prompt, answer=answer)
    row.subject = kp.subject
    row.grade = kp.grade
    row.type = "mcq"
    row.options_json = json.dumps(options, ensure_ascii=False)
    row.answer = answer
    row.explanation = explanation
    row.difficulty = difficulty
    row.source = "acceptance_demo"
    row.tags = kp.chapter
    row.cognitive_level = cognitive_level
    row.ability_subtags = ability_subtags
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _assign_question(session: Session, *, kp_id: int, question_id: int, order: int) -> None:
    row = session.exec(
        select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id, KpQuestionAssignment.question_id == question_id)
    ).first()
    if row is None:
        row = KpQuestionAssignment(kp_id=kp_id, question_id=question_id, order=order)
    row.order = order
    session.add(row)
    session.commit()


def _task(session: Session, *, kp: KnowledgePoint, title: str, description: str, link_url: str) -> None:
    row = session.exec(select(KpTask).where(KpTask.kp_id == int(kp.id), KpTask.title == title)).first()
    if row is None:
        row = KpTask(subject=kp.subject, grade=kp.grade, kp_id=int(kp.id), title=title)
    row.description = description
    row.link_url = link_url
    row.type = KpTaskType.task
    session.add(row)
    session.commit()


def _enable_course_indicators(session: Session, *, course_id: int, selected_by: str) -> tuple[list[PortraitIndicator], list[PortraitIndicator], list[PortraitIndicator]]:
    dimensions = session.exec(select(PortraitDimension)).all()
    indicators = session.exec(select(PortraitIndicator).where(PortraitIndicator.active == True)).all()  # noqa: E712
    existing = session.exec(select(CoursePortraitIndicatorSelection).where(CoursePortraitIndicatorSelection.course_id == course_id)).all()
    existing_map = {int(row.indicator_id): row for row in existing}
    for indicator in indicators:
        row = existing_map.get(int(indicator.id)) or CoursePortraitIndicatorSelection(
            course_id=course_id,
            dimension_id=int(indicator.dimension_id),
            indicator_id=int(indicator.id),
        )
        row.dimension_id = int(indicator.dimension_id)
        row.enabled = True
        row.weight = float(indicator.default_weight or 1.0)
        row.selected_by = selected_by
        row.updated_at = NOW
        session.add(row)
    session.commit()
    teacher_rows = [item for item in indicators if item.source_type == PortraitIndicatorSourceType.teacher]
    questionnaire_rows = [item for item in indicators if item.source_type == PortraitIndicatorSourceType.questionnaire]
    return indicators, teacher_rows, questionnaire_rows


def _application(
    session: Session,
    *,
    course_id: int,
    student_id: int,
    status: ApplicationStatus,
    reason: str,
    review_remark: str = "",
    reject_reason: str = "",
    reviewed_by: int | None = None,
) -> CourseApplication:
    row = session.exec(
        select(CourseApplication).where(CourseApplication.course_id == course_id, CourseApplication.student_id == student_id)
    ).first()
    if row is None:
        row = CourseApplication(course_id=course_id, student_id=student_id)
    row.apply_reason = reason
    row.status = status
    row.review_remark = review_remark
    row.reject_reason = reject_reason
    row.reviewed_by = reviewed_by
    row.reviewed_at = NOW if status != ApplicationStatus.pending else None
    row.created_at = NOW - timedelta(days=7)
    row.updated_at = NOW - timedelta(days=1)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _enrollment(session: Session, *, course_id: int, student_id: int, application_id: int) -> None:
    row = session.exec(select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == student_id)).first()
    if row is None:
        row = Enrollment(course_id=course_id, student_id=student_id, application_id=application_id)
    row.status = EnrollmentStatus.active
    row.application_id = application_id
    row.enrolled_at = NOW - timedelta(days=40)
    session.add(row)
    session.commit()


def _notification(session: Session, *, user_id: int, title: str, content: str) -> None:
    row = CourseNotification(user_id=user_id, title=title, content=content)
    row.created_at = NOW - timedelta(days=1)
    session.add(row)
    session.commit()


def _stage_batch(
    session: Session,
    *,
    course_id: int,
    stage: CourseStage,
    metric_type: StageMetricType,
    file_name: str,
    uploaded_by: str,
) -> StageImportBatch:
    row = StageImportBatch(
        course_id=course_id,
        stage_id=int(stage.id),
        subject=stage.subject,
        grade=stage.grade,
        metric_type=metric_type,
        file_name=file_name,
        uploaded_by=uploaded_by,
        total_rows=0,
        success_rows=0,
        failed_rows=0,
        error_json="[]",
        created_at=stage.ends_at or NOW,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _stage_record(session: Session, **kwargs) -> None:
    row = StageImportRecord(**kwargs)
    session.add(row)
    session.commit()


def seed_acceptance_demo() -> None:
    _reset_database()
    init_db()
    bootstrap_defaults()

    with Session(engine) as session:
        admin = _user(session, "admin", password="admin123", role=UserRole.admin, full_name="系统管理员")
        teacher = _user(session, "teacher1", password="teacher123", role=UserRole.teacher, full_name="王敏")
        students = [
            _user(session, "student1", password="student123", role=UserRole.student, full_name="李晨", student_no="2026001", class_name="计科2301"),
            _user(session, "student2", password="student123", role=UserRole.student, full_name="周悦", student_no="2026002", class_name="计科2301"),
            _user(session, "student3", password="student123", role=UserRole.student, full_name="陈昊", student_no="2026003", class_name="计科2302"),
            _user(session, "student4", password="student123", role=UserRole.student, full_name="林雪", student_no="2026004", class_name="计科2302"),
            _user(session, "student5", password="student123", role=UserRole.student, full_name="赵彤", student_no="2026005", class_name="计科2303"),
        ]

        os_course = _course(
            session,
            code="OS",
            title="操作系统",
            description="围绕操作系统原理、并发机制、存储管理和文件系统展开，适合阶段画像与知识图谱联动演示。",
            teacher_id=int(teacher.id),
            max_students=80,
        )
        _course(session, code="DS", title="数据结构", description="数据结构课程，包含线性表、树、图与排序。", teacher_id=int(teacher.id))
        _course(session, code="CN", title="计算机网络", description="计算机网络课程，覆盖体系结构、路由与应用层。", teacher_id=int(teacher.id))

        stage1 = _stage(
            session,
            course=os_course,
            order=1,
            title="阶段一：系统基础与进程管理",
            starts_at=datetime(2026, 1, 3, 9, 0, 0),
            ends_at=datetime(2026, 1, 26, 18, 0, 0),
            description="完成操作系统概述、进程线程与 CPU 调度的学习与阶段评价。",
        )
        stage2 = _stage(
            session,
            course=os_course,
            order=2,
            title="阶段二：并发控制与死锁",
            starts_at=datetime(2026, 1, 27, 9, 0, 0),
            ends_at=datetime(2026, 2, 20, 18, 0, 0),
            description="完成同步互斥、信号量、经典同步问题与死锁处理。",
        )
        stage3 = _stage(
            session,
            course=os_course,
            order=3,
            title="阶段三：存储管理与文件系统",
            starts_at=datetime(2026, 2, 21, 9, 0, 0),
            ends_at=datetime(2026, 3, 20, 18, 0, 0),
            description="完成内存管理、虚拟内存、文件系统和设备管理。",
        )

        os_kps = [
            _kp(session, subject="操作系统", code="OS-1", title="操作系统概述", chapter="系统基础", description="理解操作系统目标、发展脉络与核心职能。", x=120, y=120, difficulty=0.25, importance=0.75),
            _kp(session, subject="操作系统", code="OS-2", title="进程与线程", chapter="系统基础", description="掌握进程、线程、PCB 与状态转换。", x=280, y=180, difficulty=0.45, importance=0.88),
            _kp(session, subject="操作系统", code="OS-3", title="CPU 调度", chapter="系统基础", description="分析 FCFS、SJF、RR 等调度算法的差异。", x=460, y=160, difficulty=0.52, importance=0.83),
            _kp(session, subject="操作系统", code="OS-4", title="同步与互斥", chapter="并发控制", description="理解临界区、锁、信号量与同步问题。", x=640, y=210, difficulty=0.66, importance=0.93),
            _kp(session, subject="操作系统", code="OS-5", title="死锁", chapter="并发控制", description="识别死锁条件并比较处理策略。", x=820, y=240, difficulty=0.7, importance=0.9),
            _kp(session, subject="操作系统", code="OS-6", title="内存管理", chapter="存储管理", description="掌握分页、分段与地址转换。", x=980, y=170, difficulty=0.62, importance=0.94),
            _kp(session, subject="操作系统", code="OS-7", title="虚拟内存", chapter="存储管理", description="理解局部性、页面置换与抖动。", x=1160, y=220, difficulty=0.75, importance=0.91),
            _kp(session, subject="操作系统", code="OS-8", title="文件系统", chapter="存储管理", description="理解目录结构、索引分配与一致性问题。", x=1340, y=180, difficulty=0.6, importance=0.86),
        ]
        for source, target in zip(os_kps, os_kps[1:]):
            _edge(session, subject="操作系统", source_id=int(source.id), target_id=int(target.id), relation_type=RelationType.prerequisite)
        _edge(session, subject="操作系统", source_id=int(os_kps[1].id), target_id=int(os_kps[3].id), relation_type=RelationType.related)
        _edge(session, subject="操作系统", source_id=int(os_kps[5].id), target_id=int(os_kps[7].id), relation_type=RelationType.related)
        _chapter_edge(session, subject="操作系统", source="系统基础", target="并发控制")
        _chapter_edge(session, subject="操作系统", source="并发控制", target="存储管理")

        pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        video_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
        image_url = "https://picsum.photos/1200/800"

        _resource(
            session,
            kp=os_kps[5],
            title="内存管理讲义",
            resource_type=ResourceType.pdf,
            category="learning",
            url=pdf_url,
            description="课程讲义，包含分页、分段和地址映射示意图。",
            tags="讲义,分页,分段",
            original_file_name="内存管理讲义.pdf",
            file_extension=".pdf",
            detected_mime_type="application/pdf",
            detected_resource_type="pdf",
            preview_type="pdf",
            converted_preview_url=pdf_url,
            original_file_url=pdf_url,
        )
        _resource(
            session,
            kp=os_kps[5],
            title="虚拟内存课件",
            resource_type=ResourceType.pptx,
            category="learning",
            url=pdf_url,
            description="老师课件，系统已转换为 PDF 预览版。",
            tags="课件,虚拟内存",
            original_file_name="虚拟内存课件.pptx",
            file_extension=".pptx",
            detected_mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            detected_resource_type="pptx",
            preview_type="pdf_after_convert",
            converted_preview_url=pdf_url,
            original_file_url=pdf_url,
            source_kind="upload",
        )
        _resource(
            session,
            kp=os_kps[7],
            title="文件系统实验指导",
            resource_type=ResourceType.docx,
            category="learning",
            url=pdf_url,
            description="实验指导手册，学生端预览转换后的 PDF。",
            tags="实验,文件系统",
            original_file_name="文件系统实验指导.docx",
            file_extension=".docx",
            detected_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            detected_resource_type="docx",
            preview_type="pdf_after_convert",
            converted_preview_url=pdf_url,
            original_file_url=pdf_url,
            source_kind="upload",
        )
        video_resource = _resource(
            session,
            kp=os_kps[1],
            title="进程与线程动画讲解",
            resource_type=ResourceType.video,
            category="learning",
            url=video_url,
            description="用动画方式梳理进程切换、线程切换与并发执行流程。",
            tags="视频,进程,线程",
            detected_mime_type="video/mp4",
            detected_resource_type="video",
            preview_type="video",
            original_file_url=video_url,
        )
        _resource(
            session,
            kp=os_kps[3],
            title="PV 操作流程图",
            resource_type=ResourceType.image,
            category="learning",
            url=image_url,
            description="同步互斥中的 PV 过程图，适合课堂讲解与复盘。",
            tags="图片,PV,同步互斥",
            detected_mime_type="image/jpeg",
            detected_resource_type="image",
            preview_type="image",
            original_file_url=image_url,
        )
        _resource(
            session,
            kp=os_kps[7],
            title="EXT4 文件系统阅读链接",
            resource_type=ResourceType.link,
            category="recommend",
            url="https://www.kernel.org/doc/html/latest/filesystems/ext4/index.html",
            description="拓展阅读：Linux EXT4 文件系统官方文档。",
            tags="拓展,外部链接,文件系统",
            detected_mime_type="text/html",
            detected_resource_type="link",
            preview_type="external_link",
            original_file_url="https://www.kernel.org/doc/html/latest/filesystems/ext4/index.html",
        )

        for kp in os_kps:
            for idx in range(1, 5):
                _lvl_tags = [
                    ("understand", ""),
                    ("understand", "基础概念"),
                    ("apply", "逻辑推理"),
                    ("analyze", "系统分析"),
                ][idx - 1]
                question = _question(
                    session,
                    kp=kp,
                    prompt=f"{kp.title} 第 {idx} 题：以下哪项最符合课堂结论？",
                    answer="A",
                    options=[
                        f"A. {kp.title} 的核心概念说明",
                        f"B. {kp.title} 的常见误区",
                        f"C. {kp.title} 的性能优化建议",
                        f"D. {kp.title} 的扩展应用场景",
                    ],
                    difficulty=min(0.35 + idx * 0.08, 0.85),
                    explanation=f"{kp.title} 的这道题用于验收学生是否掌握课堂关键结论。",
                    cognitive_level=_lvl_tags[0],
                    ability_subtags=_lvl_tags[1],
                )
                _assign_question(session, kp_id=int(kp.id), question_id=int(question.id), order=idx)
            _task(
                session,
                kp=kp,
                title=f"{kp.title} 课堂任务",
                description=f"结合 {kp.title} 完成一张结构图或一个对比表，用于课堂汇报。",
                link_url="https://example.com/acceptance-task",
            )

        indicators, teacher_indicators, questionnaire_indicators = _enable_course_indicators(
            session,
            course_id=int(os_course.id),
            selected_by=teacher.username,
        )

        approved_1 = _application(
            session,
            course_id=int(os_course.id),
            student_id=int(students[0].id),
            status=ApplicationStatus.approved,
            reason="已经完成前导课程，希望通过图谱化方式系统复习操作系统。",
            review_remark="基础较好，允许直接进入课程。",
            reviewed_by=int(teacher.id),
        )
        approved_2 = _application(
            session,
            course_id=int(os_course.id),
            student_id=int(students[1].id),
            status=ApplicationStatus.approved,
            reason="希望重点提高并发控制和内存管理部分的理解。",
            review_remark="建议重点关注阶段二与阶段三的任务。",
            reviewed_by=int(teacher.id),
        )
        approved_3 = _application(
            session,
            course_id=int(os_course.id),
            student_id=int(students[2].id),
            status=ApplicationStatus.approved,
            reason="准备用于考研复习，希望跟随推荐链路逐步补强薄弱点。",
            review_remark="可进入课程，需按推荐链路完成补救学习。",
            reviewed_by=int(teacher.id),
        )
        _application(
            session,
            course_id=int(os_course.id),
            student_id=int(students[3].id),
            status=ApplicationStatus.pending,
            reason="希望先了解课程节奏，再决定是否投入更多时间。",
        )
        _application(
            session,
            course_id=int(os_course.id),
            student_id=int(students[4].id),
            status=ApplicationStatus.rejected,
            reason="目前同时选修课程较多，希望补充基础后再报名。",
            review_remark="建议先完成计算机组成原理前置内容。",
            reject_reason="当前前置基础不足，建议下轮再报。",
            reviewed_by=int(teacher.id),
        )
        _enrollment(session, course_id=int(os_course.id), student_id=int(students[0].id), application_id=int(approved_1.id))
        _enrollment(session, course_id=int(os_course.id), student_id=int(students[1].id), application_id=int(approved_2.id))
        _enrollment(session, course_id=int(os_course.id), student_id=int(students[2].id), application_id=int(approved_3.id))

        _notification(session, user_id=int(students[0].id), title="操作系统报名审核通过", content="你已通过《操作系统》课程审核，可以进入课程图谱学习。")
        _notification(session, user_id=int(students[3].id), title="操作系统报名审核中", content="老师正在处理你的报名申请，请耐心等待。")
        _notification(session, user_id=int(students[4].id), title="操作系统报名未通过", content="建议先补充前置基础后再报名。")

        questionnaire_seed = {
            int(students[0].id): [0.72, 0.80, 0.76],
            int(students[1].id): [0.64, 0.70, 0.68],
            int(students[2].id): [0.58, 0.63, 0.60],
        }
        for student_id, scores in questionnaire_seed.items():
            for indicator, score in zip(questionnaire_indicators, scores):
                session.add(
                    QuestionnairePortraitIndicatorInput(
                        user_id=student_id,
                        course_id=int(os_course.id),
                        dimension_id=int(indicator.dimension_id),
                        indicator_id=int(indicator.id),
                        score=score,
                        note="验收演示问卷数据",
                        updated_at=NOW - timedelta(days=8),
                    )
                )
        session.commit()

        teacher_stage_scores = {
            1: {
                int(students[0].id): [0.82, 0.78, 0.76],
                int(students[1].id): [0.74, 0.70, 0.72],
                int(students[2].id): [0.61, 0.58, 0.63],
            },
            2: {
                int(students[0].id): [0.85, 0.81, 0.79],
                int(students[1].id): [0.76, 0.73, 0.74],
                int(students[2].id): [0.67, 0.62, 0.65],
            },
            3: {
                int(students[0].id): [0.88, 0.84, 0.82],
                int(students[1].id): [0.79, 0.76, 0.78],
                int(students[2].id): [0.70, 0.66, 0.68],
            },
        }
        for stage in [stage1, stage2, stage3]:
            for student in students[:3]:
                session.add(
                    StageTeacherFeedback(
                        user_id=int(student.id),
                        course_id=int(os_course.id),
                        stage_id=int(stage.id),
                        subject="操作系统",
                        grade=GRADE,
                        feedback_tag="表现稳定" if int(student.id) != int(students[2].id) else "需加强前置补救",
                        comment=f"{student.full_name} 在{stage.title}中课堂互动真实、任务完成记录完整，便于老师验收阶段趋势。",
                        updated_by=teacher.username,
                        updated_at=(stage.ends_at or NOW) - timedelta(hours=2),
                    )
                )
                for indicator, score in zip(teacher_indicators[:3], teacher_stage_scores[stage.stage_order][int(student.id)]):
                    session.add(
                        TeacherPortraitIndicatorInput(
                            user_id=int(student.id),
                            course_id=int(os_course.id),
                            stage_id=int(stage.id),
                            dimension_id=int(indicator.dimension_id),
                            indicator_id=int(indicator.id),
                            score=score,
                            note=f"{stage.title} 老师补充评价",
                            updated_by=teacher.username,
                            updated_at=(stage.ends_at or NOW) - timedelta(hours=1),
                        )
                    )
        session.commit()

        active_students = students[:3]
        student_profiles = {
            int(students[0].id): {"name": students[0].full_name, "mastery": [0.82, 0.78, 0.76, 0.74, 0.71, 0.68, 0.64, 0.61], "video": 0.92, "practice": 0.88, "reco": 4},
            int(students[1].id): {"name": students[1].full_name, "mastery": [0.74, 0.69, 0.67, 0.63, 0.60, 0.58, 0.55, 0.52], "video": 0.81, "practice": 0.76, "reco": 3},
            int(students[2].id): {"name": students[2].full_name, "mastery": [0.60, 0.57, 0.53, 0.50, 0.46, 0.44, 0.40, 0.38], "video": 0.66, "practice": 0.61, "reco": 5},
        }

        for student in active_students:
            profile = student_profiles[int(student.id)]
            for index, kp in enumerate(os_kps):
                session.add(
                    Mastery(
                        user_id=int(student.id),
                        kp_id=int(kp.id),
                        value=profile["mastery"][index],
                        direct_value=max(profile["mastery"][index] - 0.04, 0.0),
                        status="mastered" if profile["mastery"][index] >= 0.7 else "learning",
                        reason_summary=f"{student.full_name} 在 {kp.title} 的掌握度来自练习、视频和阶段导入。",
                        updated_at=NOW - timedelta(days=max(1, 12 - index)),
                    )
                )
                session.add(
                    Note(
                        user_id=int(student.id),
                        kp_id=int(kp.id),
                        content=f"{student.full_name} 的课堂笔记：{kp.title} 需要重点关注 {kp.description}",
                        created_at=NOW - timedelta(days=max(1, 11 - index)),
                    )
                )
            session.add(
                VideoProgress(
                    user_id=int(student.id),
                    kp_id=int(os_kps[1].id),
                    resource_id=int(video_resource.id),
                    watched_seconds=profile["video"] * 600,
                    duration_seconds=600,
                    last_position_seconds=profile["video"] * 600,
                    completed=profile["video"] >= 0.85,
                    updated_at=NOW - timedelta(days=3),
                )
            )
            created_questions = session.exec(
                select(Question).where(Question.kp_id.in_([int(k.id) for k in os_kps])).order_by(Question.id)
            ).all()
            for attempt_index, question in enumerate(created_questions[:10]):
                correct = attempt_index % 5 != 0 or int(student.id) != int(students[2].id)
                session.add(
                    PracticeAttempt(
                        user_id=int(student.id),
                        question_id=int(question.id),
                        kp_id=int(question.kp_id),
                        correct=correct,
                        self_report="confident" if correct else "uncertain",
                        duration_ms=55000 + attempt_index * 4000,
                        created_at=NOW - timedelta(days=10 - min(attempt_index, 7)),
                    )
                )
            for ridx in range(profile["reco"]):
                session.add(
                    RecommendationLog(
                        user_id=int(student.id),
                        subject="操作系统",
                        grade=GRADE,
                        source_kp_id=int(os_kps[min(ridx, len(os_kps) - 2)].id),
                        target_kp_id=int(os_kps[min(ridx + 1, len(os_kps) - 1)].id),
                        persona_type=PersonaType.steady if int(student.id) != int(students[2].id) else PersonaType.struggling,
                        reason_summary="根据前驱关系和当前掌握度推荐下一知识点。",
                        payload_json=json.dumps({"stage": "acceptance_demo", "step": ridx + 1}, ensure_ascii=False),
                        created_at=NOW - timedelta(days=6 - ridx),
                    )
                )
            session.add(
                LearningBehaviorEvent(
                    user_id=int(student.id),
                    course_id=int(os_course.id),
                    kp_id=int(os_kps[5].id),
                    event_type="resource_preview",
                    value_json=json.dumps({"resource": "memory_pdf", "count": 1}, ensure_ascii=False),
                    created_at=NOW - timedelta(days=4),
                )
            )
            session.add(
                ReviewSchedule(
                    user_id=int(student.id),
                    question_id=int(created_questions[0].id),
                    kp_id=int(created_questions[0].kp_id),
                    interval_days=3,
                    due_at=NOW - timedelta(days=1 if int(student.id) == int(students[2].id) else -2),
                    last_result="wrong" if int(student.id) == int(students[2].id) else "correct",
                    created_at=NOW - timedelta(days=8),
                    updated_at=NOW - timedelta(days=2),
                )
            )
        session.commit()

        stage_student_values = {
            int(students[0].id): {
                1: {"video": 0.93, "assignment": 0.89, "attendance": 1.0, "task": 0.82, "participation": 0.85},
                2: {"video": 0.90, "assignment": 0.86, "attendance": 1.0, "task": 0.84, "participation": 0.88},
                3: {"video": 0.95, "assignment": 0.91, "attendance": 1.0, "task": 0.89, "participation": 0.90},
            },
            int(students[1].id): {
                1: {"video": 0.82, "assignment": 0.77, "attendance": 1.0, "task": 0.74, "participation": 0.76},
                2: {"video": 0.84, "assignment": 0.79, "attendance": 0.96, "task": 0.77, "participation": 0.78},
                3: {"video": 0.86, "assignment": 0.82, "attendance": 0.98, "task": 0.80, "participation": 0.79},
            },
            int(students[2].id): {
                1: {"video": 0.68, "assignment": 0.62, "attendance": 0.92, "task": 0.58, "participation": 0.60},
                2: {"video": 0.72, "assignment": 0.64, "attendance": 0.94, "task": 0.61, "participation": 0.63},
                3: {"video": 0.76, "assignment": 0.67, "attendance": 0.95, "task": 0.65, "participation": 0.66},
            },
        }
        for stage in [stage1, stage2, stage3]:
            metrics = {
                StageMetricType.video: _stage_batch(session, course_id=int(os_course.id), stage=stage, metric_type=StageMetricType.video, file_name=f"{stage.title}_视频记录.csv", uploaded_by=teacher.username),
                StageMetricType.assignment: _stage_batch(session, course_id=int(os_course.id), stage=stage, metric_type=StageMetricType.assignment, file_name=f"{stage.title}_作业记录.csv", uploaded_by=teacher.username),
                StageMetricType.attendance: _stage_batch(session, course_id=int(os_course.id), stage=stage, metric_type=StageMetricType.attendance, file_name=f"{stage.title}_考勤记录.csv", uploaded_by=teacher.username),
                StageMetricType.task: _stage_batch(session, course_id=int(os_course.id), stage=stage, metric_type=StageMetricType.task, file_name=f"{stage.title}_任务记录.csv", uploaded_by=teacher.username),
                StageMetricType.participation: _stage_batch(session, course_id=int(os_course.id), stage=stage, metric_type=StageMetricType.participation, file_name=f"{stage.title}_课堂参与.csv", uploaded_by=teacher.username),
            }
            total_rows = 0
            for student in active_students:
                values = stage_student_values[int(student.id)][stage.stage_order]
                happened = (stage.ends_at or NOW) - timedelta(days=1)
                _stage_record(
                    session,
                    batch_id=int(metrics[StageMetricType.video].id),
                    course_id=int(os_course.id),
                    stage_id=int(stage.id),
                    user_id=int(student.id),
                    kp_id=int(os_kps[min(stage.stage_order + 1, len(os_kps) - 1)].id),
                    subject="操作系统",
                    grade=GRADE,
                    metric_type=StageMetricType.video,
                    score_value=values["video"] * 100,
                    completion_value=values["video"],
                    duration_minutes=60 + stage.stage_order * 12,
                    attendance_value=0.0,
                    submitted_on_time=False,
                    status="ready",
                    note=f"{student.full_name} 阶段视频学习记录",
                    happened_at=happened,
                    raw_json=json.dumps({"demo": True, "kind": "video"}, ensure_ascii=False),
                )
                _stage_record(
                    session,
                    batch_id=int(metrics[StageMetricType.assignment].id),
                    course_id=int(os_course.id),
                    stage_id=int(stage.id),
                    user_id=int(student.id),
                    kp_id=int(os_kps[min(stage.stage_order + 2, len(os_kps) - 1)].id),
                    subject="操作系统",
                    grade=GRADE,
                    metric_type=StageMetricType.assignment,
                    score_value=values["assignment"] * 100,
                    completion_value=1.0,
                    duration_minutes=35,
                    attendance_value=0.0,
                    submitted_on_time=True,
                    status="submitted",
                    note=f"{student.full_name} 阶段作业完成记录",
                    happened_at=happened,
                    raw_json=json.dumps({"demo": True, "kind": "assignment"}, ensure_ascii=False),
                )
                _stage_record(
                    session,
                    batch_id=int(metrics[StageMetricType.attendance].id),
                    course_id=int(os_course.id),
                    stage_id=int(stage.id),
                    user_id=int(student.id),
                    kp_id=None,
                    subject="操作系统",
                    grade=GRADE,
                    metric_type=StageMetricType.attendance,
                    score_value=values["attendance"] * 100,
                    completion_value=values["attendance"],
                    duration_minutes=0.0,
                    attendance_value=values["attendance"],
                    submitted_on_time=False,
                    status="present",
                    note=f"{student.full_name} 阶段考勤记录",
                    happened_at=happened,
                    raw_json=json.dumps({"demo": True, "kind": "attendance"}, ensure_ascii=False),
                )
                _stage_record(
                    session,
                    batch_id=int(metrics[StageMetricType.task].id),
                    course_id=int(os_course.id),
                    stage_id=int(stage.id),
                    user_id=int(student.id),
                    kp_id=int(os_kps[min(stage.stage_order + 2, len(os_kps) - 1)].id),
                    subject="操作系统",
                    grade=GRADE,
                    metric_type=StageMetricType.task,
                    score_value=values["task"] * 100,
                    completion_value=values["task"],
                    duration_minutes=40,
                    attendance_value=0.0,
                    submitted_on_time=False,
                    status="done",
                    note=f"{student.full_name} 阶段任务完成记录",
                    happened_at=happened,
                    raw_json=json.dumps({"demo": True, "kind": "task"}, ensure_ascii=False),
                )
                _stage_record(
                    session,
                    batch_id=int(metrics[StageMetricType.participation].id),
                    course_id=int(os_course.id),
                    stage_id=int(stage.id),
                    user_id=int(student.id),
                    kp_id=int(os_kps[min(stage.stage_order, len(os_kps) - 1)].id),
                    subject="操作系统",
                    grade=GRADE,
                    metric_type=StageMetricType.participation,
                    score_value=values["participation"] * 100,
                    completion_value=values["participation"],
                    duration_minutes=0.0,
                    attendance_value=0.0,
                    submitted_on_time=False,
                    status="active",
                    note=f"{student.full_name} 阶段课堂参与记录",
                    happened_at=happened,
                    raw_json=json.dumps({"demo": True, "kind": "participation"}, ensure_ascii=False),
                )
                total_rows += 5
            for batch in metrics.values():
                batch.total_rows = len(active_students)
                batch.success_rows = len(active_students)
                session.add(batch)
            session.commit()
            recalculate_stage_snapshots_for_stage(
                session,
                stage_id=int(stage.id),
                user_ids=[int(student.id) for student in active_students],
                persist=True,
            )

        recalculate_profiles_for_subject(session, subject="操作系统", grade=GRADE, refresh_mastery=False)

        latest_profiles = {
            int(row.user_id): row
            for row in session.exec(
                select(TeacherFinalScoreConfirmation)  # placeholder to satisfy typing in comprehension
            ).all()
        }
        latest_profiles = {}
        from app.db.models import LearnerProfileSnapshot  # local import to keep script flat

        for row in session.exec(
            select(LearnerProfileSnapshot).where(LearnerProfileSnapshot.subject == "操作系统", LearnerProfileSnapshot.grade == GRADE)
        ).all():
            latest_profiles[int(row.user_id)] = row

        for student in active_students:
            snapshot = latest_profiles.get(int(student.id))
            if snapshot is None:
                continue
            suggested = float(snapshot.dynamic_score)
            confirmed = min(0.95, suggested + (0.02 if int(student.id) != int(students[2].id) else 0.01))
            session.add(
                TeacherFinalScoreConfirmation(
                    user_id=int(student.id),
                    course_id=int(os_course.id),
                    subject="操作系统",
                    grade=GRADE,
                    suggested_score=suggested,
                    confirmed_score=confirmed,
                    confirmed_level="优秀" if confirmed >= 0.85 else "良好" if confirmed >= 0.72 else "中等",
                    comment=f"{student.full_name} 的期末评价结合阶段趋势、图谱掌握度和任务完成情况确认。",
                    recommendation_summary="已完成推荐链路收口，后续建议继续强化虚拟内存与文件系统的综合分析。",
                    confirmed_by=teacher.username,
                    confirmed_at=NOW - timedelta(hours=4),
                    updated_at=NOW - timedelta(hours=4),
                )
            )
        session.commit()

        print("Acceptance demo data ready.")
        print("Accounts:")
        print("  admin / admin123")
        print("  teacher1 / teacher123")
        print("  student1 / student123")
        print("  student2 / student123")
        print("  student3 / student123")
        print("  student4 / student123")
        print("  student5 / student123")
        print("Teacher demo course: 操作系统")


if __name__ == "__main__":
    seed_acceptance_demo()
