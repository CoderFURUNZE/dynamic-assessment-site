from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.db.models import (
    Course,
    CourseTeacherActivation,
    KnowledgeEdge,
    KnowledgePoint,
    RelationType,
    TeacherCourseStatus,
    User,
)
from app.db.session import engine

SUBJECT = "高等数学"
GRADE = "通用"
TEACHER_USERNAME = "teacher1"


SECTIONS = [
    {
        "code": "HM-04-01",
        "chapter": "第四章 不定积分",
        "title": "不定积分的概念与性质",
        "description": "理解原函数、不定积分概念、基本积分表与不定积分性质。",
        "x": 120,
        "y": 120,
        "children": [
            ("HM-04-01-01", "原函数与不定积分的概念", "掌握原函数和不定积分的定义及二者关系。"),
            ("HM-04-01-02", "基本积分表", "熟悉常见初等函数的基本积分公式。"),
            ("HM-04-01-03", "不定积分的性质", "掌握线性性质、常数项处理和基本运算规则。"),
        ],
    },
    {
        "code": "HM-04-02",
        "chapter": "第四章 不定积分",
        "title": "换元积分法",
        "description": "掌握第一类换元法和第二类换元法。",
        "x": 360,
        "y": 120,
        "children": [
            ("HM-04-02-01", "第一类换元法", "通过凑微分和复合函数结构完成积分变换。"),
            ("HM-04-02-02", "第二类换元法", "通过变量替换简化根式、三角式等积分。"),
        ],
    },
    {
        "code": "HM-04-03",
        "chapter": "第四章 不定积分",
        "title": "分部积分法",
        "description": "掌握由乘积求导公式导出的分部积分方法。",
        "x": 600,
        "y": 120,
        "children": [
            ("HM-04-03-01", "分部积分法的选择策略", "判断 u 与 dv 的选取，处理乘积型积分。"),
        ],
    },
    {
        "code": "HM-04-04",
        "chapter": "第四章 不定积分",
        "title": "有理函数的积分",
        "description": "掌握有理函数积分及可化为有理函数的积分。",
        "x": 840,
        "y": 120,
        "children": [
            ("HM-04-04-01", "有理函数的积分", "利用部分分式等方法计算有理函数积分。"),
            ("HM-04-04-02", "可化为有理函数的积分举例", "把部分三角、根式或指数形式转化为有理函数积分。"),
        ],
    },
    {
        "code": "HM-04-05",
        "chapter": "第四章 不定积分",
        "title": "积分表的使用",
        "description": "根据结构识别公式并查用积分表。",
        "x": 1080,
        "y": 120,
        "children": [
            ("HM-04-05-01", "积分表查用", "结合换元、分部和标准公式快速查表求积分。"),
        ],
    },
    {
        "code": "HM-05-01",
        "chapter": "第五章 定积分",
        "title": "定积分的概念与性质",
        "description": "理解定积分问题模型、定义、近似计算和性质。",
        "x": 120,
        "y": 360,
        "children": [
            ("HM-05-01-01", "定积分问题举例", "从面积、位移等问题理解定积分建模。"),
            ("HM-05-01-02", "定积分的定义", "理解分割、取点、求和、取极限的定义过程。"),
            ("HM-05-01-03", "定积分的近似计算", "掌握用和式近似定积分的基本思想。"),
            ("HM-05-01-04", "定积分的性质", "掌握线性、区间可加、保号性和估值性质。"),
        ],
    },
    {
        "code": "HM-05-02",
        "chapter": "第五章 定积分",
        "title": "微积分基本公式",
        "description": "理解积分上限函数、牛顿-莱布尼茨公式和微积分基本定理。",
        "x": 360,
        "y": 360,
        "children": [
            ("HM-05-02-01", "位移函数与速度函数的关系", "用变速直线运动理解积分与导数的联系。"),
            ("HM-05-02-02", "积分上限函数及其导数", "掌握变上限积分函数的求导。"),
            ("HM-05-02-03", "牛顿-莱布尼茨公式", "用原函数计算定积分。"),
        ],
    },
    {
        "code": "HM-05-03",
        "chapter": "第五章 定积分",
        "title": "定积分的换元法和分部积分法",
        "description": "把不定积分方法迁移到定积分计算。",
        "x": 600,
        "y": 360,
        "children": [
            ("HM-05-03-01", "定积分的换元法", "处理定积分换元时的上下限同步变化。"),
            ("HM-05-03-02", "定积分的分部积分法", "用分部积分公式计算定积分。"),
        ],
    },
    {
        "code": "HM-05-04",
        "chapter": "第五章 定积分",
        "title": "反常积分",
        "description": "理解无穷限反常积分和无界函数反常积分。",
        "x": 840,
        "y": 360,
        "children": [
            ("HM-05-04-01", "无穷限反常积分", "掌握积分区间无穷时的极限定义。"),
            ("HM-05-04-02", "无界函数的反常积分", "掌握被积函数无界时的极限定义。"),
        ],
    },
    {
        "code": "HM-05-05",
        "chapter": "第五章 定积分",
        "title": "反常积分的审敛法与Γ函数",
        "description": "掌握反常积分审敛法和Γ函数基本形式。",
        "x": 1080,
        "y": 360,
        "children": [
            ("HM-05-05-01", "无穷限反常积分的审敛法", "使用比较、极限比较等方法判断敛散性。"),
            ("HM-05-05-02", "无界函数反常积分的审敛法", "判断瑕积分的敛散性。"),
            ("HM-05-05-03", "Γ函数", "了解Γ函数定义及其与广义积分的联系。"),
        ],
    },
    {
        "code": "HM-06-01",
        "chapter": "第六章 定积分的应用",
        "title": "定积分的元素法",
        "description": "掌握用微元思想建立定积分应用模型。",
        "x": 120,
        "y": 600,
        "children": [
            ("HM-06-01-01", "元素法建模步骤", "确定变量、微元、积分区间和累积表达式。"),
        ],
    },
    {
        "code": "HM-06-02",
        "chapter": "第六章 定积分的应用",
        "title": "定积分在几何学上的应用",
        "description": "用定积分求面积、体积和平面曲线弧长。",
        "x": 420,
        "y": 600,
        "children": [
            ("HM-06-02-01", "平面图形的面积", "建立面积微元并求平面图形面积。"),
            ("HM-06-02-02", "体积", "掌握旋转体体积、截面面积积分等方法。"),
            ("HM-06-02-03", "平面曲线的弧长", "用弧长微元计算曲线长度。"),
        ],
    },
    {
        "code": "HM-06-03",
        "chapter": "第六章 定积分的应用",
        "title": "定积分在物理学上的应用",
        "description": "用定积分求功、水压力和引力。",
        "x": 720,
        "y": 600,
        "children": [
            ("HM-06-03-01", "变力沿直线所作的功", "用功的微元建立定积分模型。"),
            ("HM-06-03-02", "水压力", "用压力微元计算液体静压力。"),
            ("HM-06-03-03", "引力", "用引力微元处理连续分布问题。"),
        ],
    },
    {
        "code": "HM-07-01",
        "chapter": "第七章 微分方程",
        "title": "微分方程的基本概念",
        "description": "理解微分方程、阶、解、通解、特解和初值问题。",
        "x": 120,
        "y": 840,
        "children": [
            ("HM-07-01-01", "微分方程基本概念", "掌握微分方程相关术语和解的含义。"),
        ],
    },
    {
        "code": "HM-07-02",
        "chapter": "第七章 微分方程",
        "title": "可分离变量的微分方程",
        "description": "掌握变量可分离方程的求解。",
        "x": 360,
        "y": 840,
        "children": [
            ("HM-07-02-01", "可分离变量方程求解", "将变量分离后两边积分求解。"),
        ],
    },
    {
        "code": "HM-07-03",
        "chapter": "第七章 微分方程",
        "title": "齐次方程",
        "description": "掌握齐次方程及可化为齐次方程的处理。",
        "x": 600,
        "y": 840,
        "children": [
            ("HM-07-03-01", "齐次方程", "用变量替换把齐次方程转化为可分离变量方程。"),
            ("HM-07-03-02", "可化为齐次的方程", "通过平移或替换化为齐次方程。"),
        ],
    },
    {
        "code": "HM-07-04",
        "chapter": "第七章 微分方程",
        "title": "一阶线性微分方程",
        "description": "掌握一阶线性方程和伯努利方程。",
        "x": 840,
        "y": 840,
        "children": [
            ("HM-07-04-01", "一阶线性方程", "掌握常数变易法或积分因子法。"),
            ("HM-07-04-02", "伯努利方程", "通过变量代换化为一阶线性方程。"),
        ],
    },
    {
        "code": "HM-07-05",
        "chapter": "第七章 微分方程",
        "title": "可降阶的高阶微分方程",
        "description": "掌握三类可降阶高阶微分方程。",
        "x": 1080,
        "y": 840,
        "children": [
            ("HM-07-05-01", "y''=f(x)型微分方程", "连续积分降阶求解。"),
            ("HM-07-05-02", "y''=f(x,y')型微分方程", "令 y'=p 降阶求解。"),
            ("HM-07-05-03", "y''=f(y,y')型微分方程", "令 y'=p(y) 降阶求解。"),
        ],
    },
    {
        "code": "HM-07-06",
        "chapter": "第七章 微分方程",
        "title": "高阶线性微分方程",
        "description": "理解高阶线性微分方程的解结构和常数变易法。",
        "x": 1320,
        "y": 840,
        "children": [
            ("HM-07-06-01", "二阶线性微分方程举例", "认识二阶线性微分方程模型。"),
            ("HM-07-06-02", "线性微分方程解的结构", "掌握齐次解、特解与通解结构。"),
            ("HM-07-06-03", "常数变易法", "用常数变易法求非齐次线性方程特解。"),
        ],
    },
    {
        "code": "HM-07-07",
        "chapter": "第七章 微分方程",
        "title": "常系数齐次线性微分方程",
        "description": "用特征方程求常系数齐次线性微分方程。",
        "x": 1560,
        "y": 840,
        "children": [
            ("HM-07-07-01", "特征方程法", "根据特征根情况写出通解。"),
        ],
    },
    {
        "code": "HM-07-08",
        "chapter": "第七章 微分方程",
        "title": "常系数非齐次线性微分方程",
        "description": "掌握常系数非齐次线性微分方程的待定系数法。",
        "x": 1800,
        "y": 840,
        "children": [
            ("HM-07-08-01", "e^(λx)P_m(x)型", "对指数乘多项式型右端项构造特解。"),
            ("HM-07-08-02", "e^(λx)(P_l(x)cosωx+Q_n(x)sinωx)型", "对指数三角组合型右端项构造特解。"),
        ],
    },
    {
        "code": "HM-07-09",
        "chapter": "第七章 微分方程",
        "title": "欧拉方程",
        "description": "掌握欧拉方程的变量代换求解。",
        "x": 2040,
        "y": 840,
        "children": [
            ("HM-07-09-01", "欧拉方程求解", "通过 x=e^t 等代换转化为常系数方程。"),
        ],
    },
    {
        "code": "HM-07-10",
        "chapter": "第七章 微分方程",
        "title": "常系数线性微分方程组解法举例",
        "description": "了解常系数线性微分方程组的基本求解思路。",
        "x": 2280,
        "y": 840,
        "children": [
            ("HM-07-10-01", "常系数线性微分方程组", "通过消元或矩阵方法求解方程组。"),
        ],
    },
]


SECTION_PREREQS = [
    ("HM-04-01", "HM-04-02"),
    ("HM-04-02", "HM-04-03"),
    ("HM-04-03", "HM-04-04"),
    ("HM-04-04", "HM-04-05"),
    ("HM-04-01", "HM-05-01"),
    ("HM-05-01", "HM-05-02"),
    ("HM-04-02", "HM-05-03"),
    ("HM-04-03", "HM-05-03"),
    ("HM-05-02", "HM-05-03"),
    ("HM-05-03", "HM-05-04"),
    ("HM-05-04", "HM-05-05"),
    ("HM-05-02", "HM-06-01"),
    ("HM-06-01", "HM-06-02"),
    ("HM-06-01", "HM-06-03"),
    ("HM-04-01", "HM-07-01"),
    ("HM-07-01", "HM-07-02"),
    ("HM-07-02", "HM-07-03"),
    ("HM-07-03", "HM-07-04"),
    ("HM-07-04", "HM-07-05"),
    ("HM-07-05", "HM-07-06"),
    ("HM-07-06", "HM-07-07"),
    ("HM-07-07", "HM-07-08"),
    ("HM-07-07", "HM-07-09"),
    ("HM-07-08", "HM-07-10"),
]


def upsert_kp(
    session: Session,
    *,
    code: str,
    title: str,
    description: str,
    chapter: str,
    x: float,
    y: float,
    importance: float,
    difficulty: float,
) -> KnowledgePoint:
    kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if kp is None:
        kp = KnowledgePoint(subject=SUBJECT, grade=GRADE, code=code, title=title)
    kp.subject = SUBJECT
    kp.grade = GRADE
    kp.title = title
    kp.description = description
    kp.chapter = chapter
    kp.knowledge_tag = "高等数学"
    kp.ability_tag = "计算能力,应用建模"
    kp.literacy_tag = "数学抽象,逻辑推理,数学运算"
    kp.importance = importance
    kp.difficulty = difficulty
    kp.pos_x = x
    kp.pos_y = y
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


def add_edge(session: Session, code_map: dict[str, int], source: str, target: str, relation: RelationType) -> bool:
    source_id = code_map[source]
    target_id = code_map[target]
    if source_id == target_id:
        return False
    existing = session.exec(
        select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == source_id, KnowledgeEdge.next_id == target_id)
    ).first()
    if existing is not None:
        existing.subject = SUBJECT
        existing.grade = GRADE
        existing.relation_type = relation
        session.add(existing)
        return False
    session.add(
        KnowledgeEdge(
            subject=SUBJECT,
            grade=GRADE,
            prereq_id=source_id,
            next_id=target_id,
            relation_type=relation,
        )
    )
    return True


def ensure_teacher_access(session: Session) -> None:
    course = session.exec(select(Course).where(Course.title == SUBJECT)).first()
    teacher = session.exec(select(User).where(User.username == TEACHER_USERNAME)).first()
    if course is None or teacher is None or course.id is None or teacher.id is None:
        return
    course.teacher_id = int(teacher.id)
    session.add(course)
    activation = session.exec(
        select(CourseTeacherActivation).where(
            CourseTeacherActivation.course_id == int(course.id),
            CourseTeacherActivation.teacher_id == int(teacher.id),
        )
    ).first()
    if activation is None:
        activation = CourseTeacherActivation(course_id=int(course.id), teacher_id=int(teacher.id))
    activation.teaching_status = TeacherCourseStatus.teaching
    activation.finished_at = None
    session.add(activation)
    session.commit()


def main() -> None:
    with Session(engine) as session:
        ensure_teacher_access(session)
        code_map: dict[str, int] = {}
        created_or_updated = 0

        for section in SECTIONS:
            section_kp = upsert_kp(
                session,
                code=section["code"],
                title=section["title"],
                description=section["description"],
                chapter=section["chapter"],
                x=float(section["x"]),
                y=float(section["y"]),
                importance=0.86,
                difficulty=0.62,
            )
            code_map[section["code"]] = int(section_kp.id)
            created_or_updated += 1
            for idx, (code, title, description) in enumerate(section["children"], start=1):
                child_kp = upsert_kp(
                    session,
                    code=code,
                    title=title,
                    description=description,
                    chapter=section["chapter"],
                    x=float(section["x"]) + (idx - 1) * 90,
                    y=float(section["y"]) + 95,
                    importance=0.76,
                    difficulty=0.58,
                )
                code_map[code] = int(child_kp.id)
                created_or_updated += 1

        edge_count = 0
        for section in SECTIONS:
            parent = section["code"]
            children = [item[0] for item in section["children"]]
            for child in children:
                if add_edge(session, code_map, parent, child, RelationType.contains):
                    edge_count += 1
            for source, target in zip(children, children[1:]):
                if add_edge(session, code_map, source, target, RelationType.prerequisite):
                    edge_count += 1

        for source, target in SECTION_PREREQS:
            if add_edge(session, code_map, source, target, RelationType.prerequisite):
                edge_count += 1

        session.commit()
        kp_total = len(session.exec(select(KnowledgePoint).where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)).all())
        edge_total = len(session.exec(select(KnowledgeEdge).where(KnowledgeEdge.subject == SUBJECT, KnowledgeEdge.grade == GRADE)).all())
        print(f"seeded subject={SUBJECT} grade={GRADE} touched_kps={created_or_updated} new_edges={edge_count} total_kps={kp_total} total_edges={edge_total}")


if __name__ == "__main__":
    main()
