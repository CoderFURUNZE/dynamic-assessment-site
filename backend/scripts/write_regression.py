#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def add(results: list[CheckResult], name: str, ok: bool, detail: str) -> None:
    results.append(CheckResult(name=name, ok=ok, detail=detail))


def request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    expected: set[int] | None = None,
    timeout: float = 20.0,
) -> tuple[int, Any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        response = client.request(method, path, params=params, json=payload, headers=headers)
    try:
        data = response.json()
    except Exception:
        data = response.text
    if expected is not None and response.status_code not in expected:
        raise RuntimeError(
            f"{method} {path} -> {response.status_code}, expected={sorted(expected)}, body={data}"
        )
    return response.status_code, data


def login(base_url: str, username: str, password: str) -> tuple[str, str]:
    _, data = request_json(
        base_url=base_url,
        method="POST",
        path="/api/auth/login",
        payload={"username": username, "password": password},
        expected={200},
    )
    return str(data["access_token"]), str(data["role"])


def write_report(results: list[CheckResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for item in results if item.ok)
    lines = [
        "# Backend Write Regression",
        "",
        f"- Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Total: {len(results)}",
        f"- Passed: {passed}",
        f"- Failed: {len(results) - passed}",
        "",
        "## Details",
        "",
    ]
    for idx, item in enumerate(results, start=1):
        lines.append(f"{idx}. [{'PASS' if item.ok else 'FAIL'}] {item.name}")
        lines.append(f"   - {item.detail}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mutation-heavy backend regression.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-user", default="admin")
    parser.add_argument("--admin-pass", default="admin123")
    parser.add_argument("--teacher-user", default="teacher1")
    parser.add_argument("--teacher-pass", default="teacher123")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output = Path(args.output) if args.output else Path("logs") / f"backend_write_regression_{timestamp}.md"
    results: list[CheckResult] = []

    try:
        admin_token, _ = login(args.base_url, args.admin_user, args.admin_pass)
        teacher_token, _ = login(args.base_url, args.teacher_user, args.teacher_pass)
        add(results, "base logins", True, f"admin={args.admin_user}, teacher={args.teacher_user}")

        _, teacher_me = request_json(
            base_url=args.base_url,
            method="GET",
            path="/api/auth/me",
            token=teacher_token,
            expected={200},
        )
        teacher_id = int(teacher_me["id"])

        _, kp_page = request_json(
            base_url=args.base_url,
            method="GET",
            path="/api/admin/kps",
            token=teacher_token,
            params={"page": 1, "page_size": 1},
            expected={200},
        )
        first_kp = (kp_page.get("items") or [None])[0]
        if not first_kp:
            raise RuntimeError("no knowledge point available for write regression")
        subject = str(first_kp["subject"]).strip()
        grade = str(first_kp["grade"]).strip()
        add(results, "discover subject", True, f"subject={subject}, grade={grade}, kp_id={first_kp.get('id')}")

        suffix = timestamp[-6:]
        username = f"e2e_student_{suffix}"
        password = "Temp1234"

        _, create_user = request_json(
            base_url=args.base_url,
            method="POST",
            path="/api/admin/users",
            token=admin_token,
            payload={
                "username": username,
                "password": password,
                "role": "student",
                "full_name": "E2E Student",
                "student_no": f"2026{suffix}",
                "class_name": "E2E-CLASS",
                "active": True,
            },
            expected={200},
        )
        add(results, "create temp student", True, f"user_id={create_user['user_id']}, username={username}")

        import_student_username = f"e2e_import_student_{suffix}"
        import_teacher_username = f"e2e_import_teacher_{suffix}"
        _, create_import_course = request_json(
            base_url=args.base_url,
            method="POST",
            path="/api/admin/courses",
            token=admin_token,
            payload={
                "code": f"E2EI{suffix}",
                "title": f"{subject}-IMPORT",
                "description": "E2E import class matching course",
                "active": True,
                "lifecycle_status": "active",
                "teacher_id": teacher_id,
                "target_class": "E2E-IMPORT",
                "max_students": 10,
                "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "end_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "apply_deadline": (datetime.utcnow() + timedelta(days=10)).isoformat(),
                "enroll_status": "open",
            },
            expected={200},
        )
        import_course_id = int(create_import_course["id"])
        add(results, "create import-matching course", True, f"course_id={import_course_id}")

        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            student_preview = client.post(
                "/api/admin/users/import/preview",
                data={"role": "student"},
                files={
                    "file": (
                        "students.csv",
                        (
                            "username,password,full_name,student_no,class_name,phone,active\n"
                            f"{import_student_username},Temp1234,Import Student,2027{suffix},E2E-IMPORT,1390000{suffix},true\n"
                        ).encode("utf-8"),
                        "text/csv",
                    )
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        if student_preview.status_code != 200:
            raise RuntimeError(f"POST /api/admin/users/import/preview -> {student_preview.status_code}, body={student_preview.text}")
        student_preview_data = student_preview.json()
        add(
            results,
            "admin import preview",
            bool(student_preview_data.get("valid_rows") == 1 and student_preview_data.get("invalid_rows") == 0),
            json.dumps(student_preview_data, ensure_ascii=False),
        )

        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            student_import = client.post(
                "/api/admin/users/import",
                data={"role": "student"},
                files={
                    "file": (
                        "students.csv",
                        (
                            "username,password,full_name,student_no,class_name,phone,active\n"
                            f"{import_student_username},Temp1234,Import Student,2027{suffix},E2E-IMPORT,1390000{suffix},true\n"
                        ).encode("utf-8"),
                        "text/csv",
                    )
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        if student_import.status_code != 200:
            raise RuntimeError(f"POST /api/admin/users/import(student) -> {student_import.status_code}, body={student_import.text}")
        student_import_data = student_import.json()
        add(
            results,
            "admin import student",
            bool(
                student_import_data.get("success_rows") == 1
                and student_import_data.get("created_rows") == 1
                and int(student_import_data.get("auto_enrolled_rows") or 0) >= 1
            ),
            json.dumps(student_import_data, ensure_ascii=False),
        )

        import_student_token, _ = login(args.base_url, import_student_username, "Temp1234")
        _, import_access = request_json(
            base_url=args.base_url,
            method="GET",
            path=f"/api/enrollment/courses/{import_course_id}/access-check",
            token=import_student_token,
            expected={200},
        )
        add(results, "imported student auto enroll", bool(import_access.get("ok") is True), json.dumps(import_access))

        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            teacher_import = client.post(
                "/api/admin/users/import",
                data={"role": "teacher"},
                files={
                    "file": (
                        "teachers.csv",
                        (
                            "username,password,full_name,student_no,class_name,phone,active\n"
                            f"{import_teacher_username},Temp1234,Import Teacher,T{suffix},教研组E2E,1370000{suffix},true\n"
                        ).encode("utf-8"),
                        "text/csv",
                    )
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        if teacher_import.status_code != 200:
            raise RuntimeError(f"POST /api/admin/users/import(teacher) -> {teacher_import.status_code}, body={teacher_import.text}")
        teacher_import_data = teacher_import.json()
        add(
            results,
            "admin import teacher",
            bool(teacher_import_data.get("success_rows") == 1 and teacher_import_data.get("created_rows") == 1),
            json.dumps(teacher_import_data, ensure_ascii=False),
        )

        _, create_course = request_json(
            base_url=args.base_url,
            method="POST",
            path="/api/admin/courses",
            token=admin_token,
            payload={
                "code": f"E2E{suffix}",
                "title": subject,
                "description": "E2E knowledge-linked course",
                "active": True,
                "lifecycle_status": "active",
                "teacher_id": teacher_id,
                "target_class": "",
                "max_students": 10,
                "start_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "end_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "apply_deadline": (datetime.utcnow() + timedelta(days=10)).isoformat(),
                "enroll_status": "open",
            },
            expected={200},
        )
        course_id = int(create_course["id"])
        add(results, "create temp course", True, f"course_id={course_id}, title={subject}")

        _, create_stage = request_json(
            base_url=args.base_url,
            method="POST",
            path=f"/api/stages/courses/{course_id}",
            token=teacher_token,
            payload={
                "grade": grade,
                "title": "E2E Stage",
                "stage_order": 1,
                "starts_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "ends_at": datetime.utcnow().isoformat(),
                "description": "Regression stage for one-click import",
            },
            expected={200},
        )
        stage_id = int(create_stage["id"])
        add(results, "create temp stage", True, f"stage_id={stage_id}, course_id={course_id}")

        student_token, _ = login(args.base_url, username, password)
        add(results, "temp student login", True, username)

        _, apply_data = request_json(
            base_url=args.base_url,
            method="POST",
            path=f"/api/enrollment/courses/{course_id}/apply",
            token=student_token,
            payload={"apply_reason": "E2E regression apply"},
            expected={200},
        )
        application_id = int(apply_data["application_id"])
        add(results, "student apply", True, f"application_id={application_id}")

        request_json(
            base_url=args.base_url,
            method="POST",
            path=f"/api/enrollment/teacher/applications/{application_id}/approve",
            token=teacher_token,
            payload={"review_remark": "E2E approved"},
            expected={200},
        )
        add(results, "teacher approve", True, f"application_id={application_id}")

        _, access_data = request_json(
            base_url=args.base_url,
            method="GET",
            path=f"/api/enrollment/courses/{course_id}/access-check",
            token=student_token,
            expected={200},
        )
        add(results, "student access check", bool(access_data.get("ok") is True), json.dumps(access_data))

        with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
            response = client.post(
                "/api/stages/one-click-import",
                data={
                    "course_id": str(course_id),
                    "stage_id": str(stage_id),
                    "include_video": "true",
                    "include_practice": "true",
                    "include_mastery": "true",
                    "include_behavior": "true",
                },
                headers={"Authorization": f"Bearer {teacher_token}"},
            )
        if response.status_code != 200:
            raise RuntimeError(f"POST /api/stages/one-click-import -> {response.status_code}, body={response.text}")
        one_click_data = response.json()
        add(
            results,
            "one-click import",
            bool(one_click_data.get("metric_type") == "one_click_auto"),
            f"success_rows={one_click_data.get('success_rows')}, recalculated_users={one_click_data.get('recalculated_users')}",
        )

        _, graph_map = request_json(
            base_url=args.base_url,
            method="GET",
            path="/api/graph/map",
            token=student_token,
            params={"subject": subject, "grade": grade},
            expected={200},
        )
        kps = ((graph_map.get("base") or {}).get("kps") or []) if isinstance(graph_map, dict) else []
        add(results, "graph map", bool(kps), f"kp_count={len(kps)}")

        practice_done = False
        for kp in kps:
            kp_id = int(kp["id"])
            _, next_data = request_json(
                base_url=args.base_url,
                method="GET",
                path="/api/practice/next",
                token=student_token,
                params={"kp_id": kp_id},
                expected={200},
            )
            question = next_data.get("question") if isinstance(next_data, dict) else None
            if not question:
                continue
            request_json(
                base_url=args.base_url,
                method="POST",
                path="/api/practice/submit",
                token=student_token,
                payload={
                    "question_id": int(question["id"]),
                    "kp_id": kp_id,
                    "answer": str((question.get("options") or ["A"])[0]),
                    "self_report": "sure",
                    "duration_ms": 3210,
                },
                expected={200},
            )
            add(results, "practice submit", True, f"kp_id={kp_id}")
            practice_done = True
            break
        if not practice_done:
            add(results, "practice submit", True, "skipped: no available question")

        resource_done = False
        for kp in kps:
            kp_id = int(kp["id"])
            _, resources = request_json(
                base_url=args.base_url,
                method="GET",
                path="/api/content/resources",
                token=student_token,
                params={"kp_id": kp_id},
                expected={200},
            )
            if not isinstance(resources, list) or not resources:
                continue
            request_json(
                base_url=args.base_url,
                method="POST",
                path="/api/content/resource/visit",
                token=student_token,
                payload={
                    "kp_id": kp_id,
                    "resource_id": int(resources[0]["id"]),
                    "action": "visit",
                },
                expected={200},
            )
            add(results, "resource visit", True, f"kp_id={kp_id}, resource_id={resources[0]['id']}")
            resource_done = True
            break
        if not resource_done:
            add(results, "resource visit", True, "skipped: no resource")

        _, config_before = request_json(
            base_url=args.base_url,
            method="GET",
            path="/api/admin/config",
            token=teacher_token,
            params={"subject": subject, "grade": grade},
            expected={200},
        )
        payload = {
            "weights": dict(config_before.get("weights") or {}),
            "thresholds": dict(config_before.get("thresholds") or {}),
            "window": dict(config_before.get("window") or {}),
            "persona": dict(config_before.get("persona") or {}),
        }
        payload["window"]["e2e_last_write"] = timestamp
        request_json(
            base_url=args.base_url,
            method="PUT",
            path="/api/admin/config",
            token=teacher_token,
            params={"subject": subject, "grade": grade},
            payload=payload,
            expected={200},
        )
        _, config_after = request_json(
            base_url=args.base_url,
            method="GET",
            path="/api/admin/config",
            token=teacher_token,
            params={"subject": subject, "grade": grade},
            expected={200},
        )
        config_ok = (config_after.get("window") or {}).get("e2e_last_write") == timestamp
        add(results, "config write-read", config_ok, f"window.e2e_last_write={(config_after.get('window') or {}).get('e2e_last_write')}")
    except Exception as exc:
        add(results, "execution", False, str(exc))

    write_report(results, output)
    passed = sum(1 for item in results if item.ok)
    print(f"[DONE] backend write regression: {passed}/{len(results)} passed")
    print(f"[REPORT] {output}")
    return 0 if passed == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
