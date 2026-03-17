#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _request_json(
    *,
    method: str,
    base_url: str,
    path: str,
    token: str | None = None,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 10,
) -> tuple[int, Any]:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{base_url.rstrip('/')}{path}{query}"
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url=url, method=method.upper(), headers=headers, data=body)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(raw) if raw else {"detail": exc.reason}
        except json.JSONDecodeError:
            parsed = {"detail": raw or str(exc.reason)}
        return exc.code, parsed
    except URLError as exc:
        raise RuntimeError(f"network error: {exc}") from exc


def _login(base_url: str, username: str, password: str) -> tuple[str, str]:
    code, data = _request_json(
        method="POST",
        base_url=base_url,
        path="/api/auth/login",
        payload={"username": username, "password": password},
    )
    if code != 200:
        detail = data.get("detail") if isinstance(data, dict) else data
        raise RuntimeError(f"login failed for {username}: {code} {detail}")
    if not isinstance(data, dict) or not data.get("access_token"):
        raise RuntimeError(f"login response missing access_token for {username}")
    return data["access_token"], str(data.get("role", "unknown"))


def _add(results: list[CheckResult], name: str, ok: bool, detail: str) -> None:
    results.append(CheckResult(name=name, ok=ok, detail=detail))


def _expect_status(
    results: list[CheckResult],
    *,
    name: str,
    code: int,
    expected: tuple[int, ...] = (200,),
    detail: str = "",
) -> bool:
    ok = code in expected
    _add(
        results,
        name=name,
        ok=ok,
        detail=detail if detail else (f"status={code}, expected={expected}"),
    )
    return ok


def _write_report(results: list[CheckResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for item in results if item.ok)
    total = len(results)
    lines = [
        "# 验收冒烟测试报告",
        "",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 总数: {total}",
        f"- 通过: {passed}",
        f"- 失败: {total - passed}",
        "",
        "## 结果明细",
        "",
    ]
    for idx, item in enumerate(results, start=1):
        mark = "PASS" if item.ok else "FAIL"
        lines.append(f"{idx}. [{mark}] {item.name}")
        lines.append(f"   - {item.detail}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="动态评价系统三端主链路冒烟验收脚本")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端地址")
    parser.add_argument("--admin-user", default="admin", help="管理员账号")
    parser.add_argument("--admin-pass", default="admin123", help="管理员密码")
    parser.add_argument("--teacher-user", default="teacher1", help="教师账号")
    parser.add_argument("--teacher-pass", default="teacher123", help="教师密码")
    parser.add_argument("--student-user", default="student1", help="学生账号")
    parser.add_argument("--student-pass", default="student123", help="学生密码")
    parser.add_argument("--timeout", type=int, default=10, help="单请求超时秒数")
    parser.add_argument("--output", default="", help="输出报告路径（md）")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output = (
        Path(args.output)
        if args.output
        else Path("logs") / f"smoke_acceptance_{timestamp}.md"
    )

    results: list[CheckResult] = []

    try:
        code, data = _request_json(
            method="GET",
            base_url=args.base_url,
            path="/health",
            timeout=args.timeout,
        )
        _expect_status(results, name="健康检查 /health", code=code)
        _add(results, name="健康返回值校验", ok=bool(isinstance(data, dict) and data.get("ok") is True), detail=f"payload={data}")
    except Exception as exc:
        _add(results, name="健康检查 /health", ok=False, detail=str(exc))
        _write_report(results, output)
        print(f"[FAIL] health check failed, report -> {output}")
        return 1

    try:
        admin_token, admin_role = _login(args.base_url, args.admin_user, args.admin_pass)
        _add(results, name="管理员登录", ok=True, detail=f"role={admin_role}")
    except Exception as exc:
        _add(results, name="管理员登录", ok=False, detail=str(exc))
        _write_report(results, output)
        print(f"[FAIL] admin login failed, report -> {output}")
        return 1

    try:
        teacher_token, teacher_role = _login(args.base_url, args.teacher_user, args.teacher_pass)
        _add(results, name="教师登录", ok=True, detail=f"role={teacher_role}")
    except Exception as exc:
        _add(results, name="教师登录", ok=False, detail=str(exc))
        _write_report(results, output)
        print(f"[FAIL] teacher login failed, report -> {output}")
        return 1

    try:
        student_token, student_role = _login(args.base_url, args.student_user, args.student_pass)
        _add(results, name="学生登录", ok=True, detail=f"role={student_role}")
    except Exception as exc:
        _add(results, name="学生登录", ok=False, detail=str(exc))
        _write_report(results, output)
        print(f"[FAIL] student login failed, report -> {output}")
        return 1

    for role_name, token in [
        ("admin", admin_token),
        ("teacher", teacher_token),
        ("student", student_token),
    ]:
        code, data = _request_json(
            method="GET",
            base_url=args.base_url,
            path="/api/auth/me",
            token=token,
            timeout=args.timeout,
        )
        _expect_status(results, name=f"{role_name} 获取 /api/auth/me", code=code)
        _add(
            results,
            name=f"{role_name} /api/auth/me 结构",
            ok=bool(isinstance(data, dict) and data.get("username")),
            detail=f"payload={data}",
        )

    code, admin_courses = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/admin/courses",
        token=teacher_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="教师课程管理列表 /api/admin/courses", code=code)

    code, _ = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/admin/users",
        token=admin_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="管理员用户列表 /api/admin/users", code=code)

    code, _ = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/admin/analytics/overview",
        token=admin_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="管理员分析总览 /api/admin/analytics/overview", code=code)

    code, teacher_courses = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/graph/courses",
        token=teacher_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="教师课程列表 /api/graph/courses", code=code)

    code, _ = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/portrait/dimensions/tree",
        token=teacher_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="教师维度树 /api/portrait/dimensions/tree", code=code)

    teacher_course_id = None
    if isinstance(teacher_courses, list) and teacher_courses:
        teacher_course_id = teacher_courses[0].get("id")
    if teacher_course_id:
        code, _ = _request_json(
            method="GET",
            base_url=args.base_url,
            path=f"/api/stages/courses/{teacher_course_id}",
            token=teacher_token,
            timeout=args.timeout,
        )
        _expect_status(results, name="教师阶段列表 /api/stages/courses/{course_id}", code=code)
        code, _ = _request_json(
            method="GET",
            base_url=args.base_url,
            path="/api/portrait/course-selection",
            token=teacher_token,
            params={"course_id": teacher_course_id},
            timeout=args.timeout,
        )
        _expect_status(results, name="教师课程画像指标 /api/portrait/course-selection", code=code)
    else:
        _add(
            results,
            name="教师阶段与课程画像检查",
            ok=True,
            detail="已跳过：教师账号无课程数据",
        )

    code, student_courses = _request_json(
        method="GET",
        base_url=args.base_url,
        path="/api/graph/courses",
        token=student_token,
        timeout=args.timeout,
    )
    _expect_status(results, name="学生课程列表 /api/graph/courses", code=code)

    subject = ""
    grade = ""
    if isinstance(admin_courses, list) and admin_courses:
        subject = str(admin_courses[0].get("title", "")).strip()
        grade = str(admin_courses[0].get("grade", "通用")).strip() or "通用"

    if subject:
        code, data = _request_json(
            method="GET",
            base_url=args.base_url,
            path="/api/graph/map",
            token=student_token,
            params={"subject": subject, "grade": grade},
            timeout=args.timeout,
        )
        _expect_status(results, name="学生图谱地图 /api/graph/map", code=code)
        kp_id = None
        if isinstance(data, dict):
            base = data.get("base", {})
            kps = base.get("kps", []) if isinstance(base, dict) else []
            if isinstance(kps, list) and kps:
                kp_id = kps[0].get("id")
        if kp_id:
            code, _ = _request_json(
                method="GET",
                base_url=args.base_url,
                path=f"/api/graph/node/{kp_id}",
                token=student_token,
                timeout=args.timeout,
            )
            _expect_status(results, name="学生节点详情 /api/graph/node/{kp_id}", code=code)
        else:
            _add(results, name="学生节点详情检查", ok=True, detail="已跳过：当前课程无知识点")
    else:
        _add(results, name="学生图谱地图检查", ok=True, detail="已跳过：系统无课程数据")

    passed = sum(1 for item in results if item.ok)
    total = len(results)
    _write_report(results, output)

    print(f"[DONE] smoke acceptance: {passed}/{total} passed")
    print(f"[REPORT] {output}")
    return 0 if passed == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
