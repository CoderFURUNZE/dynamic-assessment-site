from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import settings


def bailian_available() -> bool:
    api_key = (settings.bailian_api_key or settings.dashscope_api_key or "").strip()
    return bool(settings.bailian_enabled and api_key)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def _shorten_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def enhance_recommendation_with_bailian(context: dict[str, Any]) -> dict[str, Any]:
    """
    Ask Bailian to polish and personalize an already-computed recommendation.

    The graph/rule engine remains authoritative for target selection. Bailian only
    returns student-facing wording and path explanations, so an API failure cannot
    break the recommendation flow.
    """
    api_key = (settings.bailian_api_key or settings.dashscope_api_key or "").strip()
    if not (settings.bailian_enabled and api_key):
        return {}

    system_prompt = (
        "你是学习路径推荐助手。必须基于输入的统一知识图谱候选结果、学生画像和掌握度生成建议；"
        "不要编造不存在的知识点、资源或题目。输出必须是合法 JSON，不要输出 Markdown。"
    )
    user_prompt = {
        "task": "为学生生成个性化学习路径推荐说明",
        "constraints": [
            "target_kp_id 必须优先使用 local_recommendation.target_kp.id",
            "personalized_path 只能使用 context 中出现过的知识点 id",
            "reason_summary 不超过 80 个中文字",
            "advice_text 不超过 120 个中文字",
            "student_message 使用温和、具体、可执行的中文",
        ],
        "output_schema": {
            "target_kp_id": "number",
            "reason_summary": "string",
            "advice_text": "string",
            "personalized_path": [{"kp_id": "number", "title": "string", "action": "string"}],
            "student_message": "string",
            "teacher_explanation": "string",
        },
        "context": context,
    }

    base_url = settings.bailian_base_url.rstrip("/")
    payload = {
        "model": settings.bailian_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=float(settings.bailian_timeout_seconds)) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return {"provider": "bailian", "enabled": True, "ok": False, "error": _shorten_text(exc)}

    content = ""
    try:
        content = str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return {"provider": "bailian", "enabled": True, "ok": False, "error": "百炼返回格式不符合预期"}

    parsed = _extract_json_object(content)
    if not parsed:
        return {"provider": "bailian", "enabled": True, "ok": False, "error": "百炼未返回可解析 JSON"}

    return {
        "provider": "bailian",
        "enabled": True,
        "ok": True,
        "target_kp_id": parsed.get("target_kp_id"),
        "reason_summary": _shorten_text(parsed.get("reason_summary"), 160),
        "advice_text": _shorten_text(parsed.get("advice_text"), 240),
        "personalized_path": parsed.get("personalized_path") if isinstance(parsed.get("personalized_path"), list) else [],
        "student_message": _shorten_text(parsed.get("student_message"), 240),
        "teacher_explanation": _shorten_text(parsed.get("teacher_explanation"), 360),
    }
