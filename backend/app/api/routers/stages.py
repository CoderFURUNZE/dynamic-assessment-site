import csv
import json
import logging
from datetime import datetime
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlmodel import Session, select

from app.api.deps import require_role
from app.db.models import (
    AuditLog,
    Course,
    CourseStage,
    KnowledgePoint,
    StageImportBatch,
    StageImportRecord,
    StageMetricType,
    User,
    UserRole,
)
from app.db.session import get_session
from app.schemas.stage import (
    CourseStageIn,
    CourseStageOut,
    CourseStageUpdateIn,
    StageImportBatchOut,
    StageImportResultOut,
)
from app.services.learner_profile import recalculate_stage_snapshots_for_stage

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover - dependency guard
    load_workbook = None


router = APIRouter(prefix="/stages", tags=["stages"])
logger = logging.getLogger("app.audit")


def _log_action(session: Session, user: User, action: str, detail: str = "") -> None:
    try:
        logger.info("actor=%s role=%s action=%s detail=%s", user.username, user.role.value, action, detail)
        session.add(AuditLog(actor=user.username, role=user.role.value, action=action, detail=detail))
        session.commit()
    except Exception:
        logger.info("action=%s detail=%s", action, detail)


def _parse_dt(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"invalid datetime: {raw}") from exc


def _course_out(stage: CourseStage) -> CourseStageOut:
    return CourseStageOut(
        id=int(stage.id),
        course_id=stage.course_id,
        subject=stage.subject,
        grade=stage.grade,
        title=stage.title,
        stage_order=stage.stage_order,
        starts_at=stage.starts_at.isoformat() if stage.starts_at else None,
        ends_at=stage.ends_at.isoformat() if stage.ends_at else None,
        description=stage.description,
        created_at=stage.created_at.isoformat(),
    )


def _metric_type_value(value: StageMetricType | str) -> str:
    return value.value if isinstance(value, StageMetricType) else str(value)


def _get_course_or_403(session: Session, user: User, course_id: int) -> Course:
    course = session.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if user.role == UserRole.teacher and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="No permission for this course")
    return course


def _get_stage_or_403(session: Session, user: User, stage_id: int) -> CourseStage:
    stage = session.get(CourseStage, stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="Stage not found")
    _get_course_or_403(session, user, stage.course_id)
    return stage


def _find_user(session: Session, row: dict[str, str]) -> User:
    username = (row.get("username") or "").strip()
    student_no = (row.get("student_no") or "").strip()
    user = None
    if username:
        user = session.exec(select(User).where(User.username == username)).first()
    elif student_no:
        user = session.exec(select(User).where(User.student_no == student_no)).first()
    if user is None:
        raise ValueError("student not found by username/student_no")
    return user


def _find_kp(session: Session, *, subject: str, grade: str, row: dict[str, str]) -> KnowledgePoint | None:
    kp_id = (row.get("kp_id") or "").strip()
    kp_code = (row.get("kp_code") or "").strip()
    if kp_id:
        kp = session.get(KnowledgePoint, int(kp_id))
        if kp is None:
            raise ValueError(f"kp_id not found: {kp_id}")
        return kp
    if kp_code:
        kp = session.exec(
            select(KnowledgePoint).where(
                KnowledgePoint.code == kp_code,
                KnowledgePoint.subject == subject,
                KnowledgePoint.grade == grade,
            )
        ).first()
        if kp is None:
            raise ValueError(f"kp_code not found: {kp_code}")
        return kp
    return None


def _to_float(value: str | None, *, default: float = 0.0) -> float:
    raw = (value or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid numeric value: {raw}") from exc


def _to_ratio(value: str | None) -> float:
    raw = (value or "").strip()
    if not raw:
        return 0.0
    try:
        ratio = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid ratio value: {raw}") from exc
    if ratio > 1.0 and ratio <= 100.0:
        ratio = ratio / 100.0
    return max(0.0, min(1.0, ratio))


def _to_bool(value: str | None) -> bool:
    raw = (value or "").strip().lower()
    return raw in {"1", "true", "yes", "y", "是", "已提交", "on_time"}


def _rows_from_upload(file: UploadFile, payload: bytes) -> list[dict[str, str]]:
    name = (file.filename or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        return [{str(k).strip(): "" if v is None else str(v).strip() for k, v in row.items()} for row in reader]
    if name.endswith(".xlsx"):
        if load_workbook is None:
            raise HTTPException(status_code=400, detail="xlsx import requires openpyxl")
        wb = load_workbook(BytesIO(payload), data_only=True)
        ws = wb.active
        values = list(ws.iter_rows(values_only=True))
        if not values:
            return []
        headers = [str(item).strip() if item is not None else "" for item in values[0]]
        rows: list[dict[str, str]] = []
        for value_row in values[1:]:
            item: dict[str, str] = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                cell = value_row[idx] if idx < len(value_row) else ""
                item[header] = "" if cell is None else str(cell).strip()
            rows.append(item)
        return rows
    raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")


def _template_csv(metric_type: StageMetricType) -> str:
    rows = {
        StageMetricType.video: [
            "username,student_no,kp_code,watched_minutes,completion_ratio,happened_at,note",
            "student1,2026001,CN-GEN-001,45,0.8,2026-03-10,视频学习样例",
        ],
        StageMetricType.assignment: [
            "username,student_no,kp_code,score,completion_ratio,submitted_on_time,happened_at,note",
            "student1,2026001,CN-GEN-001,88,1,yes,2026-03-10,作业完成样例",
        ],
        StageMetricType.quiz: [
            "username,student_no,kp_code,score,completion_ratio,duration_minutes,happened_at,note",
            "student1,2026001,CN-GEN-001,76,0.76,18,2026-03-10,小测样例",
        ],
        StageMetricType.attendance: [
            "username,student_no,attendance_value,status,happened_at,note",
            "student1,2026001,1,present,2026-03-10,考勤样例",
        ],
        StageMetricType.task: [
            "username,student_no,kp_code,score,completion_ratio,status,happened_at,note",
            "student1,2026001,CN-GEN-001,90,1,done,2026-03-10,任务完成样例",
        ],
        StageMetricType.participation: [
            "username,student_no,kp_code,score,completion_ratio,status,happened_at,note",
            "student1,2026001,CN-GEN-001,1,1,active,2026-03-10,课堂参与样例",
        ],
    }
    return "\n".join(rows[metric_type])


@router.get("/courses/{course_id}", response_model=list[CourseStageOut])
def list_stages(
    course_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    _get_course_or_403(session, user, course_id)
    rows = session.exec(
        select(CourseStage).where(CourseStage.course_id == course_id).order_by(CourseStage.stage_order, CourseStage.id)
    ).all()
    return [_course_out(row) for row in rows]


@router.post("/courses/{course_id}", response_model=CourseStageOut)
def create_stage(
    course_id: int,
    payload: CourseStageIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_403(session, user, course_id)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    exists = session.exec(
        select(CourseStage).where(CourseStage.course_id == course_id, CourseStage.stage_order == payload.stage_order)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=400, detail="stage_order already exists in this course")
    try:
        starts_at = _parse_dt(payload.starts_at)
        ends_at = _parse_dt(payload.ends_at)
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
    _log_action(session, user, "course_stage_create", f"course_id={course_id} stage_id={stage.id}")
    return _course_out(stage)


@router.put("/{stage_id}", response_model=CourseStageOut)
def update_stage(
    stage_id: int,
    payload: CourseStageUpdateIn,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    stage = _get_stage_or_403(session, user, stage_id)
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
            stage.starts_at = _parse_dt(payload.starts_at)
        if payload.ends_at is not None:
            stage.ends_at = _parse_dt(payload.ends_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.description is not None:
        stage.description = payload.description.strip()
    session.add(stage)
    session.commit()
    session.refresh(stage)
    _log_action(session, user, "course_stage_update", f"stage_id={stage_id}")
    return _course_out(stage)


@router.delete("/{stage_id}")
def delete_stage(
    stage_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    stage = _get_stage_or_403(session, user, stage_id)
    has_batch = session.exec(select(StageImportBatch).where(StageImportBatch.stage_id == stage_id)).first()
    if has_batch is not None:
        raise HTTPException(status_code=400, detail="Stage already has imported data and cannot be deleted")
    session.delete(stage)
    session.commit()
    _log_action(session, user, "course_stage_delete", f"stage_id={stage_id}")
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
        content=_template_csv(metric),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="stage_template_{metric.value}.csv"'},
    )


@router.get("/imports", response_model=list[StageImportBatchOut])
def list_import_batches(
    course_id: int,
    stage_id: int | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    _get_course_or_403(session, user, course_id)
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
            metric_type=_metric_type_value(row.metric_type),
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


@router.post("/imports/upload", response_model=StageImportResultOut)
def upload_stage_data(
    course_id: int = Form(...),
    stage_id: int = Form(...),
    metric_type: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_role(UserRole.admin, UserRole.teacher)),
):
    course = _get_course_or_403(session, user, course_id)
    stage = _get_stage_or_403(session, user, stage_id)
    if stage.course_id != course_id:
        raise HTTPException(status_code=400, detail="stage does not belong to the course")
    try:
        metric = StageMetricType(metric_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid metric_type") from exc

    payload = file.file.read()
    rows = _rows_from_upload(file, payload)
    batch = StageImportBatch(
        course_id=course_id,
        stage_id=stage_id,
        subject=stage.subject,
        grade=stage.grade,
        metric_type=metric,
        file_name=file.filename or "",
        uploaded_by=user.username,
        total_rows=len(rows),
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)

    errors: list[str] = []
    success = 0
    affected_user_ids: set[int] = set()
    for index, row in enumerate(rows, start=2):
        try:
            student = _find_user(session, row)
            kp = _find_kp(session, subject=stage.subject, grade=stage.grade, row=row)
            score_value = _to_float(row.get("score"), default=0.0)
            completion_value = _to_ratio(row.get("completion_ratio") or row.get("completion_value"))
            duration_minutes = _to_float(row.get("duration_minutes") or row.get("watched_minutes"), default=0.0)
            attendance_value = _to_float(row.get("attendance_value"), default=0.0)
            if metric == StageMetricType.attendance and not row.get("attendance_value"):
                attendance_value = 1.0 if (row.get("status") or "").strip().lower() in {"present", "attended", "on_time"} else 0.0
            happened_at = _parse_dt(row.get("happened_at")) or datetime.utcnow()
            record = StageImportRecord(
                batch_id=int(batch.id),
                course_id=course_id,
                stage_id=stage_id,
                user_id=int(student.id),
                kp_id=int(kp.id) if kp is not None else None,
                subject=stage.subject,
                grade=stage.grade,
                metric_type=metric,
                score_value=score_value,
                completion_value=completion_value,
                duration_minutes=duration_minutes,
                attendance_value=attendance_value,
                submitted_on_time=_to_bool(row.get("submitted_on_time")),
                status=(row.get("status") or "").strip(),
                note=(row.get("note") or "").strip(),
                happened_at=happened_at,
                raw_json=json.dumps(row, ensure_ascii=False),
            )
            session.add(record)
            success += 1
            if student.id is not None:
                affected_user_ids.add(int(student.id))
        except Exception as exc:
            errors.append(f"第 {index} 行：{exc}")

    batch.success_rows = success
    batch.failed_rows = len(rows) - success
    batch.error_json = json.dumps(errors[:20], ensure_ascii=False)
    session.add(batch)
    session.commit()
    if affected_user_ids:
        try:
            recalculate_stage_snapshots_for_stage(
                session,
                stage_id=stage_id,
                user_ids=sorted(affected_user_ids),
                persist=True,
            )
        except Exception as exc:
            logger.exception("stage snapshot recalc failed: stage_id=%s", stage_id)
            errors.append(f"阶段评价重算失败：{exc}")
            batch.error_json = json.dumps(errors[:20], ensure_ascii=False)
            session.add(batch)
            session.commit()
    _log_action(
        session,
        user,
        "stage_data_import",
        f"course_id={course_id} stage_id={stage_id} metric={metric.value} success={success} failed={batch.failed_rows}",
    )
    return StageImportResultOut(
        batch_id=int(batch.id),
        metric_type=metric.value,
        total_rows=len(rows),
        success_rows=success,
        failed_rows=len(rows) - success,
        errors=errors[:20],
    )
