import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.models import (
    ApplicationStatus,
    Course,
    CourseApplication,
    CourseCompletionRecord,
    CourseEnrollStatus,
    CoursePrerequisite,
    Enrollment,
    KpTask,
    KpTaskType,
    KpQuestionAssignment,
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    Mastery,
    Question,
    Quiz,
    QuizItem,
    RelationType,
    ResourceType,
    User,
    UserRole,
    EnrollmentStatus,
)
from app.db.session import get_session
from app.schemas.graph import (
    GraphBaseOut,
    GraphMapOut,
    GraphNodeDetailOut,
    GraphOverlayNodeOut,
    GraphPathOut,
    GraphPracticeOut,
    GraphQuizExamOut,
    GraphRelationNodeOut,
    GraphResourceOut,
    GraphTaskOut,
    KnowledgeEdgeOut,
    KnowledgePointOut,
)
from app.services.resource_files import build_resource_payload
from app.services.eval import upsert_mastery
from app.services.learner_profile import log_behavior_event

router = APIRouter(prefix="/graph", tags=["graph"])


def _relation_value(value) -> str:
    if isinstance(value, RelationType):
        return value.value
    if isinstance(value, str) and value:
        return value
    return RelationType.prerequisite.value


def _resource_value(value) -> str:
    if isinstance(value, ResourceType):
        return value.value
    if isinstance(value, str) and value:
        return value
    return ResourceType.note.value


def _task_value(value) -> str:
    if isinstance(value, KpTaskType):
        return value.value
    if isinstance(value, str) and value:
        return value
    return KpTaskType.task.value


def _kp_out(row: KnowledgePoint) -> KnowledgePointOut:
    return KnowledgePointOut(**row.model_dump())


def _course_payload(course: Course, teacher_name: str | None = None, enrolled: bool | None = None) -> dict:
    payload = {
        "id": int(course.id),
        "code": course.code,
        "title": course.title,
        "description": course.description,
        "active": bool(course.active),
        "teacher_id": course.teacher_id,
        "teacher_name": teacher_name or "",
        "max_students": int(course.max_students or 0),
        "apply_deadline": course.apply_deadline.isoformat() if course.apply_deadline else None,
        "enroll_status": course.enroll_status.value if isinstance(course.enroll_status, CourseEnrollStatus) else str(course.enroll_status),
    }
    if enrolled is not None:
        payload["enrolled"] = bool(enrolled)
    return payload


def _relation_nodes(kps: list[KnowledgePoint], ids: list[int]) -> list[GraphRelationNodeOut]:
    return [GraphRelationNodeOut(id=int(row.id), code=row.code, title=row.title) for row in kps if int(row.id) in ids]


def _assert_student_subject_access(session: Session, user_id: int, subject: str) -> None:
    course = session.exec(select(Course).where(Course.title == subject).order_by(Course.created_at.desc())).first()
    if course is None or course.id is None:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")
    app_ids = {
        int(item.id)
        for item in session.exec(
            select(CourseApplication).where(
                CourseApplication.student_id == user_id,
                CourseApplication.course_id == int(course.id),
                CourseApplication.status == ApplicationStatus.approved,
            )
        ).all()
        if item.id is not None
    }
    if not app_ids:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")
    enrollment = session.exec(
        select(Enrollment).where(
            Enrollment.student_id == user_id,
            Enrollment.course_id == int(course.id),
            Enrollment.status == EnrollmentStatus.active,
        )
    ).first()
    if enrollment is None or enrollment.application_id is None or int(enrollment.application_id) not in app_ids:
        raise HTTPException(status_code=403, detail="你尚未通过该课程审核，暂时无法进入课程")


@router.get("/kps", response_model=list[KnowledgePointOut])
def list_kps(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    rows = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    if _user.role == UserRole.student:
        _assert_student_subject_access(session, int(_user.id), subject)
    return [_kp_out(row) for row in rows]


@router.get("/courses")
def list_courses(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    stmt = select(Course).order_by(Course.created_at.desc())
    if user.role == UserRole.teacher:
        stmt = stmt.where(Course.teacher_id == user.id)
    elif user.role == UserRole.student:
        enrolled_rows = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == user.id,
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
        approved_app_ids = {
            int(item.id)
            for item in session.exec(
                select(CourseApplication).where(
                    CourseApplication.student_id == user.id,
                    CourseApplication.status == ApplicationStatus.approved,
                )
            ).all()
            if item.id is not None
        }
        enrolled_course_ids = [
            int(item.course_id)
            for item in enrolled_rows
            if item.application_id is not None and int(item.application_id) in approved_app_ids
        ]
        if not enrolled_course_ids:
            return []
        stmt = stmt.where(Course.id.in_(enrolled_course_ids))
    courses = session.exec(stmt).all()
    teacher_ids = [int(course.teacher_id) for course in courses if course.teacher_id is not None]
    teacher_map = {}
    if teacher_ids:
        teachers = session.exec(select(User).where(User.id.in_(teacher_ids))).all()
        teacher_map = {
            int(teacher.id): teacher.full_name or teacher.username
            for teacher in teachers
            if teacher.id is not None
        }
    return [
        _course_payload(c, teacher_name=teacher_map.get(int(c.teacher_id)) if c.teacher_id is not None else "")
        for c in courses
    ]


@router.get("/available-courses")
def list_available_courses(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can browse available courses")
    courses = session.exec(select(Course).where(Course.active == True).order_by(Course.created_at.desc())).all()  # noqa: E712
    applications = session.exec(
        select(CourseApplication).where(
            CourseApplication.student_id == user.id,
        )
    ).all()
    app_map = {int(item.course_id): item for item in applications}
    teacher_ids = [int(course.teacher_id) for course in courses if course.teacher_id is not None]
    teacher_map = {}
    if teacher_ids:
        teachers = session.exec(select(User).where(User.id.in_(teacher_ids))).all()
        teacher_map = {
            int(teacher.id): teacher.full_name or teacher.username
            for teacher in teachers
            if teacher.id is not None
        }
    return [
        _course_payload(
            course,
            teacher_name=teacher_map.get(int(course.teacher_id)) if course.teacher_id is not None else "",
            enrolled=bool(app_map.get(int(course.id))),
        )
        for course in courses
        if course.id is not None
    ]


@router.get("/my-courses")
def list_my_courses(
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can view enrolled courses")
    return list_courses(session=session, user=user)


@router.post("/courses/{course_id}/enroll")
def enroll_course(
    course_id: int,
    payload: dict | None = None,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students can enroll courses")
    payload = payload or {}
    reason = str(payload.get("apply_reason") or "").strip()
    course = session.get(Course, course_id)
    if course is None or not bool(course.active):
        raise HTTPException(status_code=404, detail="Course not found")
    status_value = course.enroll_status.value if isinstance(course.enroll_status, CourseEnrollStatus) else str(course.enroll_status or "")
    if status_value != CourseEnrollStatus.open.value:
        raise HTTPException(status_code=400, detail="当前课程不可报名")
    if course.apply_deadline is not None and datetime.utcnow() > course.apply_deadline:
        raise HTTPException(status_code=400, detail="已超过报名截止时间")
    active_count = len(
        session.exec(
            select(Enrollment.id).where(
                Enrollment.course_id == course_id,
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
    )
    if active_count >= int(course.max_students or 0):
        raise HTTPException(status_code=400, detail="课程名额已满")
    prereqs = session.exec(select(CoursePrerequisite).where(CoursePrerequisite.course_id == course_id)).all()
    if prereqs:
        prereq_ids = [int(item.prerequisite_course_id) for item in prereqs]
        completed = session.exec(
            select(CourseCompletionRecord.course_id).where(
                CourseCompletionRecord.student_id == user.id,
                CourseCompletionRecord.course_id.in_(prereq_ids),
            )
        ).all()
        done_ids = {int(item) for item in completed}
        missing = [cid for cid in prereq_ids if cid not in done_ids]
        if missing:
            raise HTTPException(status_code=400, detail=f"未完成前置课程：{', '.join(str(item) for item in missing)}")
    existing = session.exec(
        select(CourseApplication).where(CourseApplication.student_id == user.id, CourseApplication.course_id == course_id)
    ).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Already applied")
    application = CourseApplication(
        course_id=course_id,
        student_id=user.id,
        apply_reason=reason,
        status=ApplicationStatus.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    return {"ok": True, "status": ApplicationStatus.pending.value, "course_id": course_id}


@router.get("/courses/{course_id}/students")
def list_course_students(
    course_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role != UserRole.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can view enrolled students")
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if int(course.teacher_id or 0) != int(user.id):
        raise HTTPException(status_code=403, detail="You can only manage your own course students")
    enrollments = session.exec(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.status == EnrollmentStatus.active)
    ).all()
    student_ids = [int(item.student_id) for item in enrollments]
    students = []
    if student_ids:
        student_rows = session.exec(select(User).where(User.id.in_(student_ids))).all()
        student_map = {int(item.id): item for item in student_rows if item.id is not None}
        for enrollment in enrollments:
            student = student_map.get(int(enrollment.student_id))
            if student is None:
                continue
            students.append(
                {
                    "id": int(student.id),
                    "username": student.username,
                    "full_name": student.full_name,
                    "student_no": student.student_no,
                    "class_name": student.class_name,
                    "active": bool(student.active),
                    "enrolled_at": enrollment.enrolled_at.isoformat(),
                }
            )
    return {
        "course": _course_payload(course, teacher_name=user.full_name or user.username),
        "count": len(students),
        "items": students,
    }


@router.delete("/courses/{course_id}/students/{student_id}")
def remove_course_student(
    course_id: int,
    student_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role != UserRole.teacher:
        raise HTTPException(status_code=403, detail="Only teachers can manage enrolled students")
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if int(course.teacher_id or 0) != int(user.id):
        raise HTTPException(status_code=403, detail="You can only manage your own course students")
    enrollment = session.exec(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == student_id)
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    session.delete(enrollment)
    session.commit()
    return {"ok": True}


@router.get("/edges", response_model=list[KnowledgeEdgeOut])
def list_edges(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    edges = session.exec(
        select(KnowledgeEdge)
        .where(KnowledgeEdge.subject == subject, KnowledgeEdge.grade == grade)
        .order_by(KnowledgeEdge.id)
    ).all()
    return [
        KnowledgeEdgeOut(prereq_id=e.prereq_id, next_id=e.next_id, relation_type=_relation_value(e.relation_type))
        for e in edges
    ]


@router.get("/map", response_model=GraphMapOut)
def graph_map(
    subject: str,
    grade: str,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    if user.role == UserRole.student:
        _assert_student_subject_access(session, int(user.id), subject)
    kps = session.exec(
        select(KnowledgePoint)
        .where(KnowledgePoint.subject == subject, KnowledgePoint.grade == grade)
        .order_by(KnowledgePoint.chapter, KnowledgePoint.id)
    ).all()
    edges = session.exec(
        select(KnowledgeEdge)
        .where(KnowledgeEdge.subject == subject, KnowledgeEdge.grade == grade)
        .order_by(KnowledgeEdge.id)
    ).all()
    course = session.exec(select(Course).where(Course.title == subject).order_by(Course.created_at.desc())).first()

    kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
    mastery_map: dict[int, Mastery] = {}
    if user.role == UserRole.student:
        for kp in kps:
            if kp.id is None:
                continue
            try:
                mastery_map[int(kp.id)] = upsert_mastery(
                    session,
                    user_id=user.id,
                    kp_id=int(kp.id),
                    subject=subject,
                    grade=grade,
                )
            except Exception:
                existing = session.exec(
                    select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == int(kp.id))
                ).first()
                if existing is not None:
                    mastery_map[int(kp.id)] = existing
        try:
            log_behavior_event(
                session,
                user_id=user.id,
                event_type="graph_view",
                subject=subject,
                grade=grade,
                payload={"subject": subject, "grade": grade},
            )
        except Exception:
            pass

    kp_title_map = {int(kp.id): kp.title for kp in kps if kp.id is not None}
    overlay: list[GraphOverlayNodeOut] = []
    for kp in kps:
        blocked_reason = None
        status = "not_started"
        mastery_value = 0.0
        if kp.id is not None and int(kp.id) in mastery_map:
            mastery = mastery_map[int(kp.id)]
            mastery_value = float(mastery.value)
            status = mastery.status
        prereqs = [
            int(edge.prereq_id)
            for edge in edges
            if int(edge.next_id) == int(kp.id) and _relation_value(edge.relation_type) == RelationType.prerequisite.value
        ]
        blocked = [
            pid
            for pid in prereqs
            if pid not in mastery_map or float(mastery_map[pid].value) < 0.6
        ]
        if blocked:
            blocked_titles = [kp_title_map.get(item, str(item)) for item in blocked[:3]]
            blocked_reason = f"前驱未完成：{'、'.join(blocked_titles)}"
        overlay.append(
            GraphOverlayNodeOut(
                kp_id=int(kp.id),
                mastery=mastery_value,
                status=status,
                recommended=False,
                blocked_reason=blocked_reason,
            )
        )

    return GraphMapOut(
        base=GraphBaseOut(
            course=course.model_dump() if course is not None else None,
            kps=[_kp_out(kp) for kp in kps],
            edges=[
                KnowledgeEdgeOut(
                    prereq_id=edge.prereq_id,
                    next_id=edge.next_id,
                    relation_type=_relation_value(edge.relation_type),
                )
                for edge in edges
            ],
        ),
        overlay=overlay,
    )


@router.get("/node/{kp_id}", response_model=GraphNodeDetailOut)
def node_detail(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    kp = session.get(KnowledgePoint, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Knowledge point not found")
    if user.role == UserRole.student:
        _assert_student_subject_access(session, int(user.id), kp.subject)

    overlay = None
    if user.role == UserRole.student:
        try:
            mastery = upsert_mastery(session, user_id=user.id, kp_id=kp_id, subject=kp.subject, grade=kp.grade)
        except Exception:
            mastery = session.exec(select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == kp_id)).first()
        if mastery is not None:
            edges = session.exec(
                select(KnowledgeEdge).where(
                    KnowledgeEdge.subject == kp.subject,
                    KnowledgeEdge.grade == kp.grade,
                )
            ).all()
            prereqs = [
                int(edge.prereq_id)
                for edge in edges
                if int(edge.next_id) == kp_id and _relation_value(edge.relation_type) == RelationType.prerequisite.value
            ]
            blocked = []
            for prereq_id in prereqs:
                prereq_mastery = session.exec(
                    select(Mastery).where(Mastery.user_id == user.id, Mastery.kp_id == prereq_id)
                ).first()
                if prereq_mastery is None or float(prereq_mastery.value) < 0.6:
                    blocked.append(prereq_id)
            blocked_titles = []
            if blocked:
                blocked_kps = session.exec(select(KnowledgePoint).where(KnowledgePoint.id.in_(blocked[:3]))).all()
                blocked_titles = [item.title for item in blocked_kps]
            overlay = GraphOverlayNodeOut(
                kp_id=kp_id,
                mastery=float(mastery.value),
                status=mastery.status,
                recommended=False,
                blocked_reason=f"前驱未完成：{'、'.join(blocked_titles or [str(item) for item in blocked[:3]])}" if blocked else None,
            )

    resource_rows = session.exec(
        select(LearningResource).where(LearningResource.kp_id == kp_id).order_by(LearningResource.id)
    ).all()
    task_rows = session.exec(
        select(KpTask).where(KpTask.kp_id == kp_id).order_by(KpTask.sort_order, KpTask.id)
    ).all()

    assign_rows = session.exec(
        select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id).order_by(KpQuestionAssignment.order)
    ).all()
    assigned_qids = [int(row.question_id) for row in assign_rows if row.question_id is not None]
    practice_rows: list[Question]
    if assigned_qids:
        all_questions = session.exec(select(Question).where(Question.id.in_(assigned_qids))).all()
        qmap = {int(row.id): row for row in all_questions if row.id is not None}
        practice_rows = [qmap[qid] for qid in assigned_qids if qid in qmap][:5]
    else:
        practice_rows = session.exec(select(Question).where(Question.kp_id == kp_id).order_by(Question.id).limit(5)).all()

    quiz = session.exec(select(Quiz).where(Quiz.kp_id == kp_id)).first()
    quiz_or_exam_list: list[GraphQuizExamOut] = []
    if quiz is not None and quiz.id is not None:
        quiz_item_count = session.exec(select(QuizItem).where(QuizItem.quiz_id == quiz.id)).all()
        quiz_or_exam_list.append(
            GraphQuizExamOut(
                kind="quiz",
                id=int(quiz.id),
                title="知识点小测",
                item_count=len(quiz_item_count),
                pass_accuracy=float(quiz.pass_accuracy),
                description=f"已配置 {len(quiz_item_count)} 道小测题",
                link_url="",
            )
        )
    for row in task_rows:
        if _task_value(row.type) != KpTaskType.exam.value or row.id is None:
            continue
        quiz_or_exam_list.append(
            GraphQuizExamOut(
                kind="exam",
                id=int(row.id),
                title=row.title,
                item_count=0,
                pass_accuracy=None,
                description=row.description,
                link_url=row.link_url,
            )
        )

    relation_edges = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.subject == kp.subject,
            KnowledgeEdge.grade == kp.grade,
        )
    ).all()
    relation_ids = {int(edge.prereq_id) for edge in relation_edges} | {int(edge.next_id) for edge in relation_edges}
    relation_kps = []
    if relation_ids:
        relation_kps = session.exec(select(KnowledgePoint).where(KnowledgePoint.id.in_(relation_ids))).all()

    prereq_ids = [
        int(edge.prereq_id)
        for edge in relation_edges
        if int(edge.next_id) == kp_id and _relation_value(edge.relation_type) == RelationType.prerequisite.value
    ]
    downstream_ids = [
        int(edge.next_id)
        for edge in relation_edges
        if int(edge.prereq_id) == kp_id and _relation_value(edge.relation_type) == RelationType.prerequisite.value
    ]
    related_ids = [
        int(edge.next_id if int(edge.prereq_id) == kp_id else edge.prereq_id)
        for edge in relation_edges
        if _relation_value(edge.relation_type) == RelationType.related.value
        and (int(edge.prereq_id) == kp_id or int(edge.next_id) == kp_id)
    ]

    return GraphNodeDetailOut(
        kp=_kp_out(kp),
        overlay=overlay,
        prerequisites=_relation_nodes(relation_kps, prereq_ids),
        downstream=_relation_nodes(relation_kps, downstream_ids),
        related=_relation_nodes(relation_kps, related_ids),
        resource_list=[
            GraphResourceOut(**build_resource_payload(row))
            for row in resource_rows
            if row.id is not None
        ],
        task_list=[
            GraphTaskOut(
                id=int(row.id),
                kp_id=int(row.kp_id),
                type=_task_value(row.type),
                title=row.title,
                description=row.description,
                link_url=row.link_url,
                sort_order=int(row.sort_order or 0),
            )
            for row in task_rows
            if row.id is not None and _task_value(row.type) == KpTaskType.task.value
        ],
        practice_list=[
            GraphPracticeOut(
                id=int(row.id),
                kp_id=int(row.kp_id),
                type=row.type,
                prompt=row.prompt,
                difficulty=float(row.difficulty),
            )
            for row in practice_rows
            if row.id is not None
        ],
        quiz_or_exam_list=quiz_or_exam_list,
    )


@router.get("/path/{kp_id}", response_model=GraphPathOut)
def path(
    kp_id: int,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
):
    prereqs = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.next_id == kp_id,
            KnowledgeEdge.relation_type == RelationType.prerequisite,
        )
    ).all()
    prereq_ids = [int(p.prereq_id) for p in prereqs]
    next_edges = session.exec(
        select(KnowledgeEdge).where(
            KnowledgeEdge.prereq_id == kp_id,
            KnowledgeEdge.relation_type == RelationType.prerequisite,
        )
    ).all()
    next_ids = [int(e.next_id) for e in next_edges]

    blocked_prereqs: list[int] = []
    kp = session.get(KnowledgePoint, kp_id)
    if user.role == UserRole.student and kp is not None:
        for prereq_id in prereq_ids:
            mastery = upsert_mastery(session, user_id=user.id, kp_id=prereq_id, subject=kp.subject, grade=kp.grade)
            if float(mastery.value) < 0.6:
                blocked_prereqs.append(prereq_id)

    return GraphPathOut(
        kp_id=kp_id,
        prereq_chain=prereq_ids + [kp_id],
        blocked_prereqs=blocked_prereqs,
        next_candidates=next_ids,
    )
