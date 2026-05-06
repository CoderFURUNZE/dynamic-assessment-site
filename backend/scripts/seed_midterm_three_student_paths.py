from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    Course,
    CourseCompletionRecord,
    Enrollment,
    EnrollmentStatus,
    KpQuestionAssignment,
    KnowledgeEdge,
    KnowledgePoint,
    LearningBehaviorEvent,
    LearningResource,
    Mastery,
    PersonaType,
    PracticeAttempt,
    Question,
    Quiz,
    QuizItem,
    QuizAttempt,
    RecommendationLog,
    RelationType,
    ResourceType,
    ReviewSchedule,
    User,
    UserRole,
    VideoProgress,
)
from app.db.session import engine, init_db  # noqa: E402
from app.services.eval import upsert_mastery  # noqa: E402


SUBJECT = "高等数学"
GRADE = "通用"
COURSE_CODE = "HM-MIDTERM"
NOW = datetime(2026, 4, 25, 18, 30, 0)
PASSWORD = "123456"

STUDENT_PROFILES = {
    "student_demo_1": {
        "name": "学生A-基础补救路径",
        "student_no": "2026001",
        "class_name": "演示班",
        "persona": PersonaType.struggling,
        "target": "HM-MID-02",
        "message": "基础概念证据不足，系统先推荐回到“函数基础”，完成低阶练习后再推进极限运算。",
        "mastered": ["HM-MID-01"],
        "learning": ["HM-MID-02"],
        "path": ["HM-MID-01", "HM-MID-02", "HM-MID-03", "HM-MID-04", "HM-MID-C2"],
    },
    "student_demo_2": {
        "name": "学生B-主线推进路径",
        "student_no": "2026002",
        "class_name": "演示班",
        "persona": PersonaType.steady,
        "target": "HM-MID-03",
        "message": "函数基础和极限直观已达标，当前卡在“极限运算”，系统推荐继续巩固主线。",
        "mastered": ["HM-MID-01", "HM-MID-02"],
        "learning": ["HM-MID-03"],
        "path": ["HM-MID-01", "HM-MID-03", "HM-MID-04", "HM-MID-C2"],
    },
    "student_demo_3": {
        "name": "学生C-积分分支冲刺路径",
        "student_no": "2026003",
        "class_name": "演示班",
        "persona": PersonaType.smart,
        "target": "HM-MID-B3",
        "message": "前置主线和积分概念、积分计算已达标，系统推荐冲刺积分应用达标终点。",
        "mastered": ["HM-MID-01", "HM-MID-02", "HM-MID-03", "HM-MID-04", "HM-MID-B1", "HM-MID-B2"],
        "learning": ["HM-MID-B3"],
        "path": ["HM-MID-01", "HM-MID-B1", "HM-MID-B2", "HM-MID-B3", "HM-MID-C2"],
    },
}

GOAL_EDGE_CODES = [
    ("HM-MID-03", "HM-MID-C2"),
    ("HM-MID-A3", "HM-MID-C2"),
    ("HM-MID-B3", "HM-MID-C2"),
    ("HM-MID-C1", "HM-MID-C2"),
]

REALISTIC_KP_CONTENT = {
    "HM-MID-01": {
        "resource": ("函数基础精讲：定义域、对应关系与函数值", "用定义域、对应关系和值域三个角度判断函数是否成立，并完成函数值计算。"),
        "questions": [
            {
                "prompt": "设 f(x)=sqrt(x-1)+1/(x-3)，则 f(x) 的定义域是（ ）。",
                "options": ["[1,+∞)", "[1,3)∪(3,+∞)", "(1,3)∪(3,+∞)", "(-∞,3)∪(3,+∞)"],
                "answer": "[1,3)∪(3,+∞)",
                "explanation": "sqrt(x-1) 要求 x≥1，1/(x-3) 要求 x≠3，合并得到 [1,3)∪(3,+∞)。",
                "difficulty": 0.35,
                "level": "understand",
                "ability": "定义域分析,符号运算",
            },
            {
                "prompt": "若 f(x)=2x^2-3x+1，则 f(a+1)-f(a) 的值是（ ）。",
                "options": ["4a-1", "4a+1", "2a+1", "4a+3"],
                "answer": "4a-1",
                "explanation": "f(a+1)=2(a+1)^2-3(a+1)+1=2a^2+a，f(a)=2a^2-3a+1，相减为 4a-1。",
                "difficulty": 0.42,
                "level": "apply",
                "ability": "代入求值,代数化简",
            },
            {
                "prompt": "下列对应关系中，能表示 y 是 x 的函数的是（ ）。",
                "options": ["x 为实数，y^2=x", "x 为实数，y=±x", "x 为非负实数，y=sqrt(x)", "x 为实数，y 满足 |y|=x"],
                "answer": "x 为非负实数，y=sqrt(x)",
                "explanation": "函数要求每个 x 只能对应唯一的 y。只有 y=sqrt(x) 在 x≥0 时输出唯一非负值。",
                "difficulty": 0.38,
                "level": "understand",
                "ability": "函数概念辨析",
            },
        ],
        "quiz": [
            {
                "prompt": "判断函数是否相同，关键要同时比较（ ）。",
                "options": ["表达式和函数名", "定义域和对应法则", "图像和变量字母", "值域和函数名"],
                "answer": "定义域和对应法则",
                "explanation": "两个函数相同必须定义域相同、对应法则相同。",
            },
            {
                "prompt": "f(x)=1/(x^2-4) 的定义域应排除（ ）。",
                "options": ["x=0", "x=2", "x=-2 和 x=2", "所有负数"],
                "answer": "x=-2 和 x=2",
                "explanation": "分母 x^2-4=(x-2)(x+2)，不能为 0。",
            },
        ],
    },
    "HM-MID-02": {
        "resource": ("极限直观精讲：趋近过程与左右极限", "用表格、图像和左右逼近理解极限存在的含义。"),
        "questions": [
            {
                "prompt": "若 x→2 时，f(x) 的左极限为 3，右极限为 5，则 lim x→2 f(x)（ ）。",
                "options": ["等于 3", "等于 5", "等于 4", "不存在"],
                "answer": "不存在",
                "explanation": "左右极限相等时二侧极限才存在；这里 3≠5，所以极限不存在。",
                "difficulty": 0.36,
                "level": "understand",
                "ability": "左右极限判断",
            },
            {
                "prompt": "函数在 x=a 处的极限存在，是否一定要求 f(a) 有定义？",
                "options": ["一定要求", "不一定要求", "只要求 f(a)=0", "只要求 f(a)>0"],
                "answer": "不一定要求",
                "explanation": "极限描述的是 x 趋近 a 时的函数变化，和点 a 处函数值是否定义无必然关系。",
                "difficulty": 0.32,
                "level": "understand",
                "ability": "极限概念辨析",
            },
            {
                "prompt": "lim x→0 sin x / x 的几何直观结果是（ ）。",
                "options": ["0", "1", "不存在", "+∞"],
                "answer": "1",
                "explanation": "这是第一重要极限，可由单位圆夹逼关系得到结果为 1。",
                "difficulty": 0.45,
                "level": "remember",
                "ability": "重要极限识记",
            },
        ],
        "quiz": [
            {
                "prompt": "极限 lim x→a f(x) 存在的必要条件是（ ）。",
                "options": ["f(a) 必须存在", "左右极限都不存在", "左右极限存在且相等", "函数必须单调"],
                "answer": "左右极限存在且相等",
                "explanation": "二侧极限存在的核心条件是左右极限同时存在并相等。",
            },
            {
                "prompt": "x 趋近 a 但 x≠a，说明极限重点关注（ ）。",
                "options": ["a 点附近的变化", "a 点函数值本身", "函数名称", "坐标轴刻度"],
                "answer": "a 点附近的变化",
                "explanation": "极限关注自变量无限接近 a 时函数值的趋势。",
            },
        ],
    },
    "HM-MID-03": {
        "resource": ("极限运算精讲：代入、因式分解与有理化", "整理常见未定式的处理步骤，训练 0/0 型极限化简。"),
        "questions": [
            {
                "prompt": "lim x→2 (x^2-4)/(x-2) 的值是（ ）。",
                "options": ["0", "2", "4", "不存在"],
                "answer": "4",
                "explanation": "x^2-4=(x-2)(x+2)，约去 x-2 后代入 x=2，得到 4。",
                "difficulty": 0.48,
                "level": "apply",
                "ability": "因式分解,极限计算",
            },
            {
                "prompt": "lim x→0 (1-cos x)/x^2 的值是（ ）。",
                "options": ["0", "1/2", "1", "2"],
                "answer": "1/2",
                "explanation": "1-cos x=2sin^2(x/2)，原式=2[sin(x/2)/x]^2=1/2。",
                "difficulty": 0.65,
                "level": "analyze",
                "ability": "三角恒等变形,重要极限",
            },
            {
                "prompt": "计算 lim x→1 (sqrt(x+3)-2)/(x-1)，最合适的第一步是（ ）。",
                "options": ["直接约分", "分子有理化", "两边取对数", "使用洛必达法则"],
                "answer": "分子有理化",
                "explanation": "分子含根式且代入为 0，乘以共轭式可化为 1/(sqrt(x+3)+2)。",
                "difficulty": 0.58,
                "level": "apply",
                "ability": "有理化,解题策略选择",
            },
        ],
        "quiz": [
            {
                "prompt": "遇到 0/0 型多项式极限，优先考虑（ ）。",
                "options": ["因式分解约分", "直接写不存在", "换成三角函数", "只看分子"],
                "answer": "因式分解约分",
                "explanation": "多项式 0/0 型常通过因式分解消去造成未定式的因子。",
            },
            {
                "prompt": "lim x→0 sin(3x)/x 的值是（ ）。",
                "options": ["0", "1", "3", "不存在"],
                "answer": "3",
                "explanation": "sin(3x)/(3x)→1，所以 sin(3x)/x→3。",
            },
        ],
    },
    "HM-MID-04": {
        "resource": ("连续性判断精讲：定义、间断点与可去间断", "围绕连续三条件判断函数在一点处是否连续。"),
        "questions": [
            {
                "prompt": "函数 f 在 x=a 处连续，需要满足（ ）。",
                "options": ["只要 f(a) 存在", "只要极限存在", "lim x→a f(x)=f(a)", "左右导数相等"],
                "answer": "lim x→a f(x)=f(a)",
                "explanation": "连续要求函数值存在、极限存在，并且极限值等于函数值。",
                "difficulty": 0.42,
                "level": "understand",
                "ability": "连续定义",
            },
            {
                "prompt": "若 f(1)=2，但 lim x→1 f(x)=3，则 x=1 是（ ）。",
                "options": ["连续点", "可去间断点", "跳跃间断点", "无穷间断点"],
                "answer": "可去间断点",
                "explanation": "极限存在但不等于函数值，改定义后可连续，因此是可去间断。",
                "difficulty": 0.55,
                "level": "apply",
                "ability": "间断点分类",
            },
            {
                "prompt": "分段函数在分界点连续，通常需要优先检查（ ）。",
                "options": ["左右极限与函数值", "函数是否为偶函数", "图像颜色", "自变量名称"],
                "answer": "左右极限与函数值",
                "explanation": "分段点最容易出现左右表达式不一致，必须检查左右极限和函数值是否相等。",
                "difficulty": 0.45,
                "level": "apply",
                "ability": "分段函数分析",
            },
        ],
        "quiz": [
            {
                "prompt": "极限存在但函数值不存在的点，属于（ ）。",
                "options": ["连续点", "可去间断点", "无穷间断点", "振荡间断点"],
                "answer": "可去间断点",
                "explanation": "补上适当函数值后可以变连续，因此是可去间断。",
            },
            {
                "prompt": "初等函数在其定义区间内通常具有（ ）。",
                "options": ["连续性", "处处不可导", "处处间断", "无极限"],
                "answer": "连续性",
                "explanation": "常见初等函数在定义域内连续。",
            },
        ],
    },
    "HM-MID-A1": {
        "resource": ("导数概念精讲：平均变化率到瞬时变化率", "用割线斜率逼近切线斜率理解导数定义。"),
        "questions": [
            {
                "prompt": "函数 f 在 x0 处的导数表示的是（ ）。",
                "options": ["函数平均值", "瞬时变化率", "函数最大值", "定义域长度"],
                "answer": "瞬时变化率",
                "explanation": "导数是差商极限，描述函数在一点附近的瞬时变化率。",
                "difficulty": 0.4,
                "level": "understand",
                "ability": "导数概念",
            },
            {
                "prompt": "曲线 y=f(x) 在 x0 处可导时，导数的几何意义是（ ）。",
                "options": ["切线斜率", "法线长度", "曲线面积", "横坐标"],
                "answer": "切线斜率",
                "explanation": "导数等于该点切线的斜率。",
                "difficulty": 0.38,
                "level": "remember",
                "ability": "几何意义",
            },
            {
                "prompt": "若 f'(2)=5，则当 h 很小时，f(2+h)-f(2) 近似为（ ）。",
                "options": ["5h", "h/5", "5", "2h"],
                "answer": "5h",
                "explanation": "由导数定义，f(2+h)-f(2)≈f'(2)h=5h。",
                "difficulty": 0.56,
                "level": "apply",
                "ability": "线性近似",
            },
        ],
        "quiz": [
            {
                "prompt": "导数定义中的差商极限本质上刻画（ ）。",
                "options": ["平均值", "变化率趋于稳定的值", "函数零点个数", "图像面积"],
                "answer": "变化率趋于稳定的值",
                "explanation": "差商表示平均变化率，极限给出瞬时变化率。",
            },
            {
                "prompt": "可导一定连续吗？",
                "options": ["一定", "不一定", "只有多项式一定", "只有三角函数一定"],
                "answer": "一定",
                "explanation": "可导是比连续更强的条件，可导必连续。",
            },
        ],
    },
    "HM-MID-A2": {
        "resource": ("求导法则精讲：四则、复合与常见公式", "整理基础函数导数和链式法则的使用场景。"),
        "questions": [
            {
                "prompt": "若 y=x^3-2x+1，则 y' 等于（ ）。",
                "options": ["3x^2-2", "3x^2+1", "x^2-2", "3x-2"],
                "answer": "3x^2-2",
                "explanation": "幂函数逐项求导：(x^3)'=3x^2，(-2x)'=-2，常数导数为 0。",
                "difficulty": 0.43,
                "level": "apply",
                "ability": "基本求导",
            },
            {
                "prompt": "函数 y=sin(2x) 的导数是（ ）。",
                "options": ["cos(2x)", "2cos(2x)", "-2cos(2x)", "2sin(2x)"],
                "answer": "2cos(2x)",
                "explanation": "复合函数求导，外层 sin 的导数为 cos，内层 2x 的导数为 2。",
                "difficulty": 0.5,
                "level": "apply",
                "ability": "链式法则",
            },
            {
                "prompt": "求导 (uv)' 的正确公式是（ ）。",
                "options": ["u'v'", "u'v+uv'", "u/v", "u'+v'"],
                "answer": "u'v+uv'",
                "explanation": "乘积求导法则为一个函数求导乘另一个不动，再相加。",
                "difficulty": 0.46,
                "level": "remember",
                "ability": "乘积法则",
            },
        ],
        "quiz": [
            {
                "prompt": "y=e^{3x} 的导数是（ ）。",
                "options": ["e^{3x}", "3e^{3x}", "e^x", "3e^x"],
                "answer": "3e^{3x}",
                "explanation": "复合函数求导需要乘以内层 3x 的导数 3。",
            },
            {
                "prompt": "常数函数 y=C 的导数是（ ）。",
                "options": ["C", "1", "0", "x"],
                "answer": "0",
                "explanation": "常数函数不随 x 变化，导数为 0。",
            },
        ],
    },
    "HM-MID-A3": {
        "resource": ("导数应用精讲：单调性、极值与最值", "用导数符号判断函数增减，并定位极值点。"),
        "questions": [
            {
                "prompt": "若在区间 I 上 f'(x)>0，则 f(x) 在 I 上（ ）。",
                "options": ["单调递增", "单调递减", "恒为 0", "不连续"],
                "answer": "单调递增",
                "explanation": "导数为正表示函数随 x 增大而增大。",
                "difficulty": 0.45,
                "level": "understand",
                "ability": "单调性判断",
            },
            {
                "prompt": "函数 f(x)=x^2-4x+3 的极小值点是（ ）。",
                "options": ["x=0", "x=1", "x=2", "x=4"],
                "answer": "x=2",
                "explanation": "f'(x)=2x-4，令 f'(x)=0 得 x=2，二次项系数为正，故为极小值点。",
                "difficulty": 0.55,
                "level": "apply",
                "ability": "极值计算",
            },
            {
                "prompt": "用导数解决最值问题时，闭区间上通常要比较（ ）。",
                "options": ["驻点和端点函数值", "只比较端点", "只比较导数值", "只看图像颜色"],
                "answer": "驻点和端点函数值",
                "explanation": "闭区间最值可能出现在驻点或端点，需要逐一比较函数值。",
                "difficulty": 0.6,
                "level": "analyze",
                "ability": "最值策略",
            },
        ],
        "quiz": [
            {
                "prompt": "f'(x) 从正变负的驻点通常是（ ）。",
                "options": ["极大值点", "极小值点", "间断点", "拐点一定成立"],
                "answer": "极大值点",
                "explanation": "导数符号正到负表示函数先增后减。",
            },
            {
                "prompt": "导数应用中，一阶导数主要用于判断（ ）。",
                "options": ["单调性和极值", "定义域", "函数名称", "坐标单位"],
                "answer": "单调性和极值",
                "explanation": "一阶导数符号反映函数增减趋势。",
            },
        ],
    },
    "HM-MID-B1": {
        "resource": ("积分概念精讲：累积量与反导数", "从面积累积和反导数两个角度理解积分。"),
        "questions": [
            {
                "prompt": "不定积分 ∫f(x)dx 表示的是（ ）。",
                "options": ["一个数", "f(x) 的全体原函数", "函数最大值", "导数值"],
                "answer": "f(x) 的全体原函数",
                "explanation": "不定积分结果是一族原函数，通常写作 F(x)+C。",
                "difficulty": 0.4,
                "level": "understand",
                "ability": "积分概念",
            },
            {
                "prompt": "若 F'(x)=f(x)，则 F(x) 称为 f(x) 的（ ）。",
                "options": ["导函数", "原函数", "反函数", "极限"],
                "answer": "原函数",
                "explanation": "导数为 f(x) 的函数 F(x) 是 f(x) 的原函数。",
                "difficulty": 0.36,
                "level": "remember",
                "ability": "原函数定义",
            },
            {
                "prompt": "定积分 ∫_a^b f(x)dx 在几何上常表示（ ）。",
                "options": ["函数值", "曲线与 x 轴围成的有向面积", "导数", "定义域"],
                "answer": "曲线与 x 轴围成的有向面积",
                "explanation": "定积分可解释为有向面积，曲线在 x 轴下方贡献为负。",
                "difficulty": 0.44,
                "level": "understand",
                "ability": "定积分几何意义",
            },
        ],
        "quiz": [
            {
                "prompt": "不定积分结果中常数 C 的含义是（ ）。",
                "options": ["任意常数", "必须等于 0", "积分上限", "函数最大值"],
                "answer": "任意常数",
                "explanation": "同一导函数对应的一族原函数相差一个常数。",
            },
            {
                "prompt": "积分与导数在基本思想上可以看作（ ）。",
                "options": ["互逆关系", "完全无关", "都只处理常数", "都不能计算面积"],
                "answer": "互逆关系",
                "explanation": "微积分基本定理建立了积分和导数之间的互逆联系。",
            },
        ],
    },
    "HM-MID-B2": {
        "resource": ("积分计算精讲：基本公式与换元法", "掌握常见函数积分公式，并识别简单换元结构。"),
        "questions": [
            {
                "prompt": "∫2x dx 的结果是（ ）。",
                "options": ["x^2+C", "2+C", "2x+C", "x+C"],
                "answer": "x^2+C",
                "explanation": "因为 (x^2)'=2x，所以 ∫2x dx=x^2+C。",
                "difficulty": 0.38,
                "level": "apply",
                "ability": "基本积分公式",
            },
            {
                "prompt": "∫cos x dx 的结果是（ ）。",
                "options": ["sin x+C", "-sin x+C", "cos x+C", "-cos x+C"],
                "answer": "sin x+C",
                "explanation": "sin x 的导数是 cos x，因此 cos x 的原函数是 sin x。",
                "difficulty": 0.4,
                "level": "remember",
                "ability": "三角函数积分",
            },
            {
                "prompt": "计算 ∫2x·e^{x^2} dx，适合令 u=（ ）。",
                "options": ["x", "2x", "x^2", "e^x"],
                "answer": "x^2",
                "explanation": "被积函数含 2x dx，正好是 x^2 的微分结构，令 u=x^2。",
                "difficulty": 0.62,
                "level": "analyze",
                "ability": "换元识别",
            },
        ],
        "quiz": [
            {
                "prompt": "∫x^n dx（n≠-1）的公式是（ ）。",
                "options": ["x^{n+1}/(n+1)+C", "nx^{n-1}+C", "x^n+C", "ln|x|+C"],
                "answer": "x^{n+1}/(n+1)+C",
                "explanation": "幂函数积分指数加 1，再除以新指数。",
            },
            {
                "prompt": "换元积分的关键是识别（ ）。",
                "options": ["内层函数及其微分", "函数颜色", "答案长度", "坐标轴方向"],
                "answer": "内层函数及其微分",
                "explanation": "换元法通过替换内层函数简化被积表达式。",
            },
        ],
    },
    "HM-MID-B3": {
        "resource": ("积分应用精讲：面积、位移与累积变化", "把定积分转化为实际累积量，完成终点应用任务。"),
        "questions": [
            {
                "prompt": "曲线 y=x 与 x 轴在 [0,2] 上围成的面积是（ ）。",
                "options": ["1", "2", "3", "4"],
                "answer": "2",
                "explanation": "面积为 ∫_0^2 x dx = x^2/2 |0^2 = 2。",
                "difficulty": 0.5,
                "level": "apply",
                "ability": "面积计算",
            },
            {
                "prompt": "速度函数 v(t)=3t^2，t 从 0 到 2 的位移是（ ）。",
                "options": ["4", "6", "8", "12"],
                "answer": "8",
                "explanation": "位移为 ∫_0^2 3t^2 dt = t^3 |0^2 = 8。",
                "difficulty": 0.56,
                "level": "apply",
                "ability": "物理应用",
            },
            {
                "prompt": "用定积分求平面图形面积时，若上方函数为 g(x)，下方函数为 h(x)，面积通常为（ ）。",
                "options": ["∫[g(x)-h(x)]dx", "∫[h(x)-g(x)]dx", "∫g(x)h(x)dx", "g(a)-h(b)"],
                "answer": "∫[g(x)-h(x)]dx",
                "explanation": "面积等于上方函数减下方函数在区间上的积分。",
                "difficulty": 0.6,
                "level": "analyze",
                "ability": "模型建立",
            },
        ],
        "quiz": [
            {
                "prompt": "定积分应用题的第一步通常是（ ）。",
                "options": ["确定被积函数和积分区间", "直接写答案", "忽略单位", "只求导"],
                "answer": "确定被积函数和积分区间",
                "explanation": "应用题建模关键是明确累积的对象和范围。",
            },
            {
                "prompt": "速度函数的定积分常表示（ ）。",
                "options": ["位移", "加速度", "时间平方", "质量"],
                "answer": "位移",
                "explanation": "速度对时间积分得到位移。",
            },
        ],
    },
    "HM-MID-C1": {
        "resource": ("综合建模准备：从文字条件到函数模型", "训练把情境中的变量、约束和目标转化为函数关系。"),
        "questions": [
            {
                "prompt": "建立函数模型时，第一步通常是（ ）。",
                "options": ["明确自变量和因变量", "先求导", "先积分", "删除所有条件"],
                "answer": "明确自变量和因变量",
                "explanation": "建模必须先确定研究对象和变量关系，再选择方法。",
                "difficulty": 0.5,
                "level": "analyze",
                "ability": "变量识别",
            },
            {
                "prompt": "若题目要求“最大利润”，数学上通常转化为（ ）。",
                "options": ["求函数最大值", "求定义域", "求导数名称", "求随机数"],
                "answer": "求函数最大值",
                "explanation": "利润随变量变化时，最大利润问题就是目标函数的最大值问题。",
                "difficulty": 0.55,
                "level": "apply",
                "ability": "目标函数建立",
            },
            {
                "prompt": "综合题中约束条件的作用是（ ）。",
                "options": ["确定变量取值范围", "改变题目字体", "保证答案为整数", "省略计算"],
                "answer": "确定变量取值范围",
                "explanation": "约束条件限定模型适用范围，也是求最值时必须考虑的定义域。",
                "difficulty": 0.52,
                "level": "understand",
                "ability": "约束分析",
            },
        ],
        "quiz": [
            {
                "prompt": "综合建模题最容易漏掉的是（ ）。",
                "options": ["变量范围", "题目标题", "函数名称", "选项编号"],
                "answer": "变量范围",
                "explanation": "变量范围决定模型是否符合实际情境。",
            },
            {
                "prompt": "把实际问题转成函数问题后，常用的求解工具包括（ ）。",
                "options": ["导数和积分", "字体和颜色", "页面大小", "用户名"],
                "answer": "导数和积分",
                "explanation": "导数用于优化，积分用于累积量计算。",
            },
        ],
    },
    "HM-MID-C2": {
        "resource": ("期中综合达标：函数、导数、积分联动", "用一组综合任务串联极限、导数和积分三条主线。"),
        "questions": [
            {
                "prompt": "若先由函数模型求最优方案，再计算累计收益，可能依次用到（ ）。",
                "options": ["导数、积分", "积分、导数", "只用定义域", "只用函数名"],
                "answer": "导数、积分",
                "explanation": "最优方案通常靠导数判断，累计收益通常靠积分计算。",
                "difficulty": 0.66,
                "level": "analyze",
                "ability": "方法选择",
            },
            {
                "prompt": "综合题检查答案合理性时，最重要的是（ ）。",
                "options": ["回到原情境检验单位和范围", "只看数值大小", "只看答案是否好看", "忽略条件"],
                "answer": "回到原情境检验单位和范围",
                "explanation": "综合应用题要检验结果是否符合实际意义、单位和约束条件。",
                "difficulty": 0.58,
                "level": "evaluate",
                "ability": "结果检验",
            },
            {
                "prompt": "若 f'(x)>0 且 f''(x)>0，在图像上可理解为（ ）。",
                "options": ["递增且增速变快", "递减且增速变慢", "恒为常数", "一定间断"],
                "answer": "递增且增速变快",
                "explanation": "一阶导数为正表示递增，二阶导数为正表示斜率增加。",
                "difficulty": 0.7,
                "level": "analyze",
                "ability": "综合图像分析",
            },
        ],
        "quiz": [
            {
                "prompt": "期中综合题中，选择方法前应先判断（ ）。",
                "options": ["题目要求的是变化率、最值还是累积量", "选项数量", "页面颜色", "题号大小"],
                "answer": "题目要求的是变化率、最值还是累积量",
                "explanation": "变化率对应导数，累积量对应积分，最值常用导数。",
            },
            {
                "prompt": "综合达标的证据应包含（ ）。",
                "options": ["正确建模、计算和解释", "只提交答案", "只看视频", "只登录系统"],
                "answer": "正确建模、计算和解释",
                "explanation": "综合能力要求过程、结果和解释都成立。",
            },
        ],
    },
}


def ensure_student(session: Session, username: str, profile: dict) -> User:
    student = session.exec(select(User).where(User.username == username)).first()
    if student is None:
        student = User(username=username, password_hash=hash_password(PASSWORD), role=UserRole.student)
    student.password_hash = hash_password(PASSWORD)
    student.role = UserRole.student
    student.active = True
    student.full_name = str(profile["name"])
    student.student_no = str(profile["student_no"])
    student.class_name = str(profile["class_name"])
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def ensure_enrollment(session: Session, course: Course, student: User) -> None:
    row = session.exec(
        select(Enrollment).where(
            Enrollment.course_id == int(course.id),
            Enrollment.student_id == int(student.id),
        )
    ).first()
    if row is None:
        row = Enrollment(course_id=int(course.id), student_id=int(student.id))
    row.status = EnrollmentStatus.active
    row.enrolled_at = NOW - timedelta(days=28)
    session.add(row)


def ensure_learning_assets(session: Session, kp: KnowledgePoint, order: int) -> tuple[Question, Quiz, LearningResource]:
    content = REALISTIC_KP_CONTENT.get(kp.code)
    if content is None:
        content = {
            "resource": (f"{kp.title} 精讲", f"围绕 {kp.title} 的核心概念、例题和易错点进行学习。"),
            "questions": [
                {
                    "prompt": f"{kp.title} 的核心学习目标最接近下列哪一项？",
                    "options": ["理解概念并能完成基础应用", "只记住标题", "跳过练习", "只看答案"],
                    "answer": "理解概念并能完成基础应用",
                    "explanation": "知识点学习需要概念理解、例题迁移和练习反馈共同形成掌握证据。",
                    "difficulty": float(kp.difficulty or 0.5),
                    "level": "understand",
                    "ability": "概念理解",
                }
            ],
            "quiz": [
                {
                    "prompt": f"完成 {kp.title} 学习后，最应该保留的证据是（ ）。",
                    "options": ["练习正确率和学习记录", "只打开页面", "只看标题", "只退出登录"],
                    "answer": "练习正确率和学习记录",
                    "explanation": "系统会综合资源、练习、小测和行为记录更新掌握度。",
                }
            ],
        }

    created_questions: list[Question] = []
    for index, item in enumerate(content["questions"], start=1):
        question = session.exec(select(Question).where(Question.kp_id == int(kp.id), Question.prompt == item["prompt"])).first()
        if question is None:
            question = Question(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id), type="mcq", prompt=item["prompt"])
        question.subject = SUBJECT
        question.grade = GRADE
        question.type = "mcq"
        question.options_json = json.dumps(item["options"], ensure_ascii=False)
        question.answer = item["answer"]
        question.explanation = item["explanation"]
        question.difficulty = float(item.get("difficulty", kp.difficulty or 0.5))
        question.source = "midterm_three_student_paths"
        question.tags = f"midterm_demo,path_demo,{kp.code}"
        question.version = "midterm-realistic-v2"
        question.cognitive_level = str(item.get("level", "understand"))
        question.ability_subtags = str(item.get("ability", ""))
        session.add(question)
        session.flush()
        session.refresh(question)
        created_questions.append(question)

        assignment = session.exec(
            select(KpQuestionAssignment).where(
                KpQuestionAssignment.kp_id == int(kp.id),
                KpQuestionAssignment.question_id == int(question.id),
            )
        ).first()
        if assignment is None:
            assignment = KpQuestionAssignment(kp_id=int(kp.id), question_id=int(question.id))
        assignment.order = order * 10 + index
        session.add(assignment)

    session.commit()

    quiz = session.exec(select(Quiz).where(Quiz.kp_id == int(kp.id))).first()
    if quiz is None:
        quiz = Quiz(subject=SUBJECT, grade=GRADE, kp_id=int(kp.id))
    quiz.subject = SUBJECT
    quiz.grade = GRADE
    quiz.pass_accuracy = 0.8
    session.add(quiz)
    session.commit()
    session.refresh(quiz)

    for index, item in enumerate(content["quiz"], start=1):
        quiz_item = session.exec(
            select(QuizItem).where(
                QuizItem.quiz_id == int(quiz.id),
                QuizItem.prompt == item["prompt"],
            )
        ).first()
        if quiz_item is None:
            quiz_item = QuizItem(quiz_id=int(quiz.id), type="mcq", prompt=item["prompt"])
        quiz_item.type = "mcq"
        quiz_item.options_json = json.dumps(item["options"], ensure_ascii=False)
        quiz_item.answer = item["answer"]
        quiz_item.explanation = item["explanation"]
        quiz_item.key_item = index == 1
        session.add(quiz_item)

    resource_title, resource_desc = content["resource"]
    resource = session.exec(
        select(LearningResource).where(
            LearningResource.kp_id == int(kp.id),
            LearningResource.title == resource_title,
        )
    ).first()
    if resource is None:
        resource = LearningResource(
            subject=SUBJECT,
            grade=GRADE,
            kp_id=int(kp.id),
            title=resource_title,
            url=f"https://example.com/midterm/{kp.code}",
            type=ResourceType.video,
        )
    resource.subject = SUBJECT
    resource.grade = GRADE
    resource.category = "learning"
    resource.description = resource_desc
    resource.tags = f"midterm_demo,path_demo,{kp.code}"
    resource.preview_status = "ready"
    resource.type = ResourceType.video
    resource.detected_resource_type = "video"
    resource.preview_type = "video"
    resource.original_file_url = resource.url
    resource.converted_preview_url = ""
    session.add(resource)
    session.commit()
    session.refresh(resource)
    return created_questions[0], quiz, resource


def clear_midterm_assets(session: Session, *, kp_ids: list[int]) -> None:
    question_ids = [
        int(row.id)
        for row in session.exec(
            select(Question).where(
                Question.kp_id.in_(kp_ids),
                (Question.source == "midterm_three_student_paths") | (Question.tags.contains("midterm_demo")),
            )
        ).all()
        if row.id is not None
    ]
    quiz_ids = [int(row.id) for row in session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids))).all() if row.id is not None]
    if question_ids:
        session.exec(delete(KpQuestionAssignment).where(KpQuestionAssignment.question_id.in_(question_ids)))
        session.exec(delete(Question).where(Question.id.in_(question_ids)))
    if quiz_ids:
        session.exec(delete(QuizItem).where(QuizItem.quiz_id.in_(quiz_ids)))
    session.exec(
        delete(LearningResource).where(
            LearningResource.kp_id.in_(kp_ids),
            (LearningResource.tags.contains("midterm_demo")) | (LearningResource.url.like("https://example.com/midterm/%")),
        )
    )
    session.commit()


def clear_student_graph_data(session: Session, *, course: Course, students: list[User], kp_ids: list[int]) -> None:
    user_ids = [int(student.id) for student in students if student.id is not None]
    if not user_ids or not kp_ids:
        return
    question_ids = [int(row.id) for row in session.exec(select(Question).where(Question.kp_id.in_(kp_ids))).all() if row.id is not None]
    quiz_ids = [int(row.id) for row in session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids))).all() if row.id is not None]
    if question_ids:
        session.exec(delete(PracticeAttempt).where(PracticeAttempt.user_id.in_(user_ids), PracticeAttempt.question_id.in_(question_ids)))
        session.exec(delete(ReviewSchedule).where(ReviewSchedule.user_id.in_(user_ids), ReviewSchedule.question_id.in_(question_ids)))
    if quiz_ids:
        session.exec(delete(QuizAttempt).where(QuizAttempt.user_id.in_(user_ids), QuizAttempt.quiz_id.in_(quiz_ids)))
    session.exec(delete(VideoProgress).where(VideoProgress.user_id.in_(user_ids), VideoProgress.kp_id.in_(kp_ids)))
    session.exec(delete(Mastery).where(Mastery.user_id.in_(user_ids), Mastery.kp_id.in_(kp_ids)))
    session.exec(delete(RecommendationLog).where(RecommendationLog.user_id.in_(user_ids), RecommendationLog.subject == SUBJECT, RecommendationLog.grade == GRADE))
    session.exec(delete(LearningBehaviorEvent).where(LearningBehaviorEvent.user_id.in_(user_ids), LearningBehaviorEvent.course_id == int(course.id)))
    session.exec(delete(CourseCompletionRecord).where(CourseCompletionRecord.course_id == int(course.id), CourseCompletionRecord.student_id.in_(user_ids)))
    session.commit()


def ensure_common_goal_shape(session: Session, kp_map: dict[str, KnowledgePoint]) -> None:
    for code, kp in kp_map.items():
        kp.is_terminal = code == "HM-MID-C2"
        session.add(kp)
    for prereq_code, next_code in GOAL_EDGE_CODES:
        prereq = kp_map.get(prereq_code)
        next_kp = kp_map.get(next_code)
        if prereq is None or next_kp is None or prereq.id is None or next_kp.id is None:
            continue
        existing = session.exec(
            select(KnowledgeEdge).where(
                KnowledgeEdge.prereq_id == int(prereq.id),
                KnowledgeEdge.next_id == int(next_kp.id),
                KnowledgeEdge.relation_type == RelationType.prerequisite,
            )
        ).first()
        if existing is None:
            session.add(
                KnowledgeEdge(
                    prereq_id=int(prereq.id),
                    next_id=int(next_kp.id),
                    relation_type=RelationType.prerequisite,
                    weight=1.0,
                )
            )
    session.commit()


def add_learning_evidence(
    session: Session,
    *,
    course: Course,
    student: User,
    kp: KnowledgePoint,
    question: Question,
    quiz: Quiz,
    resource: LearningResource,
    level: str,
    offset: int,
) -> None:
    if level == "none":
        return

    if level == "mastered":
        correct_count, quiz_score, watched_ratio, review_result = 10, 0.94, 1.0, "correct"
    elif level == "learning":
        correct_count, quiz_score, watched_ratio, review_result = 5, 0.55, 0.45, "wrong"
    else:
        correct_count, quiz_score, watched_ratio, review_result = 2, 0.35, 0.15, "wrong"

    for index in range(10):
        session.add(
            PracticeAttempt(
                user_id=int(student.id),
                question_id=int(question.id),
                kp_id=int(kp.id),
                correct=index < correct_count,
                self_report="sure" if index < correct_count and level == "mastered" else "unknown",
                duration_ms=42000 + index * 2500 + offset * 1000,
                created_at=NOW - timedelta(days=12 - min(index, 9), hours=offset),
            )
        )

    session.add(
        QuizAttempt(
            user_id=int(student.id),
            quiz_id=int(quiz.id),
            kp_id=int(kp.id),
            score=quiz_score,
            passed=quiz_score >= 0.8,
            duration_ms=180000 + offset * 10000,
            created_at=NOW - timedelta(days=2, hours=offset),
        )
    )
    video_progress = session.exec(
        select(VideoProgress).where(
            VideoProgress.user_id == int(student.id),
            VideoProgress.resource_id == int(resource.id),
        )
    )
    video_progress = video_progress.first()
    if video_progress is None:
        video_progress = VideoProgress(
            user_id=int(student.id),
            kp_id=int(kp.id),
            resource_id=int(resource.id),
        )
    video_progress.watched_seconds = round(600 * watched_ratio, 2)
    video_progress.duration_seconds = 600
    video_progress.last_position_seconds = round(600 * watched_ratio, 2)
    video_progress.completed = watched_ratio >= 0.8
    video_progress.updated_at = NOW - timedelta(days=3, hours=offset)
    session.add(video_progress)
    schedule = session.exec(
        select(ReviewSchedule).where(
            ReviewSchedule.user_id == int(student.id),
            ReviewSchedule.question_id == int(question.id),
        )
    )
    schedule = schedule.first()
    if schedule is None:
        schedule = ReviewSchedule(
            user_id=int(student.id),
            question_id=int(question.id),
            kp_id=int(kp.id),
            created_at=NOW - timedelta(days=9, hours=offset),
        )
    schedule.interval_days = 7 if review_result == "correct" else 2
    schedule.due_at = NOW + timedelta(days=4) if review_result == "correct" else NOW - timedelta(days=1)
    schedule.last_result = review_result
    schedule.updated_at = NOW - timedelta(days=1, hours=offset)
    session.add(schedule)
    session.add(
        LearningBehaviorEvent(
            user_id=int(student.id),
            course_id=int(course.id),
            kp_id=int(kp.id),
            event_type="path_demo_evidence",
            value_json=json.dumps({"level": level, "kp_code": kp.code}, ensure_ascii=False),
            created_at=NOW - timedelta(days=max(1, 8 - offset)),
        )
    )


def add_recommendation_log(session: Session, *, student: User, kp_map: dict[str, KnowledgePoint], profile: dict) -> None:
    target = kp_map[str(profile["target"])]
    path_nodes = [
        {
            "id": int(kp_map[code].id),
            "kp_id": int(kp_map[code].id),
            "code": code,
            "title": kp_map[code].title,
            "mastery": float(
                session.exec(
                    select(Mastery).where(Mastery.user_id == int(student.id), Mastery.kp_id == int(kp_map[code].id))
                ).first().value
                if session.exec(
                    select(Mastery).where(Mastery.user_id == int(student.id), Mastery.kp_id == int(kp_map[code].id))
                ).first()
                else 0.0
            ),
        }
        for code in profile["path"]
    ]
    payload = {
        "target_kp": {
            "id": int(target.id),
            "code": target.code,
            "title": target.title,
            "chapter": target.chapter,
        },
        "reason_summary": profile["message"],
        "advice_text": profile["message"],
        "student_message": profile["message"],
        "personalized_path": path_nodes,
        "recommendation_stage_label": "演示路径",
        "recommendation_source": "midterm_demo_seed",
    }
    session.add(
        RecommendationLog(
            user_id=int(student.id),
            subject=SUBJECT,
            grade=GRADE,
            source_kp_id=int(target.id),
            target_kp_id=int(target.id),
            persona_type=profile["persona"],
            reason_summary=str(profile["message"]),
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=NOW,
        )
    )


def seed() -> None:
    init_db()
    with Session(engine) as session:
        course = session.exec(select(Course).where(Course.code == COURSE_CODE)).first()
        if course is None or course.id is None:
            raise RuntimeError("Course HM-MIDTERM not found. Run seed_midterm_demo_minimal.py first.")
        course.active = True
        course.title = SUBJECT
        course.lifecycle_status = "active"
        session.add(course)

        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE, KnowledgePoint.code.startswith("HM-MID-"))
            .order_by(KnowledgePoint.id)
        ).all()
        if not kps:
            raise RuntimeError("High math midterm knowledge graph not found.")
        kp_map = {kp.code: kp for kp in kps}
        ensure_common_goal_shape(session, kp_map)

        students = [ensure_student(session, username, profile) for username, profile in STUDENT_PROFILES.items()]
        for student in students:
            ensure_enrollment(session, course, student)
        session.commit()

        kp_ids = [int(kp.id) for kp in kps]
        clear_student_graph_data(session, course=course, students=students, kp_ids=kp_ids)
        clear_midterm_assets(session, kp_ids=kp_ids)
        asset_map = {kp.code: ensure_learning_assets(session, kp, index) for index, kp in enumerate(kps, start=1)}

        for student_index, student in enumerate(students):
            profile = STUDENT_PROFILES[student.username]
            mastered = set(profile["mastered"])
            learning = set(profile["learning"])
            for kp_index, kp in enumerate(kps):
                if kp.code in mastered:
                    level = "mastered"
                elif kp.code in learning:
                    level = "learning"
                else:
                    level = "none"
                question, quiz, resource = asset_map[kp.code]
                add_learning_evidence(
                    session,
                    course=course,
                    student=student,
                    kp=kp,
                    question=question,
                    quiz=quiz,
                    resource=resource,
                    level=level,
                    offset=student_index * 20 + kp_index,
                )
            session.commit()

            for kp in kps:
                upsert_mastery(session, user_id=int(student.id), kp_id=int(kp.id), subject=SUBJECT, grade=GRADE)
            add_recommendation_log(session, student=student, kp_map=kp_map, profile=profile)
            session.commit()

        print("seeded three student paths:")
        for student in students:
            profile = STUDENT_PROFILES[student.username]
            target = kp_map[str(profile["target"])]
            target_mastery = session.exec(
                select(Mastery).where(Mastery.user_id == int(student.id), Mastery.kp_id == int(target.id))
            ).first()
            print(
                f"- {student.username} {student.full_name}: target={target.code} {target.title}, "
                f"mastery={float(target_mastery.value) if target_mastery else 0:.2f}"
            )


if __name__ == "__main__":
    seed()
