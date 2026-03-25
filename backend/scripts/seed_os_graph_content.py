from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import delete
from sqlmodel import Session, select

from app.db.models import (
    KpQuestionAssignment,
    KnowledgePoint,
    LearningResource,
    Question,
    PracticeAttempt,
    ReviewSchedule,
    ResourceType,
)
from app.db.session import engine


OS_RESOURCE_BANK: dict[str, dict[str, list[dict[str, str]] | list[dict[str, object]]]] = {
    "1.1": {
        "resources": [
            {
                "title": "操作系统概念导读：操作系统是什么、做什么",
                "url": "https://zh.wikipedia.org/wiki/%E6%93%8D%E4%BD%9C%E7%B3%BB%E7%BB%9F",
                "type": "link",
                "description": "适合第一次接触操作系统时先读，先建立“资源管理者 + 用户接口 + 控制程序”三层认识。",
                "tags": "基础概念,入门,必读",
            },
            {
                "title": "IBM 技术文章：What is an operating system?",
                "url": "https://www.ibm.com/think/topics/operating-system",
                "type": "link",
                "description": "从工业视角解释操作系统的核心职责，适合建立更贴近工程实践的理解。",
                "tags": "英文阅读,工业视角,概念建立",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：《现代操作系统》第一章",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "建议结合课程内容阅读第一章，形成对操作系统目标与演化背景的整体认识。",
                "tags": "教材,推荐书籍,体系化",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "下列哪一项最能概括操作系统的核心作用？",
                "options": ["直接替代应用软件完成业务逻辑", "管理硬件资源并为用户与应用提供统一服务", "只负责图形界面显示", "只在计算机关机时工作"],
                "answer": "B",
                "explanation": "操作系统的本质是管理资源、控制执行并向上提供统一接口，而不是直接替代应用完成业务。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "概念理解,基础题",
            },
            {
                "type": "mcq",
                "prompt": "下面哪一项不属于典型的操作系统资源管理对象？",
                "options": ["处理器", "内存", "I/O 设备", "试卷阅卷老师"],
                "answer": "D",
                "explanation": "处理器、内存、I/O 设备都由操作系统协调管理，阅卷老师不属于计算机系统资源。",
                "difficulty": 0.30,
                "source": "课程自编",
                "tags": "资源管理,辨析",
            },
            {
                "type": "blank",
                "prompt": "操作系统位于用户与硬件之间，本质上是计算机系统中的 _______ 与资源管理中心。",
                "options": [],
                "answer": "控制程序",
                "explanation": "教材通常将操作系统描述为控制程序和资源管理者。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "术语记忆",
            },
        ],
    },
    "1.2": {
        "resources": [
            {
                "title": "操作系统的发展历程与分类总览",
                "url": "https://www.geeksforgeeks.org/types-of-operating-systems/",
                "type": "link",
                "description": "快速梳理批处理、分时、实时、分布式等系统类型，适合课后横向对比。",
                "tags": "发展历程,分类,对比",
            },
            {
                "title": "Linux、Windows、macOS 的演化差异简述",
                "url": "https://www.redhat.com/en/topics/linux/what-is-linux",
                "type": "link",
                "description": "通过现代系统案例回看操作系统分类与设计取舍。",
                "tags": "现代系统,案例,延伸",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：《操作系统精髓与设计原理》系统类型章节",
                "url": "https://book.douban.com/subject/26979890/",
                "type": "book",
                "description": "适合建立“系统目标决定系统类型”的分析框架。",
                "tags": "教材,推荐书籍,系统类型",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "分时操作系统最主要的目标是提高哪一类体验？",
                "options": ["单个任务绝对吞吐量", "多用户交互响应性", "断电后的恢复速度", "磁盘物理容量"],
                "answer": "B",
                "explanation": "分时系统通过时间片轮转提升多个用户/任务的交互响应。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "系统类型,分时系统",
            },
            {
                "type": "mcq",
                "prompt": "下列哪一项通常更强调“在规定时间内完成响应”？",
                "options": ["实时操作系统", "批处理系统", "桌面系统", "办公软件"],
                "answer": "A",
                "explanation": "实时系统关注时限约束，特别是硬实时场景。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "实时系统,概念辨析",
            },
            {
                "type": "blank",
                "prompt": "按照操作系统的发展顺序，通常先后经历手工操作、批处理、分时，再到 _______ 与网络/分布式等系统。",
                "options": [],
                "answer": "实时系统",
                "explanation": "课程中常把实时系统作为后续重要类型之一。",
                "difficulty": 0.45,
                "source": "课程自编",
                "tags": "发展历程",
            },
        ],
    },
    "1.3": {
        "resources": [
            {
                "title": "操作系统常见术语表：并发、共享、异步、虚拟",
                "url": "https://en.wikipedia.org/wiki/Operating_system",
                "type": "link",
                "description": "结合课程术语做概念对照，适合查缺补漏。",
                "tags": "术语表,基础,复习",
            },
            {
                "title": "并发与并行的差异说明",
                "url": "https://en.wikipedia.org/wiki/Concurrency_(computer_science)",
                "type": "link",
                "description": "重点理解“并发不等于并行”，避免后续进程线程章节混淆。",
                "tags": "并发,并行,概念辨析",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：操作系统关键术语速查手册",
                "url": "https://book.douban.com/subject/4124283/",
                "type": "book",
                "description": "适合建立术语之间的逻辑关系，而不是孤立背诵。",
                "tags": "术语,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "“多个程序在一段时间内交替推进”更准确对应哪个概念？",
                "options": ["并发", "并行", "死锁", "独占"],
                "answer": "A",
                "explanation": "并发强调时间上的交替推进，并不要求同一时刻物理同时执行。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "并发,术语辨析",
            },
            {
                "type": "mcq",
                "prompt": "操作系统中的“共享”通常是指什么？",
                "options": ["任意用户都能修改内核代码", "多个执行实体按规则共同使用系统资源", "所有设备永久免费", "用户之间共享密码"],
                "answer": "B",
                "explanation": "共享强调资源被多个进程/线程按一定机制共同使用。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "共享,资源",
            },
            {
                "type": "blank",
                "prompt": "并发强调逻辑上的同时推进，并行强调物理上的 _______ 执行。",
                "options": [],
                "answer": "同时",
                "explanation": "并行通常表示多个计算在同一时刻由不同处理单元同时执行。",
                "difficulty": 0.38,
                "source": "课程自编",
                "tags": "并发并行",
            },
        ],
    },
    "1.4": {
        "resources": [
            {
                "title": "操作系统体系结构：整体式、层次式、微内核式",
                "url": "https://en.wikipedia.org/wiki/Microkernel",
                "type": "link",
                "description": "重点理解为什么不同体系结构会影响性能、可靠性和可扩展性。",
                "tags": "体系结构,微内核,整体式",
            },
            {
                "title": "单体内核与微内核的取舍分析",
                "url": "https://www.redhat.com/en/topics/linux/what-is-the-linux-kernel",
                "type": "link",
                "description": "从 Linux 内核案例理解单体内核路线的现实意义。",
                "tags": "内核,结构设计,案例",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：《现代操作系统》内核结构章节",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "适合把抽象的结构图和真实系统实现联系起来。",
                "tags": "内核结构,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "微内核结构通常把更多服务放到哪里？",
                "options": ["用户态", "寄存器里", "显卡里", "BIOS 里"],
                "answer": "A",
                "explanation": "微内核只保留最核心机制在内核态，其他服务尽量放在用户态。",
                "difficulty": 0.48,
                "source": "课程自编",
                "tags": "微内核,结构理解",
            },
            {
                "type": "mcq",
                "prompt": "层次式操作系统结构的主要优点之一是？",
                "options": ["无需任何接口设计", "便于模块化理解和维护", "永远比单体内核快", "不需要硬件支持"],
                "answer": "B",
                "explanation": "层次式结构强调清晰分层和接口关系，利于理解与维护。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "层次式,优点",
            },
            {
                "type": "blank",
                "prompt": "把系统服务尽量移出内核、只保留最小核心机制的设计路线叫 _______ 结构。",
                "options": [],
                "answer": "微内核",
                "explanation": "这是微内核结构的核心思想。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "名词记忆",
            },
        ],
    },
    "1.5": {
        "resources": [
            {
                "title": "从 BIOS/UEFI 到操作系统启动：引导过程概览",
                "url": "https://en.wikipedia.org/wiki/Booting",
                "type": "link",
                "description": "适合建立启动流程的整体时序：上电自检、加载引导程序、进入内核。",
                "tags": "引导,启动流程,BIOS",
            },
            {
                "title": "UEFI 基础说明",
                "url": "https://learn.microsoft.com/en-us/windows-hardware/drivers/bringup/uefi-in-windows",
                "type": "link",
                "description": "理解现代机器上的 UEFI 与传统 BIOS 差异。",
                "tags": "UEFI,启动,现代平台",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：Linux 启动过程与引导加载程序",
                "url": "https://book.douban.com/subject/27162743/",
                "type": "book",
                "description": "适合把课程中的引导流程和真实系统落地过程对应起来。",
                "tags": "Linux启动,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "计算机上电后，最先参与操作系统启动流程的通常是？",
                "options": ["应用程序", "数据库", "固件程序（BIOS/UEFI）", "浏览器插件"],
                "answer": "C",
                "explanation": "上电后首先由固件进行初始化与引导入口控制。",
                "difficulty": 0.36,
                "source": "课程自编",
                "tags": "启动流程,基础题",
            },
            {
                "type": "mcq",
                "prompt": "引导加载程序的主要任务之一是？",
                "options": ["直接编辑用户文档", "把操作系统内核装入内存并转交控制权", "关闭显示器", "删除磁盘分区"],
                "answer": "B",
                "explanation": "引导加载程序负责装载内核并交出执行控制。",
                "difficulty": 0.38,
                "source": "课程自编",
                "tags": "引导程序",
            },
            {
                "type": "blank",
                "prompt": "在操作系统启动链路中，负责装入内核并把控制权交给内核的程序通常称为 _______。",
                "options": [],
                "answer": "引导加载程序",
                "explanation": "教材中常称 boot loader/引导加载程序。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "启动链路",
            },
        ],
    },
    "1.6": {
        "resources": [
            {
                "title": "虚拟机基础：什么是虚拟化",
                "url": "https://zh.wikipedia.org/wiki/%E8%99%9A%E6%8B%9F%E6%9C%BA",
                "type": "link",
                "description": "先建立虚拟机、宿主机、客户机操作系统的关系。",
                "tags": "虚拟机,虚拟化,基础",
            },
            {
                "title": "VMware 对虚拟化的说明",
                "url": "https://www.vmware.com/topics/glossary/content/virtual-machine.html",
                "type": "link",
                "description": "用企业产品的语言理解虚拟机在教学和生产中的作用。",
                "tags": "VMware,虚拟化,案例",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：虚拟化技术与容器的区别",
                "url": "https://www.ibm.com/think/topics/virtualization",
                "type": "book",
                "description": "虽然是文章形式，但很适合做扩展阅读，帮助区分虚拟机与容器。",
                "tags": "虚拟化,容器,扩展阅读",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "虚拟机中的“宿主机”通常指什么？",
                "options": ["运行虚拟化平台的真实物理机器", "虚拟机内的文档文件", "网络交换机", "数据库实例"],
                "answer": "A",
                "explanation": "宿主机是承载虚拟化环境的真实物理主机。",
                "difficulty": 0.34,
                "source": "课程自编",
                "tags": "虚拟机,基本概念",
            },
            {
                "type": "mcq",
                "prompt": "下面哪一项更符合虚拟机的典型用途？",
                "options": ["隔离运行不同环境", "提高纸质试卷打印质量", "替代全部硬盘硬件", "关闭 CPU 调度"],
                "answer": "A",
                "explanation": "虚拟机常用于环境隔离、系统测试、资源整合。",
                "difficulty": 0.30,
                "source": "课程自编",
                "tags": "虚拟化用途",
            },
            {
                "type": "blank",
                "prompt": "在一台物理机上模拟出多台逻辑机器的关键技术叫 _______。",
                "options": [],
                "answer": "虚拟化",
                "explanation": "这是虚拟机实现的基础思想。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "虚拟化",
            },
        ],
    },
    "2.1": {
        "resources": [
            {
                "title": "进程与线程概念对比",
                "url": "https://en.wikipedia.org/wiki/Process_(computing)",
                "type": "link",
                "description": "先从“资源分配单位”和“执行单位”的角度理解进程线程差异。",
                "tags": "进程,线程,概念",
            },
            {
                "title": "线程基础说明",
                "url": "https://en.wikipedia.org/wiki/Thread_(computing)",
                "type": "link",
                "description": "配合进程概念一起看，重点抓共享与独立部分。",
                "tags": "线程,基础,对比",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：并发程序设计中的进程与线程",
                "url": "https://book.douban.com/subject/30357170/",
                "type": "book",
                "description": "适合把课程概念与后续并发编程联系起来。",
                "tags": "并发,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "通常被视为资源分配基本单位的是？",
                "options": ["进程", "线程", "中断", "寄存器"],
                "answer": "A",
                "explanation": "进程通常是资源分配的基本单位，线程通常是调度执行的基本单位。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "进程线程,概念",
            },
            {
                "type": "mcq",
                "prompt": "同一进程内多个线程最典型的特征是？",
                "options": ["完全不共享任何地址空间", "共享进程资源但有各自执行流", "必须运行在不同计算机上", "一定不会并发执行"],
                "answer": "B",
                "explanation": "线程共享所属进程的大部分资源，但拥有自己的执行上下文。",
                "difficulty": 0.45,
                "source": "课程自编",
                "tags": "线程特性",
            },
            {
                "type": "blank",
                "prompt": "若说进程是资源分配单位，那么线程更常被视为 _______ 的基本单位。",
                "options": [],
                "answer": "调度",
                "explanation": "线程通常被视为调度和执行的基本单位。",
                "difficulty": 0.38,
                "source": "课程自编",
                "tags": "调度单位",
            },
        ],
    },
    "2.2": {
        "resources": [
            {
                "title": "进程调度基础：先来先服务、时间片轮转、优先级",
                "url": "https://en.wikipedia.org/wiki/Scheduling_(computing)",
                "type": "link",
                "description": "从常见调度算法入手，理解响应时间、公平性、吞吐量之间的平衡。",
                "tags": "调度,算法,基础",
            },
            {
                "title": "Linux 调度器概览",
                "url": "https://www.kernel.org/doc/html/latest/scheduler/index.html",
                "type": "link",
                "description": "用真实操作系统案例理解调度不是纸面算法，而是工程折中。",
                "tags": "Linux,调度器,工程实践",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：CPU 调度算法分析",
                "url": "https://book.douban.com/subject/25808895/",
                "type": "book",
                "description": "适合复习各种经典调度算法的适用场景。",
                "tags": "调度算法,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "时间片轮转调度最主要改善的是哪类体验？",
                "options": ["交互响应公平性", "永远最短平均周转时间", "硬盘寿命", "掉电恢复"],
                "answer": "A",
                "explanation": "时间片轮转通过轮换 CPU 时间提升交互系统的公平性与响应性。",
                "difficulty": 0.44,
                "source": "课程自编",
                "tags": "轮转调度",
            },
            {
                "type": "mcq",
                "prompt": "若一个长作业一直抢不到 CPU，这通常反映了调度中的什么问题？",
                "options": ["饥饿", "虚拟化", "脱机", "换页"],
                "answer": "A",
                "explanation": "长期得不到服务的现象称为饥饿。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "调度问题,饥饿",
            },
            {
                "type": "blank",
                "prompt": "调度算法评价时常关注吞吐量、周转时间和 _______ 时间等指标。",
                "options": [],
                "answer": "响应",
                "explanation": "响应时间是交互系统非常关键的评价指标。",
                "difficulty": 0.36,
                "source": "课程自编",
                "tags": "评价指标",
            },
        ],
    },
    "2.3": {
        "resources": [
            {
                "title": "同步与互斥概念导读",
                "url": "https://en.wikipedia.org/wiki/Concurrency_control",
                "type": "link",
                "description": "理解为什么并发程序需要控制共享资源访问顺序。",
                "tags": "同步,互斥,并发",
            },
            {
                "title": "互斥锁与信号量基础",
                "url": "https://en.wikipedia.org/wiki/Semaphore_(programming)",
                "type": "link",
                "description": "重点理解信号量和互斥锁解决的不是同一层问题。",
                "tags": "信号量,互斥锁,经典机制",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：经典并发控制问题",
                "url": "https://book.douban.com/subject/1231579/",
                "type": "book",
                "description": "建议结合生产者-消费者、读者-写者问题一起理解。",
                "tags": "并发控制,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "互斥主要解决哪类问题？",
                "options": ["多个执行流对共享临界资源的排他访问", "网络带宽不足", "磁盘格式化", "显卡驱动安装"],
                "answer": "A",
                "explanation": "互斥的核心是让共享临界区同一时刻只被一个执行流进入。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "互斥,临界区",
            },
            {
                "type": "mcq",
                "prompt": "信号量机制常用于？",
                "options": ["控制资源访问与同步顺序", "提高显示分辨率", "卸载操作系统", "物理磁盘加电"],
                "answer": "A",
                "explanation": "信号量是经典同步机制，可表达资源数量与先后约束。",
                "difficulty": 0.44,
                "source": "课程自编",
                "tags": "信号量,同步",
            },
            {
                "type": "blank",
                "prompt": "当多个并发实体都可能修改共享变量时，需要通过 _______ 机制来保护临界区。",
                "options": [],
                "answer": "互斥",
                "explanation": "互斥是临界区保护的基本思想。",
                "difficulty": 0.34,
                "source": "课程自编",
                "tags": "临界区",
            },
        ],
    },
    "2.4": {
        "resources": [
            {
                "title": "死锁基本概念与必要条件",
                "url": "https://zh.wikipedia.org/wiki/%E6%AD%BB%E9%94%81",
                "type": "link",
                "description": "先掌握死锁定义和四个必要条件，再理解预防、避免、检测与解除。",
                "tags": "死锁,四条件,基础",
            },
            {
                "title": "银行家算法概念导读",
                "url": "https://en.wikipedia.org/wiki/Banker%27s_algorithm",
                "type": "link",
                "description": "适合理解“安全状态”和“避免死锁”的思路。",
                "tags": "银行家算法,安全状态,避免",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：死锁处理策略比较",
                "url": "https://book.douban.com/subject/27162743/",
                "type": "book",
                "description": "建议结合实际系统场景区分预防、避免、检测和恢复。",
                "tags": "死锁,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "下列哪一项不是死锁产生的必要条件？",
                "options": ["互斥", "请求并保持", "可剥夺", "循环等待"],
                "answer": "C",
                "explanation": "死锁必要条件是互斥、请求并保持、不可剥夺、循环等待。",
                "difficulty": 0.46,
                "source": "课程自编",
                "tags": "死锁四条件",
            },
            {
                "type": "mcq",
                "prompt": "银行家算法更偏向哪种死锁处理策略？",
                "options": ["预防", "避免", "检测后恢复", "忽略死锁"],
                "answer": "B",
                "explanation": "银行家算法通过安全状态判断来避免进入不安全分配。",
                "difficulty": 0.48,
                "source": "课程自编",
                "tags": "银行家算法",
            },
            {
                "type": "blank",
                "prompt": "死锁处理中，若系统每次分配资源前都检查是否仍处于安全状态，这属于死锁 _______。",
                "options": [],
                "answer": "避免",
                "explanation": "安全状态判断是死锁避免的典型代表。",
                "difficulty": 0.45,
                "source": "课程自编",
                "tags": "安全状态",
            },
        ],
    },
    "3.1": {
        "resources": [
            {
                "title": "内存管理方式总览：连续分配、分页、分段",
                "url": "https://en.wikipedia.org/wiki/Memory_management",
                "type": "link",
                "description": "适合建立多种内存管理方式的总体框架。",
                "tags": "内存管理,分页,分段",
            },
            {
                "title": "分页与分段的差异说明",
                "url": "https://www.geeksforgeeks.org/difference-between-paging-and-segmentation/",
                "type": "link",
                "description": "建议重点看“逻辑结构”和“物理划分”两个维度的区别。",
                "tags": "分页,分段,对比",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：内存管理核心机制",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "适合结合页表、地址变换、碎片问题系统复习。",
                "tags": "内存管理,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "分页管理中，内存被划分成固定大小的什么单位？",
                "options": ["页框", "段", "文件", "作业流"],
                "answer": "A",
                "explanation": "分页管理中，物理内存划分为页框，逻辑地址空间划分为页。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "分页,基础",
            },
            {
                "type": "mcq",
                "prompt": "与分页相比，分段更突出哪种特征？",
                "options": ["按逻辑意义划分程序空间", "页大小固定", "绝不会有外部碎片", "完全不需要地址变换"],
                "answer": "A",
                "explanation": "分段强调按逻辑模块划分，如代码段、数据段、栈段等。",
                "difficulty": 0.46,
                "source": "课程自编",
                "tags": "分段,概念",
            },
            {
                "type": "blank",
                "prompt": "连续分配管理容易出现两类碎片，其中内部碎片多见于 _______ 分配场景。",
                "options": [],
                "answer": "固定分区",
                "explanation": "固定分区中分配单元固定，常导致内部碎片。",
                "difficulty": 0.52,
                "source": "课程自编",
                "tags": "碎片问题",
            },
        ],
    },
    "3.2": {
        "resources": [
            {
                "title": "虚拟内存概念与按需调页",
                "url": "https://en.wikipedia.org/wiki/Virtual_memory",
                "type": "link",
                "description": "重点理解“逻辑上大、物理上按需”的思想。",
                "tags": "虚拟内存,按需调页,基础",
            },
            {
                "title": "页面置换算法简介",
                "url": "https://en.wikipedia.org/wiki/Page_replacement_algorithm",
                "type": "link",
                "description": "理解 FIFO、LRU、OPT 等算法的目标和局限。",
                "tags": "页面置换,LRU,FIFO",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：虚拟内存与局部性原理",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "建议结合缺页中断与工作集概念理解。",
                "tags": "虚拟内存,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "虚拟内存技术能够成立的重要前提之一是程序访问具有？",
                "options": ["局部性", "随机性", "无穷性", "离散性"],
                "answer": "A",
                "explanation": "局部性原理决定了程序短时间内只会访问部分页面。",
                "difficulty": 0.44,
                "source": "课程自编",
                "tags": "局部性,虚拟内存",
            },
            {
                "type": "mcq",
                "prompt": "当访问的页面不在内存中时，会触发什么？",
                "options": ["缺页中断", "系统关机", "磁盘格式化", "电源切换"],
                "answer": "A",
                "explanation": "页面不在内存中会引发缺页中断，由系统负责调入。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "缺页中断",
            },
            {
                "type": "blank",
                "prompt": "页面置换算法中，选择“最近最久未使用”的页面淘汰，这种算法简称 _______。",
                "options": [],
                "answer": "LRU",
                "explanation": "LRU 是经典页面置换算法之一。",
                "difficulty": 0.38,
                "source": "课程自编",
                "tags": "置换算法",
            },
        ],
    },
    "4.1": {
        "resources": [
            {
                "title": "文件物理结构基础：连续、链接、索引",
                "url": "https://en.wikipedia.org/wiki/File_system",
                "type": "link",
                "description": "重点抓住三类物理结构对访问效率和空间管理的影响。",
                "tags": "文件系统,物理结构,基础",
            },
            {
                "title": "磁盘文件组织方式说明",
                "url": "https://www.geeksforgeeks.org/file-allocation-methods/",
                "type": "link",
                "description": "适合复习连续分配、链接分配、索引分配的典型差异。",
                "tags": "分配方式,连续,索引",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：文件组织与磁盘布局",
                "url": "https://book.douban.com/subject/25808895/",
                "type": "book",
                "description": "适合把文件结构与磁盘访问性能联系起来理解。",
                "tags": "文件结构,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "连续分配方式最突出的优点之一是？",
                "options": ["顺序访问和随机访问效率较高", "绝不会产生外部碎片", "无需记录起始块号", "不依赖磁盘"],
                "answer": "A",
                "explanation": "连续分配有较好的访问效率，但可能产生外部碎片。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "连续分配",
            },
            {
                "type": "mcq",
                "prompt": "索引分配方式通常通过什么来记录文件块位置？",
                "options": ["索引块", "打印机缓存", "屏幕坐标", "进程优先级"],
                "answer": "A",
                "explanation": "索引分配通过索引块集中记录数据块位置。",
                "difficulty": 0.35,
                "source": "课程自编",
                "tags": "索引分配",
            },
            {
                "type": "blank",
                "prompt": "链接分配方式中，一个文件的磁盘块通过 _______ 关系串接起来。",
                "options": [],
                "answer": "指针",
                "explanation": "链接分配常通过每块中的指针指向下一块。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "链接分配",
            },
        ],
    },
    "4.2": {
        "resources": [
            {
                "title": "文件系统层次结构概览",
                "url": "https://www.geeksforgeeks.org/file-system-architecture/",
                "type": "link",
                "description": "帮助理解用户接口、文件逻辑、目录管理、设备控制之间的层次关系。",
                "tags": "文件系统,层次结构,概览",
            },
            {
                "title": "Linux 文件系统目录结构参考",
                "url": "https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html",
                "type": "link",
                "description": "用真实系统目录标准去理解抽象的文件系统组织方式。",
                "tags": "Linux,FHS,目录结构",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：文件系统实现原理",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "适合从用户视图、逻辑结构到物理实现三层联动理解。",
                "tags": "文件系统,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "文件系统分层设计的一个直接好处是？",
                "options": ["降低模块间耦合，便于维护和扩展", "永远消除磁盘故障", "完全不需要目录", "不需要用户接口"],
                "answer": "A",
                "explanation": "分层设计通过清晰职责边界提升可维护性和扩展性。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "层次结构,优点",
            },
            {
                "type": "mcq",
                "prompt": "目录管理在文件系统中的作用更接近于？",
                "options": ["组织与定位文件", "为 CPU 提供算术运算", "替代内存管理", "关闭设备中断"],
                "answer": "A",
                "explanation": "目录是文件组织、命名和查找的重要基础。",
                "difficulty": 0.30,
                "source": "课程自编",
                "tags": "目录管理",
            },
            {
                "type": "blank",
                "prompt": "把复杂系统按职责拆成若干层，每层向上提供服务、向下调用接口，这是一种 _______ 设计思想。",
                "options": [],
                "answer": "分层",
                "explanation": "文件系统层次结构本质上体现了分层思想。",
                "difficulty": 0.34,
                "source": "课程自编",
                "tags": "设计思想",
            },
        ],
    },
    "5.1": {
        "resources": [
            {
                "title": "I/O 控制方式导读：程序查询、中断、DMA、通道",
                "url": "https://en.wikipedia.org/wiki/Input/output",
                "type": "link",
                "description": "先理解 I/O 控制从 CPU 亲力亲为到专门硬件协助的演进。",
                "tags": "IO,控制方式,基础",
            },
            {
                "title": "DMA 基础说明",
                "url": "https://en.wikipedia.org/wiki/Direct_memory_access",
                "type": "link",
                "description": "重点理解 DMA 如何减少 CPU 对数据搬运的直接参与。",
                "tags": "DMA,中断,设备管理",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：现代计算机中的 I/O 体系",
                "url": "https://book.douban.com/subject/27162743/",
                "type": "book",
                "description": "适合把控制方式、设备驱动和系统性能结合起来看。",
                "tags": "IO体系,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "下列哪种 I/O 控制方式通常能进一步减轻 CPU 直接搬运数据的负担？",
                "options": ["DMA", "纯程序查询", "手工录入", "单步调试"],
                "answer": "A",
                "explanation": "DMA 允许数据在设备与内存之间直接传输，CPU 只做控制协调。",
                "difficulty": 0.44,
                "source": "课程自编",
                "tags": "DMA,IO控制",
            },
            {
                "type": "mcq",
                "prompt": "与程序查询相比，中断方式的主要优点之一是？",
                "options": ["CPU 不必一直轮询设备状态", "设备完全不需要驱动", "磁盘容量自动扩大", "永远没有上下文切换开销"],
                "answer": "A",
                "explanation": "中断方式能减少 CPU 空转轮询，提高处理器利用率。",
                "difficulty": 0.38,
                "source": "课程自编",
                "tags": "中断,程序查询",
            },
            {
                "type": "blank",
                "prompt": "设备完成一次 I/O 请求后主动通知 CPU 的机制称为 _______。",
                "options": [],
                "answer": "中断",
                "explanation": "中断是设备通知处理器的重要机制。",
                "difficulty": 0.32,
                "source": "课程自编",
                "tags": "中断",
            },
        ],
    },
    "5.2": {
        "resources": [
            {
                "title": "设备分配与回收概念说明",
                "url": "https://en.wikipedia.org/wiki/I/O_scheduling",
                "type": "link",
                "description": "从资源竞争视角理解设备分配、共享与独占策略。",
                "tags": "设备管理,分配,回收",
            },
            {
                "title": "缓冲、假脱机与设备共享思路",
                "url": "https://en.wikipedia.org/wiki/Spooling",
                "type": "link",
                "description": "理解为什么设备管理离不开缓冲和排队机制。",
                "tags": "SPOOLing,共享设备,缓冲",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：设备管理策略与资源竞争",
                "url": "https://book.douban.com/subject/25808895/",
                "type": "book",
                "description": "适合理解独占设备、共享设备与虚拟设备之间的区别。",
                "tags": "设备管理,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "打印机这类设备经常借助什么技术提高共享使用效率？",
                "options": ["假脱机技术", "页表机制", "死锁恢复", "内核裁剪"],
                "answer": "A",
                "explanation": "打印机等慢速设备常借助假脱机技术提升共享效率。",
                "difficulty": 0.42,
                "source": "课程自编",
                "tags": "SPOOLing,设备共享",
            },
            {
                "type": "mcq",
                "prompt": "设备回收的目标之一是？",
                "options": ["及时释放已不再使用的设备资源", "永久锁死设备", "删除所有设备驱动", "让用户手工重装系统"],
                "answer": "A",
                "explanation": "设备回收的核心是释放和复用资源，防止长期占用。",
                "difficulty": 0.32,
                "source": "课程自编",
                "tags": "设备回收",
            },
            {
                "type": "blank",
                "prompt": "把独占设备在逻辑上改造为可顺序共享使用的常见技术叫 _______。",
                "options": [],
                "answer": "假脱机",
                "explanation": "SPOOLing 常用于把独占设备改造为逻辑共享设备。",
                "difficulty": 0.45,
                "source": "课程自编",
                "tags": "SPOOLing",
            },
        ],
    },
    "5.3": {
        "resources": [
            {
                "title": "磁盘调度算法概览：FCFS、SSTF、SCAN、CSCAN",
                "url": "https://www.geeksforgeeks.org/disk-scheduling-algorithms/",
                "type": "link",
                "description": "建议对比各算法在平均寻道长度与公平性上的差异。",
                "tags": "磁盘调度,算法,对比",
            },
            {
                "title": "电梯算法（SCAN）简介",
                "url": "https://en.wikipedia.org/wiki/Elevator_algorithm",
                "type": "link",
                "description": "适合重点理解 SCAN/LOOK 这类算法的直观运动方式。",
                "tags": "SCAN,LOOK,电梯算法",
            },
        ],
        "recommend": [
            {
                "title": "推荐阅读：磁盘访问性能与调度策略",
                "url": "https://book.douban.com/subject/3852290/",
                "type": "book",
                "description": "建议把磁臂移动、旋转延迟和算法设计一起理解。",
                "tags": "磁盘调度,推荐书籍",
            }
        ],
        "questions": [
            {
                "type": "mcq",
                "prompt": "磁盘调度算法设计的一个典型目标是？",
                "options": ["减少平均寻道时间", "提高纸张打印质量", "删除全部中断", "扩大物理内存容量"],
                "answer": "A",
                "explanation": "磁盘调度通常重点优化寻道与访问性能。",
                "difficulty": 0.36,
                "source": "课程自编",
                "tags": "调度目标",
            },
            {
                "type": "mcq",
                "prompt": "SSTF 算法更倾向于优先服务什么请求？",
                "options": ["距离当前磁头最近的请求", "最早到达的请求", "随机请求", "最大柱面号请求"],
                "answer": "A",
                "explanation": "SSTF 即最短寻道时间优先。",
                "difficulty": 0.40,
                "source": "课程自编",
                "tags": "SSTF",
            },
            {
                "type": "blank",
                "prompt": "SCAN 算法因为磁头像电梯一样往返移动，因此常被称为 _______ 算法。",
                "options": [],
                "answer": "电梯",
                "explanation": "SCAN 的中文俗称是电梯算法。",
                "difficulty": 0.28,
                "source": "课程自编",
                "tags": "SCAN",
            },
        ],
    },
}


def _kp_key(kp: KnowledgePoint) -> str:
    return str(kp.code or "").strip()


def _resource_type(value: str) -> ResourceType:
    return ResourceType(value)


def _add_resource(session: Session, *, kp: KnowledgePoint, item: dict[str, str], category: str) -> None:
    resource_type = _resource_type("recommend_book" if category == "recommend" and item["type"] == "book" else item["type"])
    preview_type = "external_link"
    detected_resource_type = "book" if resource_type in {ResourceType.book, ResourceType.recommend_book} else resource_type.value
    row = LearningResource(
        subject=kp.subject,
        grade=kp.grade,
        kp_id=int(kp.id),
        title=item["title"],
        url=item["url"],
        type=resource_type,
        category=category,
        description=item.get("description", ""),
        tags=item.get("tags", ""),
        detected_resource_type=detected_resource_type,
        preview_type=preview_type,
        preview_status="ready",
        source_kind="external",
        original_file_url=item["url"],
        converted_preview_url="",
    )
    session.add(row)


def _add_question(session: Session, *, kp: KnowledgePoint, order: int, item: dict[str, object]) -> None:
    row = Question(
        subject=kp.subject,
        grade=kp.grade,
        kp_id=int(kp.id),
        type=str(item["type"]),
        prompt=str(item["prompt"]),
        options_json=json.dumps(item.get("options", []), ensure_ascii=False),
        answer=str(item["answer"]),
        explanation=str(item.get("explanation", "")),
        difficulty=float(item.get("difficulty", 0.5)),
        source=str(item.get("source", "课程自编")),
        tags=str(item.get("tags", "")),
        version="v2-realistic",
    )
    session.add(row)
    session.flush()
    session.add(
        KpQuestionAssignment(
            kp_id=int(kp.id),
            question_id=int(row.id),
            order=order,
        )
    )


def seed() -> None:
    with Session(engine) as session:
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == "操作系统")
            .order_by(KnowledgePoint.chapter, KnowledgePoint.code)
        ).all()

        kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
        if not kp_ids:
            raise SystemExit("没有找到“操作系统”知识点，未写入任何内容。")

        existing_questions = session.exec(select(Question).where(Question.kp_id.in_(kp_ids))).all()
        question_ids = [int(q.id) for q in existing_questions if q.id is not None]
        if question_ids:
            session.exec(delete(PracticeAttempt).where(PracticeAttempt.question_id.in_(question_ids)))
            session.exec(delete(ReviewSchedule).where(ReviewSchedule.question_id.in_(question_ids)))
            assignments = session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.question_id.in_(question_ids))).all()
            for row in assignments:
                session.delete(row)
            for row in existing_questions:
                session.delete(row)

        existing_resources = session.exec(select(LearningResource).where(LearningResource.kp_id.in_(kp_ids))).all()
        for row in existing_resources:
            session.delete(row)
        session.commit()

        generated = defaultdict(lambda: {"resources": 0, "questions": 0})
        for kp in kps:
            key = _kp_key(kp)
            bundle = OS_RESOURCE_BANK.get(key)
            if not bundle:
                continue
            for item in bundle.get("resources", []):
                _add_resource(session, kp=kp, item=item, category="learning")
                generated[key]["resources"] += 1
            for item in bundle.get("recommend", []):
                _add_resource(session, kp=kp, item=item, category="recommend")
                generated[key]["resources"] += 1
            for index, item in enumerate(bundle.get("questions", []), start=1):
                _add_question(session, kp=kp, order=index, item=item)
                generated[key]["questions"] += 1

        for kp in kps:
            kp.practice_total = max(3, int(generated[_kp_key(kp)]["questions"] or 0))
            session.add(kp)

        session.commit()

        print("已生成操作系统课程内容：")
        for kp in kps:
            key = _kp_key(kp)
            info = generated[key]
            print(f"{kp.code} {kp.title}: 资源 {info['resources']} 条，练习题 {info['questions']} 题")


if __name__ == "__main__":
    seed()
