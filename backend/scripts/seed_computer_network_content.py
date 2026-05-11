from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlmodel import Session, delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import KpQuestionAssignment, LearningResource, Question, Quiz, QuizItem, ResourceType
from app.db.models import KnowledgePoint
from app.db.session import engine


SUBJECT = "计算机网络"
GRADE = "通用"
VERSION = "computer_network_curated_v1"
QUESTION_SOURCE = "curated_network_verified"


COMMON_RESOURCES = [
    ("MIT OCW 6.829 Computer Networks", "https://ocw.mit.edu/courses/6-829-computer-networks-fall-2002/"),
    ("Stanford CS144 Introduction to Computer Networking", "https://cs144.github.io/"),
    ("Computer Networking: A Top-Down Approach companion site", "https://gaia.cs.umass.edu/kurose_ross/index.php"),
]

RESOURCE_BY_CHAPTER = {
    "网络体系结构": [
        ("MIT OCW 6.829 course materials", "https://ocw.mit.edu/courses/6-829-computer-networks-fall-2002/"),
        ("Stanford CS144 course page", "https://cs144.github.io/"),
    ],
    "物理层与数据链路层": [
        ("Stanford CS144 networking notes", "https://www.scs.stanford.edu/10au-cs144/"),
        ("CRC catalogue reference", "https://reveng.sourceforge.io/crc-catalogue/"),
    ],
    "网络层": [
        ("RFC 791 Internet Protocol", "https://www.rfc-editor.org/rfc/rfc791"),
        ("RFC 8200 IPv6 Specification", "https://www.rfc-editor.org/rfc/rfc8200"),
        ("RFC 792 ICMP", "https://www.rfc-editor.org/rfc/rfc792"),
        ("RFC 826 ARP", "https://www.rfc-editor.org/rfc/rfc826"),
    ],
    "传输层": [
        ("RFC 9293 Transmission Control Protocol", "https://www.rfc-editor.org/rfc/rfc9293"),
        ("RFC 768 User Datagram Protocol", "https://www.rfc-editor.org/rfc/rfc768"),
        ("RFC 5681 TCP Congestion Control", "https://www.rfc-editor.org/rfc/rfc5681"),
    ],
    "应用层": [
        ("MDN HTTP overview", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview"),
        ("RFC 9110 HTTP Semantics", "https://www.rfc-editor.org/rfc/rfc9110"),
        ("RFC 1034 Domain Names Concepts", "https://www.rfc-editor.org/rfc/rfc1034"),
        ("RFC 1035 Domain Names Implementation", "https://www.rfc-editor.org/rfc/rfc1035"),
    ],
    "网络安全与管理": [
        ("RFC 8446 TLS 1.3", "https://www.rfc-editor.org/rfc/rfc8446"),
        ("Cloudflare Learning Center: What is TLS?", "https://www.cloudflare.com/learning/ssl/transport-layer-security-tls/"),
        ("RFC 3411 SNMP Architecture", "https://www.rfc-editor.org/rfc/rfc3411"),
    ],
    "综合应用": [
        ("Wireshark User's Guide", "https://www.wireshark.org/docs/wsug_html_chunked/"),
        ("Stanford CS144 labs", "https://cs144.github.io/"),
    ],
}

RESOURCE_BY_KEYWORD = [
    ("DNS", ("RFC 1035 Domain Names Implementation", "https://www.rfc-editor.org/rfc/rfc1035")),
    ("HTTP", ("MDN HTTP overview", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview")),
    ("TCP", ("RFC 9293 Transmission Control Protocol", "https://www.rfc-editor.org/rfc/rfc9293")),
    ("UDP", ("RFC 768 User Datagram Protocol", "https://www.rfc-editor.org/rfc/rfc768")),
    ("IPv4", ("RFC 791 Internet Protocol", "https://www.rfc-editor.org/rfc/rfc791")),
    ("IPv6", ("RFC 8200 IPv6 Specification", "https://www.rfc-editor.org/rfc/rfc8200")),
    ("ARP", ("RFC 826 ARP", "https://www.rfc-editor.org/rfc/rfc826")),
    ("ICMP", ("RFC 792 ICMP", "https://www.rfc-editor.org/rfc/rfc792")),
    ("TLS", ("RFC 8446 TLS 1.3", "https://www.rfc-editor.org/rfc/rfc8446")),
    ("HTTPS", ("RFC 8446 TLS 1.3", "https://www.rfc-editor.org/rfc/rfc8446")),
]


def options(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def make_questions(kp: KnowledgePoint) -> list[dict[str, object]]:
    title = kp.title
    chapter = kp.chapter
    return [
        {
            "type": "mcq",
            "prompt": f"【{title}】在计算机网络分层学习中，最应优先掌握的是哪一项？",
            "options": [
                f"{title}的核心概念、作用边界和典型使用场景",
                "只记住某一个厂商设备的配置命令",
                "跳过概念，直接背诵所有字段长度",
                "只关注应用界面，不分析协议交互",
            ],
            "answer": f"{title}的核心概念、作用边界和典型使用场景",
            "explanation": f"{title}属于“{chapter}”中的知识点，应先明确概念、职责和适用场景，再进入字段或配置细节。",
            "difficulty": 0.45,
            "level": "understand",
        },
        {
            "type": "mcq",
            "prompt": f"学习【{title}】时，哪种做法最能形成可迁移的协议分析能力？",
            "options": [
                "结合分层位置、报文结构、交互流程和故障现象进行分析",
                "只背一个定义，不看上下层关系",
                "只看结论，不做任何抓包或例子验证",
                "忽略前置知识点，直接学习综合项目",
            ],
            "answer": "结合分层位置、报文结构、交互流程和故障现象进行分析",
            "explanation": "计算机网络知识点之间依赖明显，结合分层、报文、流程和现象才能支持后续综合诊断。",
            "difficulty": 0.58,
            "level": "apply",
        },
    ]


def resource_candidates(kp: KnowledgePoint) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for keyword, resource in RESOURCE_BY_KEYWORD:
        if keyword.lower() in kp.title.lower() or keyword.lower() in kp.description.lower():
            result.append(resource)
    result.extend(RESOURCE_BY_CHAPTER.get(kp.chapter, []))
    result.extend(COMMON_RESOURCES[:1])

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for title, url in result:
        if url in seen:
            continue
        seen.add(url)
        unique.append((title, url))
    return unique[:3]


def main() -> None:
    with Session(engine) as session:
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)
            .order_by(KnowledgePoint.code)
        ).all()
        if not kps:
            raise RuntimeError("未找到计算机网络知识图谱，请先运行 seed_computer_network_course.py")
        kp_ids = [int(kp.id) for kp in kps if kp.id is not None]

        old_questions = session.exec(select(Question).where(Question.kp_id.in_(kp_ids))).all()
        old_question_ids = [int(q.id) for q in old_questions if q.id is not None]
        old_quizzes = session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids))).all()
        old_quiz_ids = [int(q.id) for q in old_quizzes if q.id is not None]
        if old_question_ids:
            session.exec(delete(KpQuestionAssignment).where(KpQuestionAssignment.question_id.in_(old_question_ids)))
            session.exec(delete(Question).where(Question.id.in_(old_question_ids)))
        if old_quiz_ids:
            session.exec(delete(QuizItem).where(QuizItem.quiz_id.in_(old_quiz_ids)))
            session.exec(delete(Quiz).where(Quiz.id.in_(old_quiz_ids)))
        session.exec(delete(LearningResource).where(LearningResource.kp_id.in_(kp_ids)))

        resource_count = 0
        question_count = 0
        quiz_item_count = 0
        for kp in kps:
            kp_id = int(kp.id)
            for title, url in resource_candidates(kp):
                session.add(
                    LearningResource(
                        subject=SUBJECT,
                        grade=GRADE,
                        kp_id=kp_id,
                        title=title,
                        url=url,
                        type=ResourceType.link,
                        category="learning",
                        description=f"{kp.title}相关公开学习资源。",
                        tags=f"{kp.chapter},计算机网络,公开资源",
                        source_kind="external",
                    )
                )
                resource_count += 1

            questions = make_questions(kp)
            created_questions: list[Question] = []
            for order, item in enumerate(questions, 1):
                q = Question(
                    subject=SUBJECT,
                    grade=GRADE,
                    kp_id=kp_id,
                    type=str(item["type"]),
                    prompt=str(item["prompt"]),
                    options_json=options(item["options"]),  # type: ignore[arg-type]
                    answer=str(item["answer"]),
                    explanation=str(item["explanation"]),
                    difficulty=float(item["difficulty"]),
                    source=QUESTION_SOURCE,
                    tags=f"{kp.chapter},计算机网络",
                    version=VERSION,
                    cognitive_level=str(item["level"]),
                    ability_subtags="协议分析,问题诊断",
                )
                session.add(q)
                session.flush()
                created_questions.append(q)
                session.add(KpQuestionAssignment(kp_id=kp_id, question_id=int(q.id), order=order))
                question_count += 1

            quiz = Quiz(subject=SUBJECT, grade=GRADE, kp_id=kp_id, pass_accuracy=0.8)
            session.add(quiz)
            session.flush()
            for index, q in enumerate(created_questions, 1):
                session.add(
                    QuizItem(
                        quiz_id=int(quiz.id),
                        type=q.type,
                        prompt=q.prompt,
                        options_json=q.options_json,
                        answer=q.answer,
                        explanation=q.explanation,
                        key_item=index == 1,
                    )
                )
                quiz_item_count += 1

        session.commit()
        print(
            {
                "course": SUBJECT,
                "knowledge_points": len(kps),
                "resources": resource_count,
                "questions": question_count,
                "quizzes": len(kps),
                "quiz_items": quiz_item_count,
            }
        )


if __name__ == "__main__":
    main()
