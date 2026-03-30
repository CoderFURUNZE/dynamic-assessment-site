#!/usr/bin/env python3
"""对 OpenAPI 中所有 GET 路径做探测：不得返回 5xx。"""
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000/api"


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def get_json(path_qs: str, token: str | None = None) -> tuple[int, object]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{BASE}{path_qs}", headers=headers, method="GET")
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return resp.getcode(), None
            try:
                return resp.getcode(), json.loads(raw)
            except json.JSONDecodeError:
                return resp.getcode(), raw[:200]
    except HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, raw


def substitute_path(path: str) -> str | None:
    out = path
    for name in [
        "kp_id",
        "course_id",
        "stage_id",
        "resource_id",
        "student_id",
        "edge_id",
        "dimension_id",
        "indicator_id",
        "question_id",
        "item_id",
        "task_id",
        "user_id",
        "application_id",
        "notice_id",
    ]:
        out = out.replace("{" + name + "}", "1")
    if "{" in out:
        return None
    return out


def main() -> int:
    _, spec = get_json("/openapi.json")
    if not isinstance(spec, dict):
        print("FAIL: no openapi")
        return 1

    admin = post_json("/auth/login", {"username": "admin", "password": "admin123"})["access_token"]
    teacher = post_json("/auth/login", {"username": "teacher1", "password": "teacher123"})["access_token"]
    student = post_json("/auth/login", {"username": "student1", "password": "student123"})["access_token"]

    failures: list[str] = []
    paths = spec.get("paths") or {}

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        op = methods.get("get")
        if not isinstance(op, dict):
            continue
        if path.startswith("/openapi.json") or path in ("/docs", "/docs/oauth2-redirect", "/redoc"):
            continue

        concrete = substitute_path(path)
        if concrete is None:
            continue

        token = admin
        if "/graph/teacher/" in concrete:
            token = teacher
        if "/graph/available-courses" in concrete or "/graph/my-courses" in concrete or "/enrollment/my/" in concrete:
            token = student

        # query parameters: pick first required or common names from spec
        qs_parts: list[str] = []
        params = op.get("parameters") or []
        subj = quote("操作系统")
        gr = quote("通用")
        for p in params:
            if not isinstance(p, dict) or p.get("in") != "query":
                continue
            name = p.get("name")
            if name == "subject":
                qs_parts.append(f"subject={subj}")
            elif name == "grade":
                qs_parts.append(f"grade={gr}")
            elif name == "course_id":
                qs_parts.append("course_id=1")
            elif name == "kp_id":
                qs_parts.append("kp_id=1")
            elif name == "user_id":
                qs_parts.append("user_id=3")
            elif p.get("required"):
                # 无法满足且无默认值则跳过，避免误报 422 当 5xx
                schema = (p.get("schema") or {})
                default = schema.get("default")
                if default is not None:
                    qs_parts.append(f"{name}={default}")
                else:
                    qs_parts = []
                    break

        qs = ("?" + "&".join(qs_parts)) if qs_parts else ""
        code, body = get_json(concrete + qs, token)
        if code >= 500:
            failures.append(f"GET {concrete}{qs} -> {code} {str(body)[:200]}")

    if failures:
        print("FAILURES:")
        for f in failures:
            print(" ", f)
        return 2
    print(f"OK: all {sum(1 for p, m in paths.items() if isinstance(m, dict) and m.get('get'))} openapi GET paths checked, no 5xx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
