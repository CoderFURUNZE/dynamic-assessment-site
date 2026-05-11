from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import (
    ChapterEdge,
    Course,
    CourseEnrollStatus,
    CourseLifecycleStatus,
    CourseStage,
    CourseTeacherActivation,
    KnowledgeEdge,
    KnowledgePoint,
    RelationType,
    TeacherCourseStatus,
    User,
    UserRole,
)
from app.db.session import engine


SUBJECT = "计算机网络"
GRADE = "通用"
COURSE_CODE = "CS-NETWORK-001"
TEACHER_USERNAME = "teacher"


CHAPTERS: list[tuple[str, list[tuple[str, str, str, float, float]]]] = [
    (
        "网络体系结构",
        [
            ("CN-01-01", "计算机网络概述", "理解网络定义、组成、性能指标和分组交换思想。", 0.92, 0.35),
            ("CN-01-02", "协议、服务与接口", "掌握协议三要素、服务原语和分层设计思想。", 0.86, 0.42),
            ("CN-01-03", "OSI参考模型", "理解七层模型各层职责及层间关系。", 0.78, 0.45),
            ("CN-01-04", "TCP/IP体系结构", "掌握TCP/IP四层模型及其与OSI模型的对应关系。", 0.92, 0.48),
            ("CN-01-05", "网络性能指标", "掌握带宽、吞吐量、时延、时延带宽积和往返时间。", 0.82, 0.55),
        ],
    ),
    (
        "物理层与数据链路层",
        [
            ("CN-02-01", "物理层基本概念", "理解信道、信号、码元、速率与传输媒体。", 0.74, 0.42),
            ("CN-02-02", "编码与调制", "掌握常见编码、调制和信道容量基本概念。", 0.7, 0.62),
            ("CN-02-03", "差错检测", "掌握奇偶校验、校验和与CRC的基本思想。", 0.82, 0.58),
            ("CN-02-04", "数据链路层服务", "理解成帧、透明传输、差错控制和流量控制。", 0.86, 0.5),
            ("CN-02-05", "可靠传输协议", "掌握停止等待、后退N帧和选择重传。", 0.9, 0.68),
            ("CN-02-06", "介质访问控制", "理解信道划分、随机接入和轮询访问。", 0.76, 0.6),
            ("CN-02-07", "以太网与交换机", "掌握以太网帧格式、MAC地址、交换机自学习。", 0.9, 0.57),
        ],
    ),
    (
        "网络层",
        [
            ("CN-03-01", "网络层服务模型", "理解虚电路与数据报服务、转发与路由的区别。", 0.78, 0.48),
            ("CN-03-02", "IPv4地址与子网划分", "掌握IP地址分类、CIDR、子网掩码和地址规划。", 0.95, 0.72),
            ("CN-03-03", "IP数据报格式", "掌握IPv4首部字段、分片和重组。", 0.82, 0.62),
            ("CN-03-04", "ARP与ICMP", "理解地址解析、差错报告和网络诊断。", 0.78, 0.55),
            ("CN-03-05", "路由算法", "掌握距离向量、链路状态和最短路径思想。", 0.9, 0.78),
            ("CN-03-06", "RIP、OSPF与BGP", "理解典型路由协议的适用范围和基本机制。", 0.84, 0.74),
            ("CN-03-07", "NAT与IPv6", "理解NAT工作过程、IPv6地址和过渡技术。", 0.72, 0.6),
        ],
    ),
    (
        "传输层",
        [
            ("CN-04-01", "传输层服务", "理解端到端通信、端口、复用与分用。", 0.86, 0.5),
            ("CN-04-02", "UDP协议", "掌握UDP首部、特点和适用场景。", 0.76, 0.43),
            ("CN-04-03", "TCP报文段", "掌握TCP首部字段、序号、确认号和窗口。", 0.9, 0.68),
            ("CN-04-04", "TCP连接管理", "掌握三次握手、四次挥手和连接状态变化。", 0.92, 0.72),
            ("CN-04-05", "TCP可靠传输", "理解确认、重传、滑动窗口和流量控制。", 0.95, 0.78),
            ("CN-04-06", "TCP拥塞控制", "掌握慢开始、拥塞避免、快重传和快恢复。", 0.92, 0.82),
        ],
    ),
    (
        "应用层",
        [
            ("CN-05-01", "应用层体系结构", "理解客户/服务器、P2P和套接字接口。", 0.74, 0.42),
            ("CN-05-02", "DNS系统", "掌握域名层次、递归查询、迭代查询和缓存。", 0.86, 0.58),
            ("CN-05-03", "HTTP与Web", "掌握HTTP报文、持久连接、Cookie和缓存。", 0.92, 0.62),
            ("CN-05-04", "电子邮件协议", "理解SMTP、POP3、IMAP和邮件传输过程。", 0.62, 0.45),
            ("CN-05-05", "FTP与文件传输", "理解控制连接、数据连接和文件传输模式。", 0.58, 0.42),
            ("CN-05-06", "Socket编程基础", "理解套接字、端口绑定和网络应用开发流程。", 0.72, 0.7),
        ],
    ),
    (
        "网络安全与管理",
        [
            ("CN-06-01", "网络安全基础", "理解机密性、完整性、认证和可用性。", 0.82, 0.52),
            ("CN-06-02", "对称与非对称加密", "掌握对称加密、公钥加密和数字签名基本思想。", 0.78, 0.68),
            ("CN-06-03", "TLS与HTTPS", "理解TLS握手、证书和HTTPS安全通信过程。", 0.86, 0.74),
            ("CN-06-04", "防火墙与入侵检测", "理解包过滤、状态检测、应用网关和IDS。", 0.68, 0.58),
            ("CN-06-05", "网络管理与SNMP", "理解网络管理模型、MIB和SNMP基本机制。", 0.55, 0.5),
        ],
    ),
    (
        "综合应用",
        [
            ("CN-07-01", "网络故障诊断", "综合使用ping、traceroute、nslookup等工具定位问题。", 0.82, 0.62),
            ("CN-07-02", "抓包分析基础", "使用抓包工具分析DNS、HTTP、TCP连接过程。", 0.86, 0.72),
            ("CN-07-03", "小型网络规划", "完成地址规划、交换路由配置和服务部署方案。", 0.9, 0.78),
            ("CN-07-04", "课程综合达标", "综合运用网络体系、协议分析和故障排查完成达标任务。", 0.95, 0.82),
        ],
    ),
]


PREREQUISITES = [
    ("CN-01-01", "CN-01-02"), ("CN-01-02", "CN-01-03"), ("CN-01-03", "CN-01-04"), ("CN-01-02", "CN-01-05"),
    ("CN-01-04", "CN-02-01"), ("CN-01-05", "CN-02-02"), ("CN-02-01", "CN-02-03"), ("CN-02-03", "CN-02-04"),
    ("CN-02-04", "CN-02-05"), ("CN-02-04", "CN-02-06"), ("CN-02-06", "CN-02-07"),
    ("CN-02-07", "CN-03-01"), ("CN-03-01", "CN-03-02"), ("CN-03-02", "CN-03-03"), ("CN-03-02", "CN-03-04"),
    ("CN-03-03", "CN-03-05"), ("CN-03-05", "CN-03-06"), ("CN-03-02", "CN-03-07"),
    ("CN-03-01", "CN-04-01"), ("CN-04-01", "CN-04-02"), ("CN-04-01", "CN-04-03"), ("CN-04-03", "CN-04-04"),
    ("CN-04-03", "CN-04-05"), ("CN-04-05", "CN-04-06"),
    ("CN-04-01", "CN-05-01"), ("CN-05-01", "CN-05-02"), ("CN-05-01", "CN-05-03"), ("CN-05-01", "CN-05-04"),
    ("CN-05-01", "CN-05-05"), ("CN-04-01", "CN-05-06"),
    ("CN-05-03", "CN-06-01"), ("CN-06-01", "CN-06-02"), ("CN-06-02", "CN-06-03"), ("CN-06-01", "CN-06-04"),
    ("CN-06-01", "CN-06-05"),
    ("CN-03-04", "CN-07-01"), ("CN-05-02", "CN-07-01"), ("CN-04-04", "CN-07-02"), ("CN-05-03", "CN-07-02"),
    ("CN-03-02", "CN-07-03"), ("CN-03-06", "CN-07-03"), ("CN-06-04", "CN-07-03"),
    ("CN-07-01", "CN-07-04"), ("CN-07-02", "CN-07-04"), ("CN-07-03", "CN-07-04"),
]

RELATED = [
    ("CN-01-04", "CN-03-03"), ("CN-02-05", "CN-04-05"), ("CN-03-02", "CN-07-01"),
    ("CN-04-06", "CN-05-03"), ("CN-05-02", "CN-06-03"),
]


def main() -> None:
    now = datetime.utcnow()
    with Session(engine) as session:
        teacher = session.exec(select(User).where(User.username == TEACHER_USERNAME)).first()
        if teacher is None or teacher.id is None:
            raise RuntimeError(f"teacher user not found: {TEACHER_USERNAME}")
        teacher.role = UserRole.teacher
        teacher.active = True

        old_kps = session.exec(select(KnowledgePoint).where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)).all()
        old_kp_ids = [int(kp.id) for kp in old_kps if kp.id is not None]
        if old_kp_ids:
            session.exec(delete(KnowledgeEdge).where((KnowledgeEdge.prereq_id.in_(old_kp_ids)) | (KnowledgeEdge.next_id.in_(old_kp_ids))))
            session.exec(delete(KnowledgePoint).where(KnowledgePoint.id.in_(old_kp_ids)))
        session.exec(delete(ChapterEdge).where(ChapterEdge.subject == SUBJECT, ChapterEdge.grade == GRADE))

        course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
        if course is None:
            course = Course(code=COURSE_CODE, title=SUBJECT)
            session.add(course)
            session.flush()
        course.title = SUBJECT
        course.description = "计算机网络课程，覆盖体系结构、链路层、网络层、传输层、应用层、安全与综合实践。"
        course.active = True
        course.lifecycle_status = CourseLifecycleStatus.active
        course.teacher_id = int(teacher.id)
        course.target_class = "计算机网络演示班"
        course.max_students = 120
        course.start_at = now
        course.end_at = now + timedelta(days=120)
        course.apply_deadline = now + timedelta(days=30)
        course.enroll_status = CourseEnrollStatus.open

        activation = session.exec(
            select(CourseTeacherActivation).where(
                CourseTeacherActivation.course_id == int(course.id),
                CourseTeacherActivation.teacher_id == int(teacher.id),
            )
        ).first()
        if activation is None:
            activation = CourseTeacherActivation(course_id=int(course.id), teacher_id=int(teacher.id))
            session.add(activation)
        activation.teaching_status = TeacherCourseStatus.teaching
        activation.activated_at = now
        activation.finished_at = None
        activation.updated_at = now

        session.exec(delete(CourseStage).where(CourseStage.course_id == int(course.id)))
        for order, (chapter, _) in enumerate(CHAPTERS, 1):
            session.add(
                CourseStage(
                    course_id=int(course.id),
                    subject=SUBJECT,
                    grade=GRADE,
                    title=chapter,
                    stage_order=order,
                    starts_at=now + timedelta(days=(order - 1) * 14),
                    ends_at=now + timedelta(days=order * 14 - 1),
                    description=f"{SUBJECT}：{chapter}阶段学习与评价。",
                )
            )

        kp_by_code: dict[str, KnowledgePoint] = {}
        chapter_gap_x = 430
        row_gap_y = 155
        for chapter_index, (chapter, items) in enumerate(CHAPTERS):
            base_x = 180 + (chapter_index % 3) * chapter_gap_x
            base_y = 140 + (chapter_index // 3) * 980
            for item_index, (code, title, desc, importance, difficulty) in enumerate(items):
                kp = KnowledgePoint(
                    subject=SUBJECT,
                    grade=GRADE,
                    code=code,
                    title=title,
                    description=desc,
                    chapter=chapter,
                    knowledge_tag="知识",
                    ability_tag="协议分析",
                    literacy_tag="工程实践",
                    importance=importance,
                    difficulty=difficulty,
                    pos_x=base_x + (item_index % 2) * 170,
                    pos_y=base_y + item_index * row_gap_y,
                    practice_total=4,
                    is_terminal=code == "CN-07-04",
                )
                session.add(kp)
                session.flush()
                kp_by_code[code] = kp

        for source, target in PREREQUISITES:
            session.add(
                KnowledgeEdge(
                    subject=SUBJECT,
                    grade=GRADE,
                    prereq_id=int(kp_by_code[source].id),
                    next_id=int(kp_by_code[target].id),
                    relation_type=RelationType.prerequisite,
                )
            )
        for source, target in RELATED:
            session.add(
                KnowledgeEdge(
                    subject=SUBJECT,
                    grade=GRADE,
                    prereq_id=int(kp_by_code[source].id),
                    next_id=int(kp_by_code[target].id),
                    relation_type=RelationType.related,
                )
            )

        for source, target in zip([chapter for chapter, _ in CHAPTERS], [chapter for chapter, _ in CHAPTERS][1:]):
            session.add(
                ChapterEdge(
                    subject=SUBJECT,
                    grade=GRADE,
                    source_chapter=source,
                    target_chapter=target,
                    relation_type=RelationType.prerequisite,
                )
            )

        session.commit()
        print(
            {
                "course": SUBJECT,
                "course_code": COURSE_CODE,
                "teacher": TEACHER_USERNAME,
                "knowledge_points": len(kp_by_code),
                "edges": len(PREREQUISITES) + len(RELATED),
                "chapters": len(CHAPTERS),
            }
        )


if __name__ == "__main__":
    main()
