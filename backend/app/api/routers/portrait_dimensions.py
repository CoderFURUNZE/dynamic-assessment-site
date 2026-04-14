from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import require_role, teacher_has_course_access
from app.api.routers import stage_support
from app.db.models import (
    Course,
    CourseStage,
    CoursePortraitIndicatorSelection,
    PortraitDimension,
    PortraitIndicator,
    PortraitIndicatorSourceType,
    QuestionnairePortraitIndicatorInput,
    TeacherPortraitIndicatorInput,
    User,
    UserRole,
)
from app.db.session import get_session
from app.schemas.admin import (
    CourseIndicatorSelectionIn,
    PortraitDimensionIn,
    PortraitDimensionUpdateIn,
    PortraitIndicatorIn,
    PortraitIndicatorUpdateIn,
    QuestionnairePortraitIndicatorInputIn,
    TeacherPortraitIndicatorInputIn,
)
from app.services.learner_profile import recalculate_profile_snapshot, recalculate_stage_snapshots_for_stage

router = APIRouter(prefix="/portrait", tags=["portrait"])


def _get_course_or_404(session: Session, course_id: int) -> Course:
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _ensure_course_permission(session: Session, user: User, course: Course) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.teacher and teacher_has_course_access(session=session, teacher_id=int(user.id), course=course):
        return
    raise HTTPException(status_code=403, detail="No permission for this course")


def _course_indicator_rows_for_teacher(*, session: Session, course_id: int) -> list[dict]:
    selections = session.exec(
        select(CoursePortraitIndicatorSelection).where(
            CoursePortraitIndicatorSelection.course_id == course_id,
            CoursePortraitIndicatorSelection.enabled == True,  # noqa: E712
        )
    ).all()
    rows: list[dict] = []
    for selection in selections:
        indicator = session.get(PortraitIndicator, selection.indicator_id)
        if indicator is None or not indicator.active or indicator.source_type != PortraitIndicatorSourceType.teacher:
            continue
        dimension = session.get(PortraitDimension, selection.dimension_id)
        if dimension is None or not dimension.active:
            continue
        rows.append(
            {
                "selection": selection,
                "indicator": indicator,
                "dimension": dimension,
                "weight": float(selection.weight or indicator.default_weight or 1.0),
            }
        )
    return rows


def _course_indicator_rows_for_questionnaire(*, session: Session, course_id: int) -> list[dict]:
    selections = session.exec(
        select(CoursePortraitIndicatorSelection).where(
            CoursePortraitIndicatorSelection.course_id == course_id,
            CoursePortraitIndicatorSelection.enabled == True,  # noqa: E712
        )
    ).all()
    rows: list[dict] = []
    for selection in selections:
        indicator = session.get(PortraitIndicator, selection.indicator_id)
        if indicator is None or not indicator.active or indicator.source_type != PortraitIndicatorSourceType.questionnaire:
            continue
        dimension = session.get(PortraitDimension, selection.dimension_id)
        if dimension is None or not dimension.active:
            continue
        rows.append(
            {
                "selection": selection,
                "indicator": indicator,
                "dimension": dimension,
                "weight": float(selection.weight or indicator.default_weight or 1.0),
            }
        )
    return rows


@router.get("/dimensions/tree")
def list_dimension_tree(
    session: Session = Depends(get_session),
    _user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    dimensions = session.exec(select(PortraitDimension).order_by(PortraitDimension.sort_order, PortraitDimension.id)).all()
    indicators = session.exec(select(PortraitIndicator).order_by(PortraitIndicator.sort_order, PortraitIndicator.id)).all()
    bucket: dict[int, list[PortraitIndicator]] = {}
    for item in indicators:
        bucket.setdefault(item.dimension_id, []).append(item)
    return {
        "items": [
            {
                "id": dim.id,
                "code": dim.code,
                "title": dim.title,
                "description": dim.description,
                "sort_order": dim.sort_order,
                "active": dim.active,
                "indicators": [
                    {
                        "id": indicator.id,
                        "dimension_id": indicator.dimension_id,
                        "code": indicator.code,
                        "title": indicator.title,
                        "description": indicator.description,
                        "source_type": indicator.source_type.value if hasattr(indicator.source_type, "value") else str(indicator.source_type),
                        "default_weight": indicator.default_weight,
                        "sort_order": indicator.sort_order,
                        "active": indicator.active,
                    }
                    for indicator in bucket.get(dim.id or 0, [])
                ],
            }
            for dim in dimensions
        ]
    }


@router.post("/dimensions")
def create_dimension(
    payload: PortraitDimensionIn,
    session: Session = Depends(get_session),
    admin: User = Depends(require_role(UserRole.admin)),
):
    exists = session.exec(select(PortraitDimension).where(PortraitDimension.code == payload.code)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Dimension code already exists")
    dimension = PortraitDimension(**payload.model_dump())
    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    return {"ok": True, "item": dimension}


@router.put("/dimensions/{dimension_id}")
def update_dimension(
    dimension_id: int,
    payload: PortraitDimensionUpdateIn,
    session: Session = Depends(get_session),
    admin: User = Depends(require_role(UserRole.admin)),
):
    _ = admin
    dimension = session.get(PortraitDimension, dimension_id)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(dimension, key, value)
    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    return {"ok": True, "item": dimension}


@router.post("/indicators")
def create_indicator(
    payload: PortraitIndicatorIn,
    session: Session = Depends(get_session),
    admin: User = Depends(require_role(UserRole.admin)),
):
    _ = admin
    dimension = session.get(PortraitDimension, payload.dimension_id)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    exists = session.exec(
        select(PortraitIndicator).where(
            PortraitIndicator.dimension_id == payload.dimension_id,
            PortraitIndicator.code == payload.code,
        )
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Indicator code already exists under dimension")
    indicator = PortraitIndicator(
        dimension_id=payload.dimension_id,
        code=payload.code,
        title=payload.title,
        description=payload.description,
        source_type=PortraitIndicatorSourceType(payload.source_type),
        default_weight=payload.default_weight,
        sort_order=payload.sort_order,
        active=payload.active,
    )
    session.add(indicator)
    session.commit()
    session.refresh(indicator)
    return {"ok": True, "item": indicator}


@router.put("/indicators/{indicator_id}")
def update_indicator(
    indicator_id: int,
    payload: PortraitIndicatorUpdateIn,
    session: Session = Depends(get_session),
    admin: User = Depends(require_role(UserRole.admin)),
):
    _ = admin
    indicator = session.get(PortraitIndicator, indicator_id)
    if not indicator:
        raise HTTPException(status_code=404, detail="Indicator not found")
    data = payload.model_dump(exclude_unset=True)
    if "source_type" in data:
        data["source_type"] = PortraitIndicatorSourceType(data["source_type"])
    for key, value in data.items():
        setattr(indicator, key, value)
    session.add(indicator)
    session.commit()
    session.refresh(indicator)
    return {"ok": True, "item": indicator}


@router.get("/course-selection")
def get_course_selection(
    course_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_404(session, course_id)
    _ensure_course_permission(session, user, course)
    dimensions = session.exec(select(PortraitDimension).order_by(PortraitDimension.sort_order, PortraitDimension.id)).all()
    indicators = session.exec(select(PortraitIndicator).order_by(PortraitIndicator.sort_order, PortraitIndicator.id)).all()
    selections = session.exec(
        select(CoursePortraitIndicatorSelection).where(CoursePortraitIndicatorSelection.course_id == course_id)
    ).all()
    selection_map = {item.indicator_id: item for item in selections}
    bucket: dict[int, list[PortraitIndicator]] = {}
    for indicator in indicators:
        bucket.setdefault(indicator.dimension_id, []).append(indicator)
    return {
        "course": {"id": course.id, "title": course.title, "teacher_id": course.teacher_id},
        "items": [
            {
                "id": dim.id,
                "code": dim.code,
                "title": dim.title,
                "description": dim.description,
                "active": dim.active,
                "indicators": [
                    {
                        "id": indicator.id,
                        "code": indicator.code,
                        "title": indicator.title,
                        "description": indicator.description,
                        "source_type": indicator.source_type.value if hasattr(indicator.source_type, "value") else str(indicator.source_type),
                        "default_weight": indicator.default_weight,
                        "active": indicator.active,
                        "selected": indicator.id in selection_map,
                        "enabled": selection_map[indicator.id].enabled if indicator.id in selection_map else False,
                        "weight": selection_map[indicator.id].weight if indicator.id in selection_map else indicator.default_weight,
                    }
                    for indicator in bucket.get(dim.id or 0, [])
                ],
            }
            for dim in dimensions
        ],
    }


@router.put("/course-selection")
def update_course_selection(
    course_id: int,
    payload: CourseIndicatorSelectionIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_404(session, course_id)
    _ensure_course_permission(session, user, course)

    existing = session.exec(
        select(CoursePortraitIndicatorSelection).where(CoursePortraitIndicatorSelection.course_id == course_id)
    ).all()
    existing_map = {item.indicator_id: item for item in existing}
    keep_ids: set[int] = set()

    for row in payload.selections:
        indicator_id = int(row.get("indicator_id") or 0)
        if not indicator_id:
            continue
        indicator = session.get(PortraitIndicator, indicator_id)
        if not indicator:
            continue
        keep_ids.add(indicator_id)
        enabled = bool(row.get("enabled", True))
        weight = float(row.get("weight") or indicator.default_weight or 0.0)
        selection = existing_map.get(indicator_id) or CoursePortraitIndicatorSelection(
            course_id=course_id,
            dimension_id=indicator.dimension_id,
            indicator_id=indicator_id,
            selected_by=user.username,
        )
        selection.dimension_id = indicator.dimension_id
        selection.enabled = enabled
        selection.weight = weight
        selection.selected_by = user.username
        selection.updated_at = datetime.utcnow()
        session.add(selection)

    for item in existing:
        if item.indicator_id not in keep_ids:
            session.delete(item)

    session.commit()
    return {"ok": True, "count": len(keep_ids)}


@router.get("/teacher-input")
def get_teacher_indicator_input(
    course_id: int,
    user_id: int,
    stage_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_404(session, course_id)
    _ensure_course_permission(session, user, course)
    rows = _course_indicator_rows_for_teacher(session=session, course_id=course_id)
    existing = session.exec(
        select(TeacherPortraitIndicatorInput).where(
            TeacherPortraitIndicatorInput.course_id == course_id,
            TeacherPortraitIndicatorInput.user_id == user_id,
            TeacherPortraitIndicatorInput.stage_id == stage_id,
        )
    ).all()
    existing_map = {int(item.indicator_id): item for item in existing}
    return {
        "items": [
            {
                "dimension_id": int(row["dimension"].id),
                "dimension_title": row["dimension"].title,
                "indicator_id": int(row["indicator"].id),
                "indicator_title": row["indicator"].title,
                "indicator_code": row["indicator"].code,
                "weight": row["weight"],
                "score": float(existing_map[int(row["indicator"].id)].score) if int(row["indicator"].id) in existing_map else None,
                "note": existing_map[int(row["indicator"].id)].note if int(row["indicator"].id) in existing_map else "",
            }
            for row in rows
        ]
    }


@router.put("/teacher-input")
def save_teacher_indicator_input(
    course_id: int,
    payload: TeacherPortraitIndicatorInputIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_404(session, course_id)
    _ensure_course_permission(session, user, course)
    valid_rows = _course_indicator_rows_for_teacher(session=session, course_id=course_id)
    valid_by_indicator = {int(row["indicator"].id): row for row in valid_rows}
    existing = session.exec(
        select(TeacherPortraitIndicatorInput).where(
            TeacherPortraitIndicatorInput.course_id == course_id,
            TeacherPortraitIndicatorInput.user_id == payload.user_id,
            TeacherPortraitIndicatorInput.stage_id == payload.stage_id,
        )
    ).all()
    existing_map = {int(item.indicator_id): item for item in existing}
    keep_ids: set[int] = set()

    input_rows = payload.inputs or payload.indicator_scores or []

    for row in input_rows:
        indicator_id = int(row.get("indicator_id") or 0)
        if indicator_id not in valid_by_indicator:
            continue
        score = row.get("score")
        note = str(row.get("note") or "").strip()
        if score in (None, ""):
            continue
        keep_ids.add(indicator_id)
        valid_row = valid_by_indicator[indicator_id]
        record = existing_map.get(indicator_id) or TeacherPortraitIndicatorInput(
            user_id=payload.user_id,
            course_id=course_id,
            stage_id=payload.stage_id,
            dimension_id=int(valid_row["dimension"].id),
            indicator_id=indicator_id,
        )
        record.dimension_id = int(valid_row["dimension"].id)
        record.score = max(0.0, min(1.0, float(score)))
        record.note = note
        record.updated_by = user.username
        record.updated_at = datetime.utcnow()
        session.add(record)

    for item in existing:
        if int(item.indicator_id) not in keep_ids:
            session.delete(item)

    session.commit()
    recalculate_stage_snapshots_for_stage(
        session,
        stage_id=payload.stage_id,
        user_ids=[payload.user_id],
        persist=True,
    )
    return {"ok": True, "count": len(keep_ids)}


@router.get("/questionnaire-input")
def get_questionnaire_indicator_input(
    course_id: int,
    user_id: int | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher, UserRole.student)),
):
    course = _get_course_or_404(session, course_id)
    target_user_id = user_id or user.id
    if user.role == UserRole.student and target_user_id != user.id:
        raise HTTPException(status_code=403, detail="No permission for this user")
    if user.role in {UserRole.admin, UserRole.teacher}:
        _ensure_course_permission(session, user, course)

    rows = _course_indicator_rows_for_questionnaire(session=session, course_id=course_id)
    existing = session.exec(
        select(QuestionnairePortraitIndicatorInput).where(
            QuestionnairePortraitIndicatorInput.course_id == course_id,
            QuestionnairePortraitIndicatorInput.user_id == target_user_id,
        )
    ).all()
    existing_map = {int(item.indicator_id): item for item in existing}
    return {
        "items": [
            {
                "dimension_id": int(row["dimension"].id),
                "dimension_title": row["dimension"].title,
                "indicator_id": int(row["indicator"].id),
                "indicator_title": row["indicator"].title,
                "indicator_code": row["indicator"].code,
                "weight": row["weight"],
                "score": float(existing_map[int(row["indicator"].id)].score) if int(row["indicator"].id) in existing_map else None,
                "note": existing_map[int(row["indicator"].id)].note if int(row["indicator"].id) in existing_map else "",
            }
            for row in rows
        ]
    }


@router.put("/questionnaire-input")
def save_questionnaire_indicator_input(
    course_id: int,
    payload: QuestionnairePortraitIndicatorInputIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher, UserRole.student)),
):
    course = _get_course_or_404(session, course_id)
    target_user_id = payload.user_id or user.id
    if user.role == UserRole.student and target_user_id != user.id:
        raise HTTPException(status_code=403, detail="No permission for this user")
    if user.role in {UserRole.admin, UserRole.teacher}:
        _ensure_course_permission(session, user, course)

    valid_rows = _course_indicator_rows_for_questionnaire(session=session, course_id=course_id)
    valid_by_indicator = {int(row["indicator"].id): row for row in valid_rows}
    existing = session.exec(
        select(QuestionnairePortraitIndicatorInput).where(
            QuestionnairePortraitIndicatorInput.course_id == course_id,
            QuestionnairePortraitIndicatorInput.user_id == target_user_id,
        )
    ).all()
    existing_map = {int(item.indicator_id): item for item in existing}
    keep_ids: set[int] = set()

    input_rows = payload.inputs or payload.indicator_scores or []

    for row in input_rows:
        indicator_id = int(row.get("indicator_id") or 0)
        if indicator_id not in valid_by_indicator:
            continue
        score = row.get("score")
        note = str(row.get("note") or "").strip()
        if score in (None, ""):
            continue
        keep_ids.add(indicator_id)
        valid_row = valid_by_indicator[indicator_id]
        record = existing_map.get(indicator_id) or QuestionnairePortraitIndicatorInput(
            user_id=target_user_id,
            course_id=course_id,
            dimension_id=int(valid_row["dimension"].id),
            indicator_id=indicator_id,
        )
        record.dimension_id = int(valid_row["dimension"].id)
        record.score = max(0.0, min(1.0, float(score)))
        record.note = note
        record.updated_at = datetime.utcnow()
        session.add(record)

    for item in existing:
        if int(item.indicator_id) not in keep_ids:
            session.delete(item)

    session.commit()
    stage_rows = session.exec(
        select(CourseStage).where(CourseStage.course_id == course_id).order_by(CourseStage.stage_order.asc())
    ).all()
    normalized_stage_rows: list[CourseStage] = []
    for stage in stage_rows:
        subject, grade = stage_support._normalized_stage_identity(stage, course)
        if stage.subject != subject or stage.grade != grade:
            stage.subject = subject
            stage.grade = grade
            session.add(stage)
        normalized_stage_rows.append(stage)
    session.commit()
    for stage in normalized_stage_rows:
        recalculate_stage_snapshots_for_stage(
            session,
            stage_id=int(stage.id),
            user_ids=[target_user_id],
            persist=True,
        )
    profile_grade = next((str(stage.grade or "").strip() for stage in normalized_stage_rows if str(stage.grade or "").strip()), "通用")
    recalculate_profile_snapshot(
        session,
        user_id=target_user_id,
        subject=course.title,
        grade=profile_grade,
        persist=True,
    )
    return {"ok": True, "count": len(keep_ids)}
