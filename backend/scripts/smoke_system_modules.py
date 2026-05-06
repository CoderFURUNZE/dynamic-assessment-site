from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from app.db.models import Course, CourseStage, KnowledgePoint, User  # noqa: E402
from app.db.session import engine  # noqa: E402
from backend.scripts.seed_midterm_three_student_paths import seed as seed_three_student_paths  # noqa: E402


BASE_URL = "http://127.0.0.1:8000/api"


class SmokeFailure(RuntimeError):
    pass


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected_status: int = 200,
    timeout: int = 25,
    **kwargs: Any,
) -> Any:
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=timeout, **kwargs)
    if response.status_code != expected_status:
        raise SmokeFailure(f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:600]}")
    if not response.content:
        return None
    return response.json()


def login(path: str, username: str, password: str) -> str:
    data = request_json("POST", path, json={"username": username, "password": password})
    token = str(data.get("access_token") or "")
    assert_true(bool(token), f"{username} login missing token")
    return token


def demo_context() -> dict[str, Any]:
    with Session(engine) as session:
        course = session.exec(select(Course).where(Course.code == "HM-MIDTERM")).first()
        assert_true(course is not None and course.id is not None, "HM-MIDTERM course missing")
        kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == "HM-MID-01")).first()
        assert_true(kp is not None and kp.id is not None, "HM-MID-01 missing")
        student = session.exec(select(User).where(User.username == "student_demo_1")).first()
        assert_true(student is not None and student.id is not None, "student_demo_1 missing")
        teacher = session.exec(select(User).where(User.username == "teacher_demo")).first()
        assert_true(teacher is not None and teacher.id is not None, "teacher_demo missing")
        return {
            "course_id": int(course.id),
            "subject": str(course.title),
            "grade": str(kp.grade),
            "kp_id": int(kp.id),
            "student_id": int(student.id),
            "teacher_id": int(teacher.id),
        }


def cleanup_smoke_stages(course_id: int) -> None:
    with Session(engine) as session:
        rows = session.exec(
            select(CourseStage).where(
                CourseStage.course_id == course_id,
                CourseStage.title.startswith("SMOKE-"),
            )
        ).all()
        for row in rows:
            session.delete(row)
        session.commit()


def smoke_auth(admin_token: str, teacher_token: str, student_token: str) -> list[str]:
    admin_me = request_json("GET", "/auth/me", token=admin_token)
    teacher_me = request_json("GET", "/auth/me", token=teacher_token)
    student_me = request_json("GET", "/auth/me", token=student_token)
    assert_true(admin_me.get("role") == "admin", "admin /auth/me role mismatch")
    assert_true(teacher_me.get("role") == "teacher", "teacher /auth/me role mismatch")
    assert_true(student_me.get("role") == "student", "student /auth/me role mismatch")
    return ["auth: admin/teacher/student login and /me"]


def smoke_admin_basic(admin_token: str, ctx: dict[str, Any]) -> list[str]:
    users = request_json("GET", "/admin/users", token=admin_token, params={"page": 1, "page_size": 10})
    courses = request_json("GET", "/admin/courses", token=admin_token)
    config = request_json("GET", "/admin/config", token=admin_token, params={"subject": ctx["subject"], "grade": ctx["grade"]})
    audit = request_json("GET", "/admin/audit", token=admin_token, params={"page": 1, "page_size": 5})
    persona_rules = request_json("GET", "/admin/persona/rules", token=admin_token, params={"subject": ctx["subject"], "grade": ctx["grade"]})
    persona_students = request_json("GET", "/admin/persona/students", token=admin_token, params={"subject": ctx["subject"], "grade": ctx["grade"]})
    final_students = request_json("GET", "/admin/final-score/students", token=admin_token, params={"subject": ctx["subject"], "grade": ctx["grade"]})
    analytics = request_json("GET", "/admin/analytics/overview", token=admin_token, params={"subject": ctx["subject"], "grade": ctx["grade"]})

    assert_true(isinstance(users.get("items"), list), "admin users shape invalid")
    assert_true(isinstance(courses.get("items", []), list), "admin courses shape invalid")
    assert_true("weights" in config or "weights_json" in config or isinstance(config, dict), "admin config shape invalid")
    assert_true(isinstance(audit.get("items"), list), "admin audit shape invalid")
    assert_true(isinstance(persona_rules, dict), "persona rules shape invalid")
    assert_true(isinstance(persona_students.get("items", []), list), "persona students shape invalid")
    assert_true(isinstance(final_students.get("items", []), list), "final-score students shape invalid")
    assert_true(isinstance(analytics, dict), "analytics overview shape invalid")
    return [
        "admin: users/courses/config/audit/persona/final-score/analytics read paths",
    ]


def smoke_teacher_course_and_graph(teacher_token: str, ctx: dict[str, Any]) -> list[str]:
    subject = ctx["subject"]
    grade = ctx["grade"]
    course_id = ctx["course_id"]
    kp_id = ctx["kp_id"]

    courses = request_json("GET", "/graph/courses", token=teacher_token)
    catalog = request_json("GET", "/graph/teacher/course-catalog", token=teacher_token)
    students = request_json("GET", f"/graph/courses/{course_id}/students", token=teacher_token)
    kps = request_json("GET", "/graph/kps", token=teacher_token, params={"subject": subject, "grade": grade})
    edges = request_json("GET", "/graph/edges", token=teacher_token, params={"subject": subject, "grade": grade})
    graph_map = request_json("GET", "/graph/map", token=teacher_token, params={"subject": subject, "grade": grade})
    node = request_json("GET", f"/graph/node/{kp_id}", token=teacher_token)
    path = request_json("GET", f"/graph/path/{kp_id}", token=teacher_token)
    chapter_layout = request_json("GET", "/graph/chapter-layout", token=teacher_token, params={"subject": subject, "grade": grade})

    teacher_kps = request_json("GET", "/admin/kps", token=teacher_token, params={"subject": subject, "grade": grade, "page": 1, "page_size": 5})
    coverage = request_json("GET", "/admin/graph/kp-coverage", token=teacher_token, params={"subject": subject, "grade": grade})
    resources = request_json("GET", "/admin/kp-resources", token=teacher_token, params={"kp_id": kp_id})
    tasks = request_json("GET", "/admin/kp-tasks", token=teacher_token, params={"kp_id": kp_id})
    questions = request_json("GET", "/admin/kp-questions", token=teacher_token, params={"kp_id": kp_id})
    quiz = request_json("GET", "/admin/quiz", token=teacher_token, params={"kp_id": kp_id})

    assert_true(any(item.get("title") == subject for item in courses), "teacher graph courses missing demo course")
    assert_true(isinstance(catalog.get("items", []), list), "teacher catalog shape invalid")
    assert_true(isinstance(students.get("items", []), list), "course students shape invalid")
    assert_true(len(kps) > 0 and len(edges) > 0, "teacher graph kps/edges missing")
    assert_true(len(graph_map.get("base", {}).get("kps", [])) > 0, "teacher graph map missing kps")
    assert_true(node.get("kp", {}).get("id") == kp_id, "graph node detail mismatch")
    assert_true("path_summary" in path, "graph path shape invalid")
    assert_true("chapters" in chapter_layout, "chapter layout shape invalid")
    assert_true(isinstance(teacher_kps.get("items", []), list), "teacher admin kps shape invalid")
    assert_true(isinstance(coverage, dict), "graph coverage shape invalid")
    assert_true(isinstance(resources, list), "kp resources shape invalid")
    assert_true(isinstance(tasks, list), "kp tasks shape invalid")
    assert_true(isinstance(questions, list), "kp questions shape invalid")
    assert_true(isinstance(quiz, dict), "quiz admin shape invalid")
    return ["teacher: course catalog/students/graph/content authoring read paths"]


def smoke_enrollment_and_notifications(student_token: str, teacher_token: str, ctx: dict[str, Any]) -> list[str]:
    course_id = ctx["course_id"]
    enrollable = request_json("GET", "/enrollment/courses/enrollable", token=student_token)
    applications = request_json("GET", "/enrollment/my/applications", token=student_token)
    notifications = request_json("GET", "/enrollment/my/notifications", token=student_token)
    access = request_json("GET", f"/enrollment/courses/{course_id}/access-check", token=student_token)
    teacher_apps = request_json("GET", "/enrollment/teacher/applications", token=teacher_token, params={"course_id": course_id})
    assert_true(isinstance(enrollable.get("items", []), list), "enrollable courses shape invalid")
    assert_true(isinstance(applications.get("items", []), list), "my applications shape invalid")
    assert_true(isinstance(notifications.get("items", []), list), "notifications shape invalid")
    assert_true(access.get("ok") is True, "course access-check failed")
    assert_true(isinstance(teacher_apps.get("items", []), list), "teacher applications shape invalid")
    return ["enrollment: enrollable/applications/notifications/access-check/review read paths"]


def smoke_stages(teacher_token: str, ctx: dict[str, Any]) -> list[str]:
    course_id = ctx["course_id"]
    cleanup_smoke_stages(course_id)
    stages = request_json("GET", f"/stages/courses/{course_id}", token=teacher_token)
    max_order = max([int(item.get("stage_order") or 0) for item in stages] or [0])
    order = max_order + 1000
    created = request_json(
        "POST",
        f"/stages/courses/{course_id}",
        token=teacher_token,
        json={
            "grade": ctx["grade"],
            "title": "SMOKE-阶段连通性测试",
            "stage_order": order,
            "description": "temporary smoke stage; safe to delete",
        },
    )
    stage_id = int(created["id"])
    updated = request_json(
        "PUT",
        f"/stages/{stage_id}",
        token=teacher_token,
        json={"title": "SMOKE-阶段连通性测试-已更新", "description": "updated by smoke"},
    )
    assert_true(updated.get("title", "").endswith("已更新"), "stage update did not persist")

    guides = request_json("GET", "/stages/metric-guides", token=teacher_token)
    imports = request_json("GET", "/stages/imports", token=teacher_token, params={"course_id": course_id})
    internal_summary = request_json(
        "GET",
        "/stages/internal-summary",
        token=teacher_token,
        params={"course_id": course_id, "stage_id": stage_id},
    )
    behavior_summary = request_json(
        "GET",
        "/stages/internal-behavior-summary",
        token=teacher_token,
        params={"course_id": course_id, "stage_id": stage_id},
    )
    request_json("DELETE", f"/stages/{stage_id}", token=teacher_token)
    cleanup_smoke_stages(course_id)

    assert_true(isinstance(guides, list) and len(guides) > 0, "stage metric guides missing")
    assert_true(isinstance(imports, list), "stage imports shape invalid")
    assert_true(isinstance(internal_summary, dict), "stage internal summary shape invalid")
    assert_true(isinstance(behavior_summary, dict), "stage behavior summary shape invalid")
    return ["stages: list/create/update/delete/guides/import-summary"]


def smoke_portrait_eval_report(admin_token: str, teacher_token: str, student_token: str, ctx: dict[str, Any]) -> list[str]:
    subject = ctx["subject"]
    grade = ctx["grade"]
    course_id = ctx["course_id"]
    kp_id = ctx["kp_id"]
    student_id = ctx["student_id"]

    stages = request_json("GET", f"/stages/courses/{course_id}", token=teacher_token)
    max_order = max([int(item.get("stage_order") or 0) for item in stages] or [0])
    temp_stage = request_json(
        "POST",
        f"/stages/courses/{course_id}",
        token=teacher_token,
        json={
            "grade": grade,
            "title": "SMOKE-画像输入连通性测试",
            "stage_order": max_order + 1001,
            "description": "temporary smoke stage; safe to delete",
        },
    )
    temp_stage_id = int(temp_stage["id"])

    dimensions = request_json("GET", "/portrait/dimensions/tree", token=admin_token)
    selection = request_json("GET", "/portrait/course-selection", token=teacher_token, params={"course_id": course_id})
    teacher_input = request_json(
        "GET",
        "/portrait/teacher-input",
        token=teacher_token,
        params={"course_id": course_id, "user_id": student_id, "stage_id": temp_stage_id},
    )
    questionnaire_input = request_json(
        "GET",
        "/portrait/questionnaire-input",
        token=student_token,
        params={"course_id": course_id},
    )
    mastery = request_json("GET", "/eval/mastery", token=student_token, params={"kp_id": kp_id})
    profile = request_json("GET", "/eval/profile", token=student_token, params={"subject": subject, "grade": grade})
    overview = request_json("GET", "/eval/overview", token=student_token, params={"subject": subject, "grade": grade})
    detail = request_json(
        "GET",
        "/admin/analytics/student-detail",
        token=teacher_token,
        params={"subject": subject, "grade": grade, "user_id": student_id},
    )
    final_detail = request_json(
        "GET",
        "/admin/final-score/detail",
        token=teacher_token,
        params={"subject": subject, "grade": grade, "user_id": student_id},
    )
    request_json("DELETE", f"/stages/{temp_stage_id}", token=teacher_token)
    cleanup_smoke_stages(course_id)

    assert_true(isinstance(dimensions.get("items", []), list), "portrait dimensions shape invalid")
    assert_true(isinstance(selection.get("items", []), list), "portrait course-selection shape invalid")
    assert_true(isinstance(teacher_input, dict), "teacher portrait input shape invalid")
    assert_true(isinstance(questionnaire_input, dict), "questionnaire input shape invalid")
    assert_true(int(mastery.get("kp_id")) == kp_id, "eval mastery kp mismatch")
    assert_true(isinstance(profile, dict) and "dynamic_score" in profile, "eval profile shape invalid")
    assert_true(isinstance(overview, dict), "eval overview shape invalid")
    assert_true(isinstance(detail.get("mastery_map", []), list), "teacher student detail shape invalid")
    assert_true(isinstance(final_detail, dict), "final score detail shape invalid")
    return ["portrait/eval/report: dimensions, inputs, profile, overview, detail, final score"]


def smoke_notes_extensions(student_token: str, ctx: dict[str, Any]) -> list[str]:
    kp_id = ctx["kp_id"]
    notes = request_json("GET", "/notes/", token=student_token, params={"kp_id": kp_id})
    ext = request_json("GET", "/extensions/overview", token=student_token)
    methodology = request_json("GET", "/extensions/methodology", token=student_token)
    assert_true(isinstance(notes, list), "notes list shape invalid")
    assert_true(isinstance(ext.get("features", []), list), "extensions overview shape invalid")
    assert_true(isinstance(methodology.get("method_cards", []), list), "methodology shape invalid")
    return ["notes/extensions: note list and extension docs"]


def run_smoke() -> list[str]:
    seed_three_student_paths()
    ctx = demo_context()
    admin_token = login("/auth/login/admin", "admin", "admin123")
    teacher_token = login("/auth/login/admin", "teacher_demo", "123456")
    student_token = login("/auth/login", "student_demo_1", "123456")

    results: list[str] = []
    results += smoke_auth(admin_token, teacher_token, student_token)
    results += smoke_admin_basic(admin_token, ctx)
    results += smoke_teacher_course_and_graph(teacher_token, ctx)
    results += smoke_enrollment_and_notifications(student_token, teacher_token, ctx)
    results += smoke_stages(teacher_token, ctx)
    results += smoke_portrait_eval_report(admin_token, teacher_token, student_token, ctx)
    results += smoke_notes_extensions(student_token, ctx)
    seed_three_student_paths()
    return results


def main() -> int:
    try:
        requests.get("http://127.0.0.1:8000/health", timeout=5).raise_for_status()
    except Exception as exc:
        print(f"[FAIL] backend is not reachable: {exc}")
        return 2
    try:
        results = run_smoke()
    except Exception as exc:
        print(f"[FAIL] system module smoke failed: {exc}")
        return 1
    print("\nSystem module smoke packet passed")
    for item in results:
        print(f"[PASS] {item}")
    print(
        "\nCovered modules: auth, admin basics, teacher course workspace, graph/content authoring, "
        "enrollment/review/notifications, stages, portrait dimensions and inputs, eval/profile/report, "
        "notes, extension information pages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
