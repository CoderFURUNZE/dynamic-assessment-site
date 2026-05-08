from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import (  # noqa: E402
    Course,
    CourseLifecycleStatus,
    CourseTeacherActivation,
    KpQuestionAssignment,
    KnowledgeEdge,
    KnowledgePoint,
    LearningResource,
    Question,
    Quiz,
    QuizItem,
    RelationType,
    ResourceType,
    TeacherCourseStatus,
    User,
)
from app.db.session import engine, init_db  # noqa: E402


SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM-VERIFIED-CALCULUS"
TEACHER_USERNAME = "teacher1"
SOURCE_TAG = "verified_high_math_pack_2026"


# External resources are public course/textbook pages. They are not mirrored.
# Keep URLs empty rather than inventing a source when no reliable source is available.
RESOURCE_SETS: dict[str, list[dict[str, str]]] = {
    "functions": [
        {"title": "OpenStax Calculus Volume 1: Functions and Graphs", "url": "https://openstax.org/books/calculus-volume-1/pages/1-introduction"},
        {"title": "MIT OCW 18.01SC Single Variable Calculus", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/"},
        {"title": "Paul's Online Math Notes: Functions", "url": "https://tutorial.math.lamar.edu/Classes/Alg/Functions.aspx"},
    ],
    "limits": [
        {"title": "OpenStax Calculus Volume 1: Limits", "url": "https://openstax.org/books/calculus-volume-1/pages/2-introduction"},
        {"title": "Paul's Online Math Notes: Limits", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/LimitsIntro.aspx"},
        {"title": "Khan Academy Calculus 1", "url": "https://www.khanacademy.org/math/calculus-1"},
    ],
    "continuity": [
        {"title": "OpenStax Calculus Volume 1: Continuity", "url": "https://openstax.org/books/calculus-volume-1/pages/2-4-continuity"},
        {"title": "Paul's Online Math Notes: Continuity", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/Continuity.aspx"},
        {"title": "MIT OCW 18.01SC Single Variable Calculus", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/"},
    ],
    "derivatives": [
        {"title": "OpenStax Calculus Volume 1: Derivatives", "url": "https://openstax.org/books/calculus-volume-1/pages/3-introduction"},
        {"title": "Paul's Online Math Notes: Derivatives", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeIntro.aspx"},
        {"title": "Khan Academy Calculus 1: Derivatives", "url": "https://www.khanacademy.org/math/calculus-1/cs1-derivatives-definition-and-basic-rules"},
    ],
    "derivative_applications": [
        {"title": "OpenStax Calculus Volume 1: Applications of Derivatives", "url": "https://openstax.org/books/calculus-volume-1/pages/4-introduction"},
        {"title": "Paul's Online Math Notes: Applications of Derivatives", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeAppsIntro.aspx"},
        {"title": "MIT OCW 18.01SC Applications of Differentiation", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/pages/unit-2-applications-of-differentiation/"},
    ],
    "integrals": [
        {"title": "OpenStax Calculus Volume 1: Integration", "url": "https://openstax.org/books/calculus-volume-1/pages/5-introduction"},
        {"title": "Paul's Online Math Notes: Integrals", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/IntegralsIntro.aspx"},
        {"title": "MIT OCW 18.01SC Integration", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/pages/unit-3-the-definite-integral-and-its-applications/"},
    ],
    "integration_techniques": [
        {"title": "OpenStax Calculus Volume 2: Techniques of Integration", "url": "https://openstax.org/books/calculus-volume-2/pages/3-introduction"},
        {"title": "Paul's Online Math Notes: Integration Techniques", "url": "https://tutorial.math.lamar.edu/Classes/CalcII/IntegrationTechniques.aspx"},
        {"title": "Khan Academy Calculus 2", "url": "https://www.khanacademy.org/math/calculus-2"},
    ],
    "integral_applications": [
        {"title": "OpenStax Calculus Volume 1: Applications of Integration", "url": "https://openstax.org/books/calculus-volume-1/pages/6-introduction"},
        {"title": "Paul's Online Math Notes: Applications of Integrals", "url": "https://tutorial.math.lamar.edu/Classes/CalcI/ApplicationsIntegralsIntro.aspx"},
        {"title": "MIT OCW 18.01SC Applications of Integration", "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/pages/unit-3-the-definite-integral-and-its-applications/"},
    ],
    "series": [
        {"title": "OpenStax Calculus Volume 2: Sequences and Series", "url": "https://openstax.org/books/calculus-volume-2/pages/5-introduction"},
        {"title": "Paul's Online Math Notes: Series", "url": "https://tutorial.math.lamar.edu/Classes/CalcII/SeriesIntro.aspx"},
        {"title": "Khan Academy Calculus 2: Series", "url": "https://www.khanacademy.org/math/calculus-2/cs2-series"},
    ],
    "multivariable": [
        {"title": "OpenStax Calculus Volume 3", "url": "https://openstax.org/details/books/calculus-volume-3"},
        {"title": "MIT OCW 18.02SC Multivariable Calculus", "url": "https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/"},
        {"title": "Khan Academy Multivariable Calculus", "url": "https://www.khanacademy.org/math/multivariable-calculus"},
    ],
    "differential_equations": [
        {"title": "OpenStax Calculus Volume 2: Introduction to Differential Equations", "url": "https://openstax.org/books/calculus-volume-2/pages/4-introduction"},
        {"title": "MIT OCW 18.03 Differential Equations", "url": "https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/"},
        {"title": "Paul's Online Math Notes: Differential Equations", "url": "https://tutorial.math.lamar.edu/Classes/DE/DE.aspx"},
    ],
}


CHAPTERS = [
    (
        "HM-V01",
        "函数、极限与连续",
        "functions",
        [
            ("01", "集合、映射与函数", "理解集合、映射、函数定义、定义域、值域、复合函数与反函数。"),
            ("02", "初等函数与函数性质", "掌握基本初等函数、奇偶性、单调性、周期性、有界性和反函数。"),
            ("03", "数列极限", "理解数列极限的 epsilon-N 定义、收敛性质与常见极限。"),
            ("04", "函数极限", "掌握一点处、无穷远处、左右极限以及函数极限运算法则。"),
            ("05", "无穷小与无穷大", "理解无穷小、无穷大、等价无穷小和阶的比较。"),
            ("06", "两个重要极限", "掌握 sin x / x 与 (1+1/x)^x 型重要极限及其应用。"),
            ("07", "函数连续性", "掌握连续定义、间断点分类、初等函数连续性。"),
            ("08", "闭区间连续函数性质", "掌握有界性、最值定理、介值定理和零点定理。"),
        ],
    ),
    (
        "HM-V02",
        "导数与微分",
        "derivatives",
        [
            ("01", "导数概念", "理解变化率、切线斜率、导数定义以及可导与连续的关系。"),
            ("02", "基本求导法则", "掌握四则运算、复合函数、反函数和基本初等函数求导。"),
            ("03", "高阶导数", "掌握二阶及高阶导数的定义、记号和计算。"),
            ("04", "隐函数与参数方程求导", "掌握隐函数求导、参数方程求导及相关变化率。"),
            ("05", "函数微分", "理解微分定义、线性主部、微分形式不变性和近似计算。"),
        ],
    ),
    (
        "HM-V03",
        "微分中值定理与导数应用",
        "derivative_applications",
        [
            ("01", "罗尔定理", "掌握罗尔定理条件、结论和几何意义。"),
            ("02", "拉格朗日中值定理", "掌握拉格朗日中值定理及函数增量估计。"),
            ("03", "柯西中值定理", "掌握柯西中值定理及其与洛必达法则的联系。"),
            ("04", "洛必达法则", "掌握 0/0、∞/∞ 型未定式及其他可转化未定式。"),
            ("05", "单调性与极值", "用一阶导数判断单调性、极值和函数最值。"),
            ("06", "凹凸性、拐点与函数作图", "用二阶导数判断凹凸性、拐点和图形趋势。"),
            ("07", "曲率", "理解曲率、曲率半径及平面曲线弯曲程度。"),
            ("08", "优化问题", "建立实际问题目标函数并用导数求最优值。"),
        ],
    ),
    (
        "HM-V04",
        "不定积分",
        "integrals",
        [
            ("01", "原函数与不定积分", "理解原函数、不定积分定义、线性性质和积分常数。"),
            ("02", "基本积分公式", "掌握幂函数、指数、对数、三角函数的基本积分公式。"),
            ("03", "第一类换元积分法", "掌握凑微分与变量代换思想。"),
            ("04", "第二类换元积分法", "掌握三角代换、根式代换等变量替换方法。"),
            ("05", "分部积分法", "掌握分部积分公式及函数类型选择策略。"),
            ("06", "有理函数积分", "掌握部分分式分解和有理函数积分。"),
        ],
    ),
    (
        "HM-V05",
        "定积分及其应用",
        "integral_applications",
        [
            ("01", "定积分概念", "理解分割、取样、求和、取极限的黎曼积分思想。"),
            ("02", "定积分性质", "掌握线性、区间可加性、保号性、估值性质和积分中值定理。"),
            ("03", "微积分基本定理", "掌握变上限积分函数和牛顿-莱布尼茨公式。"),
            ("04", "定积分换元与分部积分", "掌握定积分中的换元和分部积分公式。"),
            ("05", "反常积分", "掌握无穷区间和无界函数反常积分的收敛判别。"),
            ("06", "平面图形面积", "用定积分计算直角坐标、参数方程和极坐标下的面积。"),
            ("07", "体积与弧长", "掌握旋转体体积、截面法体积和弧长公式。"),
            ("08", "物理应用", "用定积分建立变力做功、液体压力和平均值模型。"),
        ],
    ),
    (
        "HM-V06",
        "常微分方程",
        "differential_equations",
        [
            ("01", "微分方程基本概念", "理解微分方程阶数、解、通解、特解和初值问题。"),
            ("02", "可分离变量方程", "掌握可分离变量方程的分离、积分和初值求解。"),
            ("03", "一阶线性微分方程", "掌握积分因子法和常数变易法。"),
            ("04", "可降阶高阶方程", "识别 y''=f(x)、y''=f(x,y') 等可降阶类型。"),
            ("05", "二阶常系数齐次线性方程", "用特征方程求二阶常系数齐次线性方程。"),
            ("06", "二阶常系数非齐次线性方程", "掌握待定系数法和特解结构。"),
        ],
    ),
    (
        "HM-V07",
        "无穷级数",
        "series",
        [
            ("01", "常数项级数", "理解级数收敛、部分和、必要条件和基本性质。"),
            ("02", "正项级数判别法", "掌握比较、比值、根值和积分判别法。"),
            ("03", "任意项级数", "掌握交错级数、绝对收敛和条件收敛。"),
            ("04", "幂级数", "掌握收敛半径、收敛区间和幂级数运算。"),
            ("05", "泰勒级数", "掌握泰勒公式、麦克劳林展开和常用函数展开。"),
            ("06", "傅里叶级数基础", "理解三角级数、正交性和周期函数展开思想。"),
        ],
    ),
    (
        "HM-V08",
        "空间解析几何与向量代数",
        "multivariable",
        [
            ("01", "空间直角坐标系与向量", "掌握空间点、向量、模、方向角和方向余弦。"),
            ("02", "向量数量积与向量积", "掌握点积、叉积及其几何意义。"),
            ("03", "平面与直线", "掌握平面方程、空间直线方程和位置关系。"),
            ("04", "曲面与空间曲线", "识别二次曲面、柱面、旋转曲面和空间曲线投影。"),
        ],
    ),
    (
        "HM-V09",
        "多元函数微分法",
        "multivariable",
        [
            ("01", "多元函数概念、极限与连续", "理解多元函数定义域、极限、连续性和几何图形。"),
            ("02", "偏导数", "掌握一阶和高阶偏导数的定义与计算。"),
            ("03", "全微分", "理解可微、全微分、连续偏导与可微的关系。"),
            ("04", "多元复合函数求导", "掌握链式法则和全导数计算。"),
            ("05", "隐函数求导", "掌握一个方程或方程组确定隐函数的求导。"),
            ("06", "方向导数与梯度", "掌握方向导数、梯度及最大方向变化率。"),
            ("07", "多元函数极值", "掌握无条件极值、条件极值和拉格朗日乘数法。"),
        ],
    ),
    (
        "HM-V10",
        "重积分与曲线曲面积分",
        "multivariable",
        [
            ("01", "二重积分概念与性质", "理解二重积分定义、几何意义和基本性质。"),
            ("02", "直角坐标下二重积分", "掌握 X 型、Y 型区域的累次积分计算。"),
            ("03", "极坐标下二重积分", "掌握极坐标变换和面积元素。"),
            ("04", "三重积分", "掌握直角坐标、柱面坐标和球面坐标下的三重积分。"),
            ("05", "第一类曲线积分", "理解对弧长的曲线积分及其物理意义。"),
            ("06", "第二类曲线积分", "理解对坐标的曲线积分、方向性和格林公式基础。"),
            ("07", "第一类曲面积分", "掌握对面积的曲面积分和曲面面积元素。"),
            ("08", "第二类曲面积分", "理解通量、曲面方向和高斯公式基础。"),
        ],
    ),
    (
        "HM-V11",
        "综合达标",
        "functions",
        [
            ("01", "高等数学综合建模", "综合使用极限、导数、积分、多元函数和微分方程建立模型。"),
            ("02", "高等数学课程达标", "完成核心概念、运算能力、应用建模和证明意识的综合达标。"),
        ],
    ),
]


BASE_QUESTIONS = {
    "functions": [
        ("blank", "求函数 f(x)=sqrt(x-1)/(x+2) 的定义域。", "x>=1", [], "根式要求 x-1>=0，且 x+2 在 x>=1 时不为 0。"),
        ("mcq", "若 f(x)=2x-1, g(x)=x^2，则 (f∘g)(3) 等于多少？", "17", ["5", "8", "17", "36"], "先算 g(3)=9，再算 f(9)=17。"),
    ],
    "limits": [
        ("blank", "计算极限 lim_{x->2} (x^2-4)/(x-2)。", "4", [], "因式分解后约去 x-2，代入 x=2 得 4。"),
        ("mcq", "lim_{x->0} sin x / x 的值是？", "1", ["0", "1", "不存在", "+∞"], "这是第一重要极限。"),
    ],
    "continuity": [
        ("mcq", "函数在 x=a 连续需要满足哪一项？", "极限存在且等于函数值", ["函数值存在即可", "极限存在且等于函数值", "左极限存在即可", "函数必须单调"], "连续要求 f(a) 存在、极限存在并等于 f(a)。"),
        ("blank", "f(x)=1/x 在 x=0 处的间断点类型是？", "无穷间断点", [], "x 趋近 0 时函数值无界。"),
    ],
    "derivatives": [
        ("blank", "求 y=x^3-2x 的导数。", "3x^2-2", [], "幂函数逐项求导。"),
        ("mcq", "若 y=sin x，则 y' 等于？", "cos x", ["sin x", "cos x", "-sin x", "-cos x"], "正弦函数导数为余弦函数。"),
    ],
    "derivative_applications": [
        ("mcq", "若 f'(x)>0 在区间内恒成立，则 f 在该区间上？", "单调增加", ["单调增加", "单调减少", "恒为 0", "不连续"], "一阶导数为正表示函数单调增加。"),
        ("blank", "函数 f(x)=x^2 在 x=0 处取得什么类型的极值？", "极小值", [], "f'(0)=0 且二阶导数 2>0。"),
    ],
    "integrals": [
        ("blank", "计算不定积分 ∫2x dx。", "x^2+C", [], "x^2 的导数为 2x。"),
        ("mcq", "∫cos x dx 等于？", "sin x+C", ["sin x+C", "-sin x+C", "cos x+C", "-cos x+C"], "sin x 的导数为 cos x。"),
    ],
    "integration_techniques": [
        ("blank", "用分部积分计算 ∫x e^x dx。", "x e^x-e^x+C", [], "取 u=x, dv=e^x dx。"),
        ("mcq", "积分 ∫2x cos(x^2) dx 适合优先使用？", "换元法", ["分部积分法", "换元法", "部分分式法", "比较判别法"], "令 u=x^2。"),
    ],
    "integral_applications": [
        ("blank", "曲线 y=x 与 x 轴在 [0,1] 围成面积是多少？", "1/2", [], "面积为 ∫_0^1 x dx=1/2。"),
        ("mcq", "旋转体体积的圆盘法常见形式是？", "π∫[a,b] f(x)^2 dx", ["∫f(x)dx", "π∫[a,b] f(x)^2 dx", "2π∫f(x)dx", "∫sqrt(1+f'(x)^2)dx"], "圆盘截面积为 πr^2。"),
    ],
    "differential_equations": [
        ("blank", "求微分方程 dy/dx=2x 的通解。", "y=x^2+C", [], "两边对 x 积分。"),
        ("mcq", "方程 y'+y=0 的通解是？", "Ce^{-x}", ["Ce^x", "Ce^{-x}", "x+C", "C sin x"], "分离变量 dy/y=-dx。"),
    ],
    "series": [
        ("mcq", "几何级数 ∑ r^n 收敛的条件是？", "|r|<1", ["|r|<1", "|r|>1", "r=1", "任意 r"], "几何级数收敛当且仅当公比绝对值小于 1。"),
        ("blank", "函数 e^x 在 x=0 处的麦克劳林展开首三项是？", "1+x+x^2/2", [], "e^x=1+x+x^2/2!+...。"),
    ],
    "multivariable": [
        ("blank", "求 f(x,y)=x^2y+y^3 对 x 的偏导数。", "2xy", [], "对 x 求导时把 y 视为常数。"),
        ("mcq", "二重积分在极坐标变换中面积元素 dxdy 等于？", "r dr dθ", ["dr dθ", "r dr dθ", "r^2 dr dθ", "dx dy"], "极坐标雅可比为 r。"),
    ],
}


def ensure_course(session: Session) -> None:
    course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
    if course is None:
        course = Course(
            code=COURSE_CODE,
            title=SUBJECT,
            description="高等数学完整知识图谱包：数据来源可追溯，资源使用公开课程/教材链接，习题为公式校验型原创题。",
            active=True,
            lifecycle_status=CourseLifecycleStatus.active,
            target_class="毕业答辩演示班",
            max_students=300,
            start_at=datetime.utcnow() - timedelta(days=1),
            end_at=datetime.utcnow() + timedelta(days=365),
        )
        session.add(course)
        session.commit()
        session.refresh(course)
    else:
        course.title = SUBJECT
        course.description = "高等数学完整知识图谱包：数据来源可追溯，资源使用公开课程/教材链接，习题为公式校验型原创题。"
        course.active = True
        course.lifecycle_status = CourseLifecycleStatus.active
        session.add(course)
        session.commit()

    teacher = session.exec(select(User).where(User.username == TEACHER_USERNAME)).first()
    if teacher and course.id is not None:
        exists = session.exec(
            select(CourseTeacherActivation).where(
                CourseTeacherActivation.course_id == int(course.id),
                CourseTeacherActivation.teacher_id == int(teacher.id),
            )
        ).first()
        if exists is None:
            session.add(
                CourseTeacherActivation(
                    course_id=int(course.id),
                    teacher_id=int(teacher.id),
                    teaching_status=TeacherCourseStatus.teaching,
                )
            )
            session.commit()


def ensure_kp(session: Session, *, code: str, title: str, chapter: str, desc: str, key: str, x: float, y: float, terminal: bool = False) -> KnowledgePoint:
    kp = session.exec(select(KnowledgePoint).where(KnowledgePoint.code == code)).first()
    if kp is None:
        kp = KnowledgePoint(subject=SUBJECT, grade=GRADE, code=code, title=title)
    kp.subject = SUBJECT
    kp.grade = GRADE
    kp.title = title
    kp.chapter = chapter
    kp.description = desc
    kp.knowledge_tag = chapter
    kp.ability_tag = key
    kp.literacy_tag = "数学抽象,逻辑推理,数学建模"
    kp.importance = 0.86 if terminal else 0.72
    kp.difficulty = 0.55
    kp.pos_x = x
    kp.pos_y = y
    kp.practice_total = 2
    kp.is_terminal = terminal
    session.add(kp)
    session.commit()
    session.refresh(kp)
    return kp


def ensure_edge(session: Session, a: KnowledgePoint, b: KnowledgePoint) -> None:
    if a.id is None or b.id is None:
        return
    exists = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.prereq_id == int(a.id), KnowledgeEdge.next_id == int(b.id))).first()
    if exists is None:
        session.add(KnowledgeEdge(subject=SUBJECT, grade=GRADE, prereq_id=int(a.id), next_id=int(b.id), relation_type=RelationType.prerequisite))
        session.commit()


def ensure_resource(session: Session, kp: KnowledgePoint, key: str) -> None:
    if kp.id is None:
        return
    for item in RESOURCE_SETS.get(key, []):
        if not item.get("url"):
            continue
        exists = session.exec(select(LearningResource).where(LearningResource.kp_id == int(kp.id), LearningResource.title == item["title"])).first()
        if exists is None:
            exists = LearningResource(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), title=item["title"], url=item["url"])
        exists.type = ResourceType.link
        exists.category = "verified_open_resource"
        exists.description = f"公开可核验资源；用于支撑知识点：{kp.title}。"
        exists.tags = SOURCE_TAG
        exists.source_kind = "external_verified"
        session.add(exists)
    session.commit()


def ensure_questions(session: Session, kp: KnowledgePoint, key: str) -> None:
    if kp.id is None:
        return
    for order, (qtype, prompt, answer, options, explanation) in enumerate(BASE_QUESTIONS.get(key, []), start=1):
        full_prompt = f"【{kp.title}】{prompt}"
        q = session.exec(select(Question).where(Question.kp_id == int(kp.id), Question.prompt == full_prompt)).first()
        if q is None:
            q = Question(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), type=qtype, prompt=full_prompt, answer=answer)
        q.options_json = json.dumps(options, ensure_ascii=False)
        q.explanation = explanation
        q.difficulty = 0.45
        q.source = "curated_formula_verified"
        q.tags = SOURCE_TAG
        q.version = "verified-high-math-2026"
        q.cognitive_level = "apply"
        q.ability_subtags = key
        session.add(q)
        session.commit()
        session.refresh(q)
        exists = session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == int(kp.id), KpQuestionAssignment.question_id == int(q.id))).first()
        if exists is None:
            session.add(KpQuestionAssignment(kp_id=int(kp.id), question_id=int(q.id), order=order))
            session.commit()


def ensure_quiz(session: Session, kp: KnowledgePoint, key: str) -> None:
    if kp.id is None:
        return
    quiz = session.exec(select(Quiz).where(Quiz.kp_id == int(kp.id))).first()
    if quiz is None:
        quiz = Quiz(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), pass_accuracy=0.8)
        session.add(quiz)
        session.commit()
        session.refresh(quiz)
    for qtype, prompt, answer, options, explanation in BASE_QUESTIONS.get(key, [])[:2]:
        full_prompt = f"【小测-{kp.title}】{prompt}"
        item = session.exec(select(QuizItem).where(QuizItem.quiz_id == int(quiz.id), QuizItem.prompt == full_prompt)).first()
        if item is None:
            item = QuizItem(quiz_id=int(quiz.id), type=qtype, prompt=full_prompt, answer=answer)
        item.options_json = json.dumps(options, ensure_ascii=False)
        item.explanation = explanation
        item.key_item = True
        session.add(item)
    session.commit()


def seed() -> None:
    init_db()
    with Session(engine) as session:
        ensure_course(session)
        by_code: dict[str, KnowledgePoint] = {}
        previous_leaf: KnowledgePoint | None = None
        chapter_heads: list[KnowledgePoint] = []
        for chapter_index, (prefix, chapter, default_key, items) in enumerate(CHAPTERS, start=1):
            chapter_previous: KnowledgePoint | None = None
            for item_index, (suffix, title, desc) in enumerate(items, start=1):
                code = f"{prefix}-{suffix}"
                key = "continuity" if "连续" in title else "limits" if "极限" in title or "无穷" in title else default_key
                if "不定积分" in chapter and ("换元" in title or "分部" in title or "有理" in title):
                    key = "integration_techniques"
                if "定积分" in chapter:
                    key = "integral_applications"
                terminal = prefix == "HM-V11" and suffix == "02"
                kp = ensure_kp(
                    session,
                    code=code,
                    title=title,
                    chapter=chapter,
                    desc=desc,
                    key=key,
                    x=160 + (item_index - 1) * 220,
                    y=chapter_index * 170,
                    terminal=terminal,
                )
                by_code[code] = kp
                if item_index == 1:
                    chapter_heads.append(kp)
                    if previous_leaf is not None:
                        ensure_edge(session, previous_leaf, kp)
                if chapter_previous is not None:
                    ensure_edge(session, chapter_previous, kp)
                chapter_previous = kp
                previous_leaf = kp
                ensure_resource(session, kp, key)
                ensure_questions(session, kp, key)
                ensure_quiz(session, kp, key)

        extra_edges = [
            ("HM-V01-04", "HM-V02-01"),
            ("HM-V01-07", "HM-V02-01"),
            ("HM-V02-02", "HM-V03-01"),
            ("HM-V03-05", "HM-V05-06"),
            ("HM-V04-03", "HM-V05-04"),
            ("HM-V05-03", "HM-V06-02"),
            ("HM-V05-05", "HM-V07-02"),
            ("HM-V08-02", "HM-V09-06"),
            ("HM-V09-03", "HM-V10-01"),
            ("HM-V10-08", "HM-V11-01"),
        ]
        for a, b in extra_edges:
            if a in by_code and b in by_code:
                ensure_edge(session, by_code[a], by_code[b])

        print(f"Seeded verified high math graph: {len(by_code)} nodes")


if __name__ == "__main__":
    seed()
