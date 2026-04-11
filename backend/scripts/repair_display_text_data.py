from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.db.models import Course, CourseStage
from app.db.session import engine


COURSE_FIXTURES = {
    "OS": {
        "title": "操作系统",
        "description": "围绕操作系统原理、并发机制、存储管理和文件系统展开，适合阶段画像与知识图谱联动演示。",
        "target_class": "计科2301",
        "stages": {
            1: ("阶段一：系统基础与进程管理", "完成操作系统概述、进程线程与 CPU 调度的学习与阶段评价。"),
            2: ("阶段二：并发控制与死锁", "围绕同步互斥、死锁分析与课堂表现进行阶段性评价。"),
            3: ("阶段三：存储管理与文件系统", "结合内存管理、虚拟内存和文件系统完成阶段总结。"),
        },
    },
    "DS": {
        "title": "数据结构",
        "description": "覆盖线性表、树、图与排序等核心内容，适合展示学习路径、练习反馈与阶段评价。",
        "target_class": "计科2302",
        "stages": {
            1: ("阶段一：线性结构基础", "完成线性表、栈、队列与串的基础学习和课堂练习。"),
            2: ("阶段二：树结构与递归", "围绕树、二叉树与递归应用开展练习、测验和反馈。"),
            3: ("阶段三：图与排序综合", "完成图结构、遍历算法与排序方法的综合学习评价。"),
        },
    },
    "CN": {
        "title": "计算机网络",
        "description": "聚焦网络体系结构、传输控制、路由交换和应用层协议，适合真实教学演示。",
        "target_class": "网工2301",
        "stages": {
            1: ("阶段一：网络体系结构", "学习分层模型、网络设备和数据传输基础，完成阶段检测。"),
            2: ("阶段二：传输与路由机制", "围绕 TCP/IP、拥塞控制和路由协议开展学习与练习。"),
            3: ("阶段三：应用服务与综合分析", "综合分析应用层协议、抓包现象和网络故障排查思路。"),
        },
    },
    "CO": {
        "title": "计算机组成原理",
        "description": "从 CPU、存储体系、指令执行与 I/O 机制展开，适合展示过程性学习与动态评价。",
        "target_class": "计科2303",
        "stages": {
            1: ("阶段一：数据表示与运算器", "学习数制转换、数据表示和运算器结构，完成基础练习。"),
            2: ("阶段二：控制器与 CPU", "围绕指令执行、控制方式与 CPU 结构完成阶段学习。"),
            3: ("阶段三：存储系统与输入输出", "结合主存层次、总线与 I/O 机制完成综合分析。"),
        },
    },
}


def repair_display_text_data() -> dict[str, int | bool]:
    fixed_courses = 0
    fixed_stages = 0

    with Session(engine) as session:
        courses = session.exec(select(Course)).all()
        for course in courses:
            if course.id is None:
                continue
            fixture = COURSE_FIXTURES.get(str(course.code or "").upper())
            if fixture is None:
                continue

            course.title = fixture["title"]
            course.description = fixture["description"]
            course.target_class = fixture["target_class"]
            session.add(course)
            fixed_courses += 1

            stages = session.exec(
                select(CourseStage)
                .where(CourseStage.course_id == int(course.id))
                .order_by(CourseStage.stage_order, CourseStage.id)
            ).all()
            stage_map = fixture["stages"]
            for stage in stages:
                stage_fixture = stage_map.get(int(stage.stage_order or 0))
                if stage_fixture is None:
                    continue
                stage.title = stage_fixture[0]
                stage.description = stage_fixture[1]
                session.add(stage)
                fixed_stages += 1

        session.commit()

    return {"ok": True, "fixed_courses": fixed_courses, "fixed_stages": fixed_stages}


if __name__ == "__main__":
    print(repair_display_text_data())
