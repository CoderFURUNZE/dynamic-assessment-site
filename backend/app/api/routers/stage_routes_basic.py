import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.api.deps import require_role
from app.api.routers import stage_support
from app.db.models import CourseStage, StageImportBatch, StageMetricType, User, UserRole
from app.db.session import get_session
from app.schemas.stage import CourseStageIn, CourseStageOut, CourseStageUpdateIn, StageImportBatchOut, StageMetricGuideOut


router = APIRouter()


@router.get("/courses/{course_id}", response_model=list[CourseStageOut])
def list_stages(
    course_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = stage_support.get_course_or_403(session, user, course_id)
    rows = session.exec(
        select(CourseStage).where(CourseStage.course_id == course_id).order_by(CourseStage.stage_order, CourseStage.id)
    ).all()
    return [stage_support.course_out(row, course) for row in rows]


@router.post("/courses/{course_id}", response_model=CourseStageOut)
def create_stage(
    course_id: int,
    payload: CourseStageIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = stage_support.get_course_or_403(session, user, course_id)
    stage_support.assert_course_stage_editable(course)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    exists = session.exec(
        select(CourseStage).where(CourseStage.course_id == course_id, CourseStage.stage_order == payload.stage_order)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=400, detail="stage_order already exists in this course")
    try:
        starts_at = stage_support.parse_dt(payload.starts_at)
        ends_at = stage_support.parse_dt(payload.ends_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stage = CourseStage(
        course_id=course_id,
        subject=course.title,
        grade=(payload.grade or "通用").strip() or "通用",
        title=title,
        stage_order=max(1, int(payload.stage_order)),
        starts_at=starts_at,
        ends_at=ends_at,
        description=payload.description.strip(),
    )
    session.add(stage)
    session.commit()
    session.refresh(stage)
    stage_support.log_action(session, user, "course_stage_create", f"course_id={course_id} stage_id={stage.id}")
    return stage_support.course_out(stage, course)


@router.put("/{stage_id}", response_model=CourseStageOut)
def update_stage(
    stage_id: int,
    payload: CourseStageUpdateIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    stage = stage_support.get_stage_or_403(session, user, stage_id)
    course = stage_support.get_course_or_403(session, user, stage.course_id)
    stage_support.assert_course_stage_editable(course)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="title required")
        stage.title = title
    if payload.grade is not None:
        stage.grade = payload.grade.strip() or "通用"
    if payload.stage_order is not None:
        order_value = max(1, int(payload.stage_order))
        exists = session.exec(
            select(CourseStage).where(
                CourseStage.course_id == stage.course_id,
                CourseStage.stage_order == order_value,
                CourseStage.id != stage_id,
            )
        ).first()
        if exists is not None:
            raise HTTPException(status_code=400, detail="stage_order already exists in this course")
        stage.stage_order = order_value
    try:
        if payload.starts_at is not None:
            stage.starts_at = stage_support.parse_dt(payload.starts_at)
        if payload.ends_at is not None:
            stage.ends_at = stage_support.parse_dt(payload.ends_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.description is not None:
        stage.description = payload.description.strip()
    session.add(stage)
    session.commit()
    session.refresh(stage)
    stage_support.log_action(session, user, "course_stage_update", f"stage_id={stage_id}")
    return stage_support.course_out(stage, course)


@router.delete("/{stage_id}")
def delete_stage(
    stage_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    stage = stage_support.get_stage_or_403(session, user, stage_id)
    course = stage_support.get_course_or_403(session, user, stage.course_id)
    stage_support.assert_course_stage_editable(course)
    has_batch = session.exec(select(StageImportBatch).where(StageImportBatch.stage_id == stage_id)).first()
    if has_batch is not None:
        raise HTTPException(status_code=400, detail="Stage already has imported data and cannot be deleted")
    session.delete(stage)
    session.commit()
    stage_support.log_action(session, user, "course_stage_delete", f"stage_id={stage_id}")
    return {"ok": True}


@router.get("/template")
def download_template(
    metric_type: str,
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    _ = user
    try:
        metric = StageMetricType(metric_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid metric_type") from exc
    return Response(
        content="\ufeff" + stage_support.template_csv(metric),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="stage_template_{metric.value}.csv"'},
    )


@router.get("/metric-guides", response_model=list[StageMetricGuideOut])
def list_metric_guides(
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    _ = user
    return [stage_support.metric_guide(metric) for metric in StageMetricType]


@router.get("/imports", response_model=list[StageImportBatchOut])
def list_import_batches(
    course_id: int,
    stage_id: int | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    stage_support.get_course_or_403(session, user, course_id)
    query = select(StageImportBatch).where(StageImportBatch.course_id == course_id)
    if stage_id is not None:
        query = query.where(StageImportBatch.stage_id == stage_id)
    rows = session.exec(query.order_by(StageImportBatch.created_at.desc())).all()
    stage_map = {
        int(stage.id): stage.title
        for stage in session.exec(select(CourseStage).where(CourseStage.course_id == course_id)).all()
        if stage.id is not None
    }
    return [
        StageImportBatchOut(
            id=int(row.id),
            course_id=row.course_id,
            stage_id=row.stage_id,
            stage_title=stage_map.get(row.stage_id, f"阶段#{row.stage_id}"),
            subject=row.subject,
            grade=row.grade,
            metric_type=row.metric_type.value if hasattr(row.metric_type, "value") else str(row.metric_type),
            file_name=row.file_name,
            uploaded_by=row.uploaded_by,
            total_rows=row.total_rows,
            success_rows=row.success_rows,
            failed_rows=row.failed_rows,
            error_preview=list(json.loads(row.error_json or "[]"))[:5],
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
