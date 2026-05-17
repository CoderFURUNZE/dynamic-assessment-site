from __future__ import annotations

import mimetypes
import shutil
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from sqlmodel import Session

from app.core.config import settings
from app.db.models import LearningResource, ResourceType
from app.db.session import engine

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="resource-convert")

RESOURCE_UPLOAD_RULES = {
    "pdf": {"max_size_bytes": 25 * 1024 * 1024, "label": "PDF 文档"},
    "ppt": {"max_size_bytes": 60 * 1024 * 1024, "label": "PPT 课件"},
    "pptx": {"max_size_bytes": 60 * 1024 * 1024, "label": "PPT 课件"},
    "doc": {"max_size_bytes": 25 * 1024 * 1024, "label": "Word 文档"},
    "docx": {"max_size_bytes": 25 * 1024 * 1024, "label": "Word 文档"},
    "image": {"max_size_bytes": 10 * 1024 * 1024, "label": "图片资源"},
    "video": {"max_size_bytes": 300 * 1024 * 1024, "label": "视频资源"},
}


UPLOAD_CHUNK_SIZE = 1024 * 1024
SIGNATURE_READ_SIZE = 4096
MAX_RESOURCE_UPLOAD_BYTES = max(int(rule.get("max_size_bytes", 0) or 0) for rule in RESOURCE_UPLOAD_RULES.values())


def _media_root() -> Path:
    root = Path(settings.media_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resource_type_from_detected(detected_resource_type: str, *, category: str) -> ResourceType:
    normalized = (detected_resource_type or "").lower()
    if category == "recommend" and normalized in {"pdf", "ppt", "pptx", "doc", "docx", "book"}:
        return ResourceType.book
    mapping = {
        "pdf": ResourceType.pdf,
        "ppt": ResourceType.ppt,
        "pptx": ResourceType.pptx,
        "doc": ResourceType.doc,
        "docx": ResourceType.docx,
        "video": ResourceType.video,
        "image": ResourceType.image,
        "link": ResourceType.link,
    }
    return mapping.get(normalized, ResourceType.note)


def _preview_type_for_detected(detected_resource_type: str) -> str:
    normalized = (detected_resource_type or "").lower()
    if normalized == "pdf":
        return "pdf_inline"
    if normalized == "video":
        return "video_inline"
    if normalized == "image":
        return "image_inline"
    if normalized == "link":
        return "external_link"
    if normalized in {"ppt", "pptx", "doc", "docx"}:
        return "pdf_after_convert"
    return "download"


def _guess_extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _signature_detect(payload: bytes, filename: str, content_type: str | None, source_path: Path | None = None) -> tuple[str, str]:
    prefix = payload[:32]
    ext = _guess_extension(filename)
    guessed_mime = (content_type or mimetypes.guess_type(filename)[0] or "").lower()

    if prefix.startswith(b"%PDF"):
        return "application/pdf", "pdf"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "image"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "image"
    if prefix.startswith(b"GIF87a") or prefix.startswith(b"GIF89a"):
        return "image/gif", "image"
    if prefix.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "image/webp", "image"
    if prefix.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm", "video"
    if b"ftyp" in payload[:16]:
        return guessed_mime or "video/mp4", "video"
    if prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        if ext == ".ppt":
            return "application/vnd.ms-powerpoint", "ppt"
        if ext == ".doc":
            return "application/msword", "doc"
    if zipfile.is_zipfile(Path(filename)) if False else False:
        pass
    try:
        with zipfile.ZipFile(Path(filename), "r"):  # pragma: no cover - never executed
            pass
    except Exception:
        pass
    try:
        if source_path is not None:
            archive_source = source_path
        else:
            from io import BytesIO

            archive_source = BytesIO(payload)
        with zipfile.ZipFile(archive_source, "r") as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" in names:
                if any(name.startswith("ppt/") for name in names):
                    return "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"
                if any(name.startswith("word/") for name in names):
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
    except Exception:
        pass
    if guessed_mime.startswith("image/"):
        return guessed_mime, "image"
    if guessed_mime.startswith("video/"):
        return guessed_mime, "video"
    if ext in {".ppt", ".pptx"}:
        return guessed_mime or "application/vnd.ms-powerpoint", "pptx" if ext == ".pptx" else "ppt"
    if ext in {".doc", ".docx"}:
        return guessed_mime or "application/msword", "docx" if ext == ".docx" else "doc"
    if ext == ".pdf":
        return "application/pdf", "pdf"
    raise ValueError("Unsupported file type")


def detect_uploaded_file(
    *,
    filename: str,
    payload: bytes,
    content_type: str | None,
    file_size_bytes: int | None = None,
    source_path: Path | None = None,
) -> dict:
    detected_mime_type, detected_resource_type = _signature_detect(payload, filename, content_type, source_path)
    _validate_upload_constraints(
        filename=filename,
        file_size_bytes=len(payload) if file_size_bytes is None else file_size_bytes,
        detected_resource_type=detected_resource_type,
        detected_mime_type=detected_mime_type,
    )
    ext = _guess_extension(filename)
    ext_map = {
        ".pdf": "pdf",
        ".ppt": "ppt",
        ".pptx": "pptx",
        ".doc": "doc",
        ".docx": "docx",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
        ".webp": "image",
        ".mp4": "video",
        ".webm": "video",
    }
    extension_detected = ext_map.get(ext, "")
    return {
        "original_file_name": filename,
        "file_extension": ext,
        "detected_mime_type": detected_mime_type,
        "detected_resource_type": detected_resource_type,
        "preview_type": _preview_type_for_detected(detected_resource_type),
        "extension_mismatch": bool(extension_detected and extension_detected != detected_resource_type),
        "upload_rule": RESOURCE_UPLOAD_RULES.get(detected_resource_type, {}),
    }


def _validate_upload_constraints(*, filename: str, file_size_bytes: int, detected_resource_type: str, detected_mime_type: str) -> None:
    normalized = (detected_resource_type or "").lower()
    rule = RESOURCE_UPLOAD_RULES.get(normalized)
    if rule:
        max_size_bytes = int(rule.get("max_size_bytes", 0) or 0)
        if max_size_bytes and file_size_bytes > max_size_bytes:
            max_mb = max_size_bytes / 1024 / 1024
            raise ValueError(f"{rule.get('label', '资源')}大小不能超过 {max_mb:.0f} MB")
    if normalized == "video":
        ext = _guess_extension(filename)
        if ext not in {".mp4", ".webm"}:
            raise ValueError("视频仅支持 MP4 或 WEBM 格式，建议使用 16:9 横屏资源")
    if normalized == "image":
        ext = _guess_extension(filename)
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            raise ValueError("图片仅支持 PNG、JPG、GIF、WEBP 格式")
    if normalized in {"ppt", "pptx", "doc", "docx", "pdf"} and not detected_mime_type:
        raise ValueError("文档资源识别失败，请检查文件格式")


def store_uploaded_file(*, kp_id: int, filename: str, payload: bytes, detected_resource_type: str) -> dict:
    ext = _guess_extension(filename)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    folder = _media_root() / "resources" / "original"
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"kp_{kp_id}_{ts}{ext or ''}"
    dest = folder / stored_name
    dest.write_bytes(payload)
    return {
        "absolute_path": str(dest),
        "relative_url": f"{settings.media_url}/resources/original/{stored_name}",
        "file_size_bytes": len(payload),
        "stored_name": stored_name,
    }


def _stream_to_path(
    source: BinaryIO,
    dest: Path,
    *,
    max_size_bytes: int,
    max_size_label: str,
) -> tuple[int, bytes]:
    total = 0
    signature = bytearray()
    try:
        with dest.open("wb") as target:
            while True:
                chunk = source.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if max_size_bytes and total > max_size_bytes:
                    max_mb = max_size_bytes / 1024 / 1024
                    raise ValueError(f"{max_size_label}大小不能超过 {max_mb:.0f} MB")
                if len(signature) < SIGNATURE_READ_SIZE:
                    signature.extend(chunk[: SIGNATURE_READ_SIZE - len(signature)])
                target.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return total, bytes(signature)


def inspect_uploaded_file_stream(*, filename: str, source: BinaryIO, content_type: str | None) -> dict:
    temp_root = _media_root() / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="detect_", suffix=_guess_extension(filename), dir=temp_root, delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        file_size_bytes, signature = _stream_to_path(
            source,
            temp_path,
            max_size_bytes=MAX_RESOURCE_UPLOAD_BYTES,
            max_size_label="资源",
        )
        if file_size_bytes <= 0:
            raise ValueError("file is empty")
        return detect_uploaded_file(
            filename=filename,
            payload=signature,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            source_path=temp_path,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def store_uploaded_file_stream(*, kp_id: int, filename: str, source: BinaryIO, content_type: str | None) -> dict:
    ext = _guess_extension(filename)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    folder = _media_root() / "resources" / "original"
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"kp_{kp_id}_{ts}{ext or ''}"
    dest = folder / stored_name
    try:
        file_size_bytes, signature = _stream_to_path(
            source,
            dest,
            max_size_bytes=MAX_RESOURCE_UPLOAD_BYTES,
            max_size_label="资源",
        )
        if file_size_bytes <= 0:
            raise ValueError("file is empty")
        detected = detect_uploaded_file(
            filename=filename,
            payload=signature,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            source_path=dest,
        )
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return {
        "absolute_path": str(dest),
        "relative_url": f"{settings.media_url}/resources/original/{stored_name}",
        "file_size_bytes": file_size_bytes,
        "stored_name": stored_name,
        "detected": detected,
    }


def store_video_file_stream(*, filename: str, source: BinaryIO, relative_folder: str = "videos") -> dict:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    folder = _media_root() / relative_folder
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{ts}_{filename}"
    dest = folder / stored_name
    max_size_bytes = int(RESOURCE_UPLOAD_RULES["video"]["max_size_bytes"])
    file_size_bytes, _signature = _stream_to_path(
        source,
        dest,
        max_size_bytes=max_size_bytes,
        max_size_label="视频资源",
    )
    if file_size_bytes <= 0:
        dest.unlink(missing_ok=True)
        raise ValueError("file is empty")
    return {
        "absolute_path": str(dest),
        "relative_url": f"{settings.media_url}/{relative_folder}/{stored_name}",
        "file_size_bytes": file_size_bytes,
        "stored_name": stored_name,
    }


def maybe_prepare_preview(*, resource: LearningResource) -> None:
    detected = (resource.detected_resource_type or "").lower()
    if detected in {"pdf", "video", "image"}:
        resource.converted_preview_url = resource.original_file_url or resource.url
        resource.preview_status = "ready"
        return
    if detected == "link":
        resource.preview_status = "ready"
        resource.preview_type = "external_link"
        resource.converted_preview_url = ""
        return
    resource.preview_status = "processing"
    enqueue_conversion(resource_id=int(resource.id))


def enqueue_conversion(*, resource_id: int) -> None:
    _executor.submit(_convert_resource_to_pdf, resource_id)


def _convert_resource_to_pdf(resource_id: int) -> None:
    with Session(engine) as session:
        resource = session.get(LearningResource, resource_id)
        if resource is None:
            return
        source_url = resource.original_file_url or resource.url
        if not source_url.startswith(settings.media_url):
            resource.preview_status = "failed"
            resource.preview_error = "当前资源不是本地上传文件，无法生成预览版"
            session.add(resource)
            session.commit()
            return
        source_path = _media_root() / source_url.removeprefix(settings.media_url).lstrip("/")
        if not source_path.exists():
            resource.preview_status = "failed"
            resource.preview_error = "原始文件不存在，无法生成预览版"
            session.add(resource)
            session.commit()
            return
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            resource.preview_status = "failed"
            resource.preview_error = "服务器未安装 LibreOffice，暂时无法把 Office 文档转换为 PDF"
            session.add(resource)
            session.commit()
            return
        output_dir = _media_root() / "resources" / "preview"
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(source_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            resource.preview_status = "failed"
            resource.preview_error = f"转换失败：{exc}"
            session.add(resource)
            session.commit()
            return

        preview_path = output_dir / f"{source_path.stem}.pdf"
        if not preview_path.exists():
            resource.preview_status = "failed"
            resource.preview_error = "转换流程已执行，但未生成 PDF 预览文件"
            session.add(resource)
            session.commit()
            return
        resource.converted_preview_url = f"{settings.media_url}/resources/preview/{preview_path.name}"
        resource.preview_status = "ready"
        resource.preview_error = ""
        session.add(resource)
        session.commit()


def build_resource_payload(resource: LearningResource) -> dict:
    preview_url = resource.converted_preview_url or resource.original_file_url or resource.url
    return {
        "id": int(resource.id),
        "kp_id": int(resource.kp_id),
        "type": resource.type.value if hasattr(resource.type, "value") else str(resource.type),
        "title": resource.title,
        "url": preview_url,
        "category": resource.category or ("recommend" if str(resource.type) in {"book", "recommend_book"} else "learning"),
        "description": resource.description or "",
        "tags": resource.tags or "",
        "original_file_name": resource.original_file_name or "",
        "file_extension": resource.file_extension or "",
        "detected_mime_type": resource.detected_mime_type or "",
        "detected_resource_type": resource.detected_resource_type or "",
        "preview_type": resource.preview_type or "",
        "preview_status": resource.preview_status or "ready",
        "preview_error": resource.preview_error or "",
        "converted_preview_url": resource.converted_preview_url or "",
        "original_file_url": resource.original_file_url or "",
        "file_size_bytes": int(resource.file_size_bytes or 0),
        "extension_mismatch": bool(resource.extension_mismatch),
        "source_kind": resource.source_kind or "external",
    }
