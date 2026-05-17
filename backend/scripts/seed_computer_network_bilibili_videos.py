from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import KnowledgePoint, LearningResource, ResourceType  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402


SUBJECT = "计算机网络"
GRADE = "通用"
BVID = "BV19E411D78Q"
SOURCE_TITLE = "王道计算机考研 计算机网络"
SOURCE_OWNER = "王道计算机教育"
SOURCE_API = f"https://api.bilibili.com/x/web-interface/view?bvid={BVID}"

KP_PAGE_MAP: dict[str, int] = {
    "CN-01-01": 2,
    "CN-01-02": 9,
    "CN-01-03": 11,
    "CN-01-04": 12,
    "CN-01-05": 7,
    "CN-02-01": 13,
    "CN-02-02": 15,
    "CN-02-03": 22,
    "CN-02-04": 19,
    "CN-02-05": 25,
    "CN-02-06": 31,
    "CN-02-07": 38,
    "CN-03-01": 45,
    "CN-03-02": 48,
    "CN-03-03": 46,
    "CN-03-04": 52,
    "CN-03-05": 57,
    "CN-03-06": 59,
    "CN-03-07": 51,
    "CN-04-01": 74,
    "CN-04-02": 75,
    "CN-04-03": 78,
    "CN-04-04": 79,
    "CN-04-05": 81,
    "CN-04-06": 85,
    "CN-05-01": 87,
    "CN-05-02": 88,
    "CN-05-03": 94,
    "CN-05-04": 92,
    "CN-05-05": 91,
    "CN-05-06": 87,
    "CN-06-01": 94,
    "CN-06-02": 94,
    "CN-06-03": 94,
    "CN-06-04": 73,
    "CN-06-05": 73,
    "CN-07-01": 55,
    "CN-07-02": 94,
    "CN-07-03": 48,
    "CN-07-04": 1,
}

FALLBACK_PARTS: dict[int, str] = {
    1: "1.0_开篇_欢迎来到计算机网络的世界（咸鱼版）",
    2: "1.1_1 计算机网络的概念（咸鱼版）",
    7: "1.1_5_1 计算机网络的性能指标(上)（咸鱼版）",
    9: "1.2.1 计算机网络分层结构（上）（咸鱼版）",
    11: "1.2.3_1 OSI参考模型（咸鱼版）",
    12: "1.2.3_2 TCP IP模型（咸鱼版）",
    13: "2.1.1 通信基础的基本概念(咸鱼版）",
    15: "2.1.3_1 编码和调制（上）（咸鱼版）",
    19: "3.1 数据链路层的功能（咸鱼版）",
    22: "3.3.1_2 检错编码（循环冗余校验码）（咸鱼版）",
    25: "3.4_2 停止等待协议（咸鱼版）",
    31: "3.5.2_1 随机访问介质访问控制（咸鱼版）",
    38: "3.6.2 以太网与IEEE 802.3（咸鱼版）",
    45: "4.1 网络层的功能（咸鱼版）",
    46: "4.2.1 IPv4分组（咸鱼版）",
    48: "4.2.3 子网划分与和子网掩码（咸鱼版）",
    51: "4.2.6 网络地址转换 NAT（咸鱼版）",
    52: "4.2.7 地址解析协议ARP（咸鱼版）",
    55: "4.2.9_2 （选学）traceroute的实现原理（咸鱼版）",
    57: "4.4.1 路由算法（咸鱼版）",
    59: "4.4.3_1 RIP的基本概念（咸鱼版）",
    73: "4.7 网络层设备（咸鱼版）",
    74: "5.1 传输层提供的服务（咸鱼版）",
    75: "5.2.1 UDP数据报（咸鱼版）",
    78: "5.3.2 TCP报文段（咸鱼版）",
    79: "5.3.3_1 TCP连接管理（建立连接）（咸鱼版）",
    81: "5.3.4+5_1 TCP可靠传输、流量控制（咸鱼版）",
    85: "5.3.6_1 TCP拥塞控制（慢开始和拥塞避免）（咸鱼版）",
    87: "6.1 网络应用模型（咸鱼版）",
    88: "6.2_1 DNS概述（咸鱼版）",
    91: "6.3 FTP 文件传输协议（咸鱼版）",
    92: "6.4 电子邮件（咸鱼版）",
    94: "6.5.2 超文本传输协议HTTP（咸鱼版）",
}


def bilibili_embed_url(page: int) -> str:
    return f"https://player.bilibili.com/player.html?bvid={BVID}&page={page}"


def load_page_parts() -> dict[int, str]:
    request = urllib.request.Request(SOURCE_API, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if int(payload.get("code", -1)) != 0:
            return FALLBACK_PARTS
        return {int(item["page"]): str(item["part"]) for item in payload.get("data", {}).get("pages", [])}
    except Exception:
        return FALLBACK_PARTS


def upsert_video(session: Session, *, kp: KnowledgePoint, page: int, part: str) -> bool:
    url = bilibili_embed_url(page)
    row = session.exec(
        select(LearningResource).where(
            LearningResource.kp_id == int(kp.id),
            LearningResource.type == ResourceType.video,
            LearningResource.url == url,
        )
    ).first()
    created = row is None
    if row is None:
        row = LearningResource(subject=kp.subject, grade=kp.grade, kp_id=int(kp.id), title="")

    note = "安全/综合章节暂无完全对应分P，当前关联王道计算机网络中最接近的协议基础视频。" if str(kp.code).startswith(("CN-06", "CN-07")) else ""
    row.subject = kp.subject
    row.grade = kp.grade
    row.title = f"王道计算机考研计算机网络：{part}"
    row.url = url
    row.type = ResourceType.video
    row.category = "learning"
    row.description = f"{SOURCE_OWNER}《{SOURCE_TITLE}》P{page}，用于“{kp.title}”的视频资源学习。{note}".strip()
    row.tags = f"王道计算机考研,计算机网络,bilibili,{BVID},P{page},{kp.code}"
    row.detected_resource_type = "video"
    row.preview_type = "video_inline"
    row.preview_status = "ready"
    row.preview_error = ""
    row.converted_preview_url = url
    row.original_file_url = url
    row.source_kind = "external"
    row.updated_at = datetime.utcnow()
    session.add(row)
    return created


def main() -> None:
    init_db()
    page_parts = load_page_parts()
    with Session(engine) as session:
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)
            .order_by(KnowledgePoint.code)
        ).all()
        if not kps:
            raise RuntimeError("未找到计算机网络知识点，请先运行 seed_computer_network_course.py")

        created = 0
        updated = 0
        missing: list[str] = []
        for kp in kps:
            page = KP_PAGE_MAP.get(str(kp.code))
            if page is None:
                missing.append(str(kp.code))
                continue
            part = page_parts.get(page) or FALLBACK_PARTS.get(page) or f"{SOURCE_TITLE} P{page}"
            if upsert_video(session, kp=kp, page=page, part=part):
                created += 1
            else:
                updated += 1

        session.commit()
        print(
            {
                "source": SOURCE_TITLE,
                "bvid": BVID,
                "knowledge_points": len(kps),
                "created": created,
                "updated": updated,
                "missing": missing,
            }
        )


if __name__ == "__main__":
    main()
