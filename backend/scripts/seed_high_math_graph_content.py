from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import delete
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.models import (
    KpQuestionAssignment,
    KpTask,
    KpTaskType,
    KnowledgePoint,
    LearningResource,
    PracticeAttempt,
    Question,
    Quiz,
    QuizAttempt,
    QuizItem,
    ResourceType,
    ReviewSchedule,
)
from app.db.session import engine


SUBJECT = "高等数学"
GRADE = "通用"
SEED_TAG = "high_math_seed_pack"
QUESTION_VERSION = "high_math-v1"
TASK_TITLE_PREFIX = "演示任务："
QUIZ_PROMPT_PREFIX = "【高数节点小测】"


RESOURCE_BANK = {
    "function": [
        {
            "title": "OpenStax Calculus Volume 1: Functions and Graphs",
            "url": "https://openstax.org/books/calculus-volume-1/pages/1-introduction",
            "description": "覆盖函数、基本函数类型、复合函数与反函数，适合函数与映射类节点预习和复习。",
        },
        {
            "title": "Paul's Online Math Notes: Functions",
            "url": "https://tutorial.math.lamar.edu/Classes/Alg/Functions.aspx",
            "description": "用例题说明函数记号、定义域、值域和复合函数计算，可作为入门练习材料。",
        },
    ],
    "limit": [
        {
            "title": "OpenStax Calculus Volume 1: Limits",
            "url": "https://openstax.org/books/calculus-volume-1/pages/2-introduction",
            "description": "系统讲解数列/函数极限思想、极限定律、连续性与夹逼定理。",
        },
        {
            "title": "Paul's Online Math Notes: Limits",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/LimitsIntro.aspx",
            "description": "包含极限计算、单侧极限、无穷极限与连续性的讲义和练习。",
        },
    ],
    "continuity": [
        {
            "title": "OpenStax Calculus Volume 1: Continuity",
            "url": "https://openstax.org/books/calculus-volume-1/pages/2-4-continuity",
            "description": "对应连续函数、间断点、闭区间连续函数性质和介值定理。",
        },
        {
            "title": "Paul's Online Math Notes: Continuity",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/Continuity.aspx",
            "description": "通过分段函数和常见间断点例题训练连续性判断。",
        },
    ],
    "derivative": [
        {
            "title": "OpenStax Calculus Volume 1: Derivatives",
            "url": "https://openstax.org/books/calculus-volume-1/pages/3-introduction",
            "description": "覆盖导数定义、导数作为函数、求导法则、高阶导数和隐函数求导。",
        },
        {
            "title": "Paul's Online Math Notes: Derivatives",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeIntro.aspx",
            "description": "适合导数概念、求导公式、链式法则、隐函数求导和相关变化率训练。",
        },
    ],
    "differential": [
        {
            "title": "OpenStax Calculus Volume 1: Linear Approximations and Differentials",
            "url": "https://openstax.org/books/calculus-volume-1/pages/4-2-linear-approximations-and-differentials",
            "description": "讲解微分、线性近似和误差估计，与微分应用节点直接对应。",
        },
        {
            "title": "Paul's Online Math Notes: Differentials",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/Differentials.aspx",
            "description": "提供微分形式、近似计算和误差估计例题。",
        },
    ],
    "application_derivative": [
        {
            "title": "OpenStax Calculus Volume 1: Applications of Derivatives",
            "url": "https://openstax.org/books/calculus-volume-1/pages/4-introduction",
            "description": "覆盖中值定理、洛必达法则、函数图形、极值、曲率和优化问题。",
        },
        {
            "title": "Paul's Online Math Notes: Applications of Derivatives",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DerivativeAppsIntro.aspx",
            "description": "包含单调性、凹凸性、极值、优化、相关变化率等练习。",
        },
    ],
    "indefinite_integral": [
        {
            "title": "OpenStax Calculus Volume 1: Integration",
            "url": "https://openstax.org/books/calculus-volume-1/pages/5-introduction",
            "description": "覆盖原函数、不定积分、换元积分和积分基本公式。",
        },
        {
            "title": "Paul's Online Math Notes: Indefinite Integrals",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/IndefiniteIntegrals.aspx",
            "description": "适合练习基本积分公式、线性性质和换元法。",
        },
    ],
    "technique_integral": [
        {
            "title": "OpenStax Calculus Volume 2: Techniques of Integration",
            "url": "https://openstax.org/books/calculus-volume-2/pages/3-introduction",
            "description": "覆盖分部积分、三角代换、部分分式和积分策略。",
        },
        {
            "title": "Paul's Online Math Notes: Integration Techniques",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcII/IntegrationTechniques.aspx",
            "description": "提供分部积分、有理函数积分、根式积分和综合积分技巧练习。",
        },
    ],
    "definite_integral": [
        {
            "title": "OpenStax Calculus Volume 1: The Definite Integral",
            "url": "https://openstax.org/books/calculus-volume-1/pages/5-2-the-definite-integral",
            "description": "对应定积分定义、黎曼和、定积分性质和几何意义。",
        },
        {
            "title": "Paul's Online Math Notes: Definite Integrals",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/DefnOfDefiniteIntegral.aspx",
            "description": "包含定积分定义、近似计算和牛顿-莱布尼茨公式相关例题。",
        },
    ],
    "improper_integral": [
        {
            "title": "OpenStax Calculus Volume 2: Improper Integrals",
            "url": "https://openstax.org/books/calculus-volume-2/pages/3-7-improper-integrals",
            "description": "讲解无穷限和无界函数反常积分的定义与审敛。",
        },
        {
            "title": "Paul's Online Math Notes: Improper Integrals",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcII/ImproperIntegrals.aspx",
            "description": "提供反常积分收敛性判断和计算练习。",
        },
    ],
    "integral_application": [
        {
            "title": "OpenStax Calculus Volume 1: Applications of Integration",
            "url": "https://openstax.org/books/calculus-volume-1/pages/6-introduction",
            "description": "对应面积、体积、弧长、平均值、功和物理应用。",
        },
        {
            "title": "Paul's Online Math Notes: Applications of Integrals",
            "url": "https://tutorial.math.lamar.edu/Classes/CalcI/ApplicationsIntegralsIntro.aspx",
            "description": "包含面积、旋转体体积、弧长和功等典型模型练习。",
        },
    ],
    "differential_equation": [
        {
            "title": "OpenStax Calculus Volume 2: Introduction to Differential Equations",
            "url": "https://openstax.org/books/calculus-volume-2/pages/4-introduction",
            "description": "覆盖微分方程基本概念、可分离变量方程和一阶线性方程。",
        },
        {
            "title": "Paul's Online Math Notes: Differential Equations",
            "url": "https://tutorial.math.lamar.edu/Classes/DE/DE.aspx",
            "description": "提供常微分方程定义、可分离变量、一阶线性、高阶线性方程练习。",
        },
    ],
}


COMMON_SINGLE_VARIABLE_RESOURCES = [
    {
        "title": "MIT OpenCourseWare 18.01SC Single Variable Calculus",
        "url": "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/",
        "description": "MIT 单变量微积分公开课，包含极限、导数、积分及应用的视频、讲义和习题。",
    },
    {
        "title": "Khan Academy Calculus 1",
        "url": "https://www.khanacademy.org/math/calculus-1",
        "description": "面向微积分基础知识的分主题练习，适合作为节点练习后的补充训练。",
    },
    {
        "title": "LibreTexts Calculus Bookshelf",
        "url": "https://math.libretexts.org/Bookshelves/Calculus",
        "description": "开放微积分教材库，覆盖函数、极限、导数、积分、应用和常微分方程基础。",
    },
]


COMMON_DE_RESOURCES = [
    {
        "title": "MIT OpenCourseWare 18.03 Differential Equations",
        "url": "https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/",
        "description": "MIT 常微分方程公开课，适合微分方程节点的系统学习和例题训练。",
    },
    {
        "title": "Khan Academy Differential Equations",
        "url": "https://www.khanacademy.org/math/differential-equations",
        "description": "覆盖可分离变量、一阶线性、二阶线性方程等基础题型。",
    },
    {
        "title": "LibreTexts Differential Equations Bookshelf",
        "url": "https://math.libretexts.org/Bookshelves/Differential_Equations",
        "description": "开放常微分方程教材库，包含概念讲解和典型求解方法。",
    },
]


QUESTION_BANK = {
    "function": [
        {
            "type": "blank",
            "prompt": "求函数 f(x)=sqrt(x-1)/(x+2) 的定义域。",
            "answer": "[1,+∞)",
            "explanation": "要求 x-1>=0 且 x+2!=0，因此 x>=1，分母条件自动满足。",
            "difficulty": 0.35,
        },
        {
            "type": "mcq",
            "prompt": "设 f(x)=2x-1, g(x)=x^2，则 (f∘g)(3) 等于多少？",
            "options": ["5", "8", "17", "36"],
            "answer": "C",
            "explanation": "(f∘g)(3)=f(g(3))=f(9)=18-1=17。",
            "difficulty": 0.30,
        },
        {
            "type": "blank",
            "prompt": "若 f(x)=ln(x-2)，则 f 的定义域是 _______。",
            "answer": "(2,+∞)",
            "explanation": "对数函数要求 x-2>0。",
            "difficulty": 0.32,
        },
    ],
    "limit": [
        {
            "type": "blank",
            "prompt": "计算极限 lim_{x->2} (x^2-4)/(x-2)。",
            "answer": "4",
            "explanation": "因式分解为 (x-2)(x+2)/(x-2)，约去后取 x=2。",
            "difficulty": 0.35,
        },
        {
            "type": "mcq",
            "prompt": "下列哪个极限等于 1？",
            "options": ["lim_{x->0} sin x / x", "lim_{x->0} x/sin(2x)", "lim_{x->0} (1-cos x)/x", "lim_{x->∞} x/(x+1)^2"],
            "answer": "A",
            "explanation": "第一个重要极限为 lim_{x->0} sin x/x=1。",
            "difficulty": 0.36,
        },
        {
            "type": "blank",
            "prompt": "当 x->0 时，sin x 与 x 是 _______ 无穷小。",
            "answer": "等价",
            "explanation": "因为 lim_{x->0} sin x/x=1。",
            "difficulty": 0.30,
        },
    ],
    "continuity": [
        {
            "type": "blank",
            "prompt": "若 f(x)=x^2 (x!=1), f(1)=a 在 x=1 连续，则 a=_______。",
            "answer": "1",
            "explanation": "连续要求 f(1)=lim_{x->1}x^2=1。",
            "difficulty": 0.34,
        },
        {
            "type": "mcq",
            "prompt": "函数 f(x)=1/x 在 x=0 处属于哪类间断？",
            "options": ["可去间断", "跳跃间断", "无穷间断", "连续"],
            "answer": "C",
            "explanation": "x->0 时函数值无界，是无穷间断。",
            "difficulty": 0.35,
        },
        {
            "type": "mcq",
            "prompt": "闭区间上连续函数一定具备哪项性质？",
            "options": ["处处可导", "必有最大值和最小值", "必为单调函数", "没有零点"],
            "answer": "B",
            "explanation": "闭区间连续函数有界且能取到最大值和最小值。",
            "difficulty": 0.38,
        },
    ],
    "derivative": [
        {
            "type": "blank",
            "prompt": "求导：y=x^3 sin x，则 y'=_______。",
            "answer": "3x^2 sin x+x^3 cos x",
            "explanation": "使用乘积求导法则。",
            "difficulty": 0.45,
        },
        {
            "type": "blank",
            "prompt": "求导：y=ln(1+x^2)，则 y'=_______。",
            "answer": "2x/(1+x^2)",
            "explanation": "使用链式法则，外层 ln u 的导数为 u'/u。",
            "difficulty": 0.42,
        },
        {
            "type": "mcq",
            "prompt": "曲线 y=x^2 在 x=1 处切线斜率是多少？",
            "options": ["0", "1", "2", "4"],
            "answer": "C",
            "explanation": "y'=2x，代入 x=1 得斜率 2。",
            "difficulty": 0.30,
        },
    ],
    "differential": [
        {
            "type": "blank",
            "prompt": "若 y=x^2，则 dy=_______。",
            "answer": "2x dx",
            "explanation": "dy=f'(x)dx。",
            "difficulty": 0.32,
        },
        {
            "type": "mcq",
            "prompt": "用微分近似计算 sqrt(4.04)，最接近的结果是？",
            "options": ["2.01", "2.02", "2.04", "2.10"],
            "answer": "A",
            "explanation": "在 x=4 处，d(sqrt x)=dx/(2sqrt x)=0.04/4=0.01，所以约为 2.01。",
            "difficulty": 0.48,
        },
        {
            "type": "blank",
            "prompt": "函数增量 Δy 的线性主部通常写作 _______。",
            "answer": "dy",
            "explanation": "微分 dy 是函数增量的线性主部。",
            "difficulty": 0.28,
        },
    ],
    "application_derivative": [
        {
            "type": "blank",
            "prompt": "函数 f(x)=x^3-3x 的驻点为 x=_______。",
            "answer": "-1,1",
            "explanation": "f'(x)=3x^2-3=3(x^2-1)，令其为 0 得 x=±1。",
            "difficulty": 0.45,
        },
        {
            "type": "mcq",
            "prompt": "f''(x)>0 在某区间内通常说明曲线在该区间内如何？",
            "options": ["凹向下", "凹向上", "恒为负", "不可导"],
            "answer": "B",
            "explanation": "二阶导数为正表示曲线凹向上。",
            "difficulty": 0.36,
        },
        {
            "type": "blank",
            "prompt": "用洛必达法则计算 lim_{x->0} (e^x-1)/x = _______。",
            "answer": "1",
            "explanation": "分子分母同时求导，得到 lim e^x/1=1。",
            "difficulty": 0.40,
        },
    ],
    "indefinite_integral": [
        {
            "type": "blank",
            "prompt": "计算不定积分 ∫2x dx。",
            "answer": "x^2+C",
            "explanation": "x^2 的导数是 2x，不定积分需加任意常数 C。",
            "difficulty": 0.30,
        },
        {
            "type": "blank",
            "prompt": "计算 ∫2x cos(x^2) dx。",
            "answer": "sin(x^2)+C",
            "explanation": "令 u=x^2，则 du=2x dx。",
            "difficulty": 0.45,
        },
        {
            "type": "mcq",
            "prompt": "不定积分 ∫f(x)dx 的结果通常差一个什么量？",
            "options": ["任意常数 C", "固定整数 1", "自变量 x", "积分下限"],
            "answer": "A",
            "explanation": "同一导函数对应一族相差常数的原函数。",
            "difficulty": 0.25,
        },
    ],
    "technique_integral": [
        {
            "type": "blank",
            "prompt": "计算 ∫x e^x dx。",
            "answer": "(x-1)e^x+C",
            "explanation": "分部积分取 u=x, dv=e^x dx。",
            "difficulty": 0.52,
        },
        {
            "type": "blank",
            "prompt": "计算 ∫1/(x^2-1) dx。",
            "answer": "1/2 ln|(x-1)/(x+1)|+C",
            "explanation": "将 1/(x^2-1) 分解为 1/2·1/(x-1)-1/2·1/(x+1)。",
            "difficulty": 0.58,
        },
        {
            "type": "mcq",
            "prompt": "积分 ∫x cos x dx 更适合优先采用哪种方法？",
            "options": ["分部积分法", "夹逼准则", "特征方程法", "二分法"],
            "answer": "A",
            "explanation": "多项式与三角函数乘积通常适合分部积分。",
            "difficulty": 0.40,
        },
    ],
    "definite_integral": [
        {
            "type": "blank",
            "prompt": "计算定积分 ∫_0^1 x^2 dx。",
            "answer": "1/3",
            "explanation": "原函数为 x^3/3，代入上下限得 1/3。",
            "difficulty": 0.32,
        },
        {
            "type": "blank",
            "prompt": "求 d/dx ∫_0^{x^2} cos t dt。",
            "answer": "2x cos(x^2)",
            "explanation": "由微积分基本定理和链式法则得到。",
            "difficulty": 0.48,
        },
        {
            "type": "mcq",
            "prompt": "若 f(x)>=0，则 ∫_a^b f(x)dx 可解释为哪种几何量？",
            "options": ["曲线下方与 x 轴围成的面积", "曲线斜率", "函数定义域", "函数反函数"],
            "answer": "A",
            "explanation": "非负函数定积分对应曲边梯形面积。",
            "difficulty": 0.28,
        },
    ],
    "improper_integral": [
        {
            "type": "blank",
            "prompt": "判断并计算 ∫_1^∞ 1/x^2 dx。",
            "answer": "收敛，值为1",
            "explanation": "∫_1^b x^-2 dx=1-1/b，令 b->∞ 得 1。",
            "difficulty": 0.45,
        },
        {
            "type": "mcq",
            "prompt": "反常积分 ∫_1^∞ 1/x dx 的敛散性是？",
            "options": ["收敛", "发散", "等于 0", "无法定义被积函数"],
            "answer": "B",
            "explanation": "∫_1^b 1/x dx=ln b，b->∞ 时发散。",
            "difficulty": 0.38,
        },
        {
            "type": "blank",
            "prompt": "p-积分 ∫_1^∞ 1/x^p dx 收敛的条件是 p _______ 1。",
            "answer": ">",
            "explanation": "无穷区间 p-积分在 p>1 时收敛。",
            "difficulty": 0.36,
        },
    ],
    "integral_application": [
        {
            "type": "blank",
            "prompt": "求 y=x 与 y=x^2 在 [0,1] 上围成的面积。",
            "answer": "1/6",
            "explanation": "面积为 ∫_0^1 (x-x^2)dx=1/2-1/3=1/6。",
            "difficulty": 0.45,
        },
        {
            "type": "blank",
            "prompt": "曲线 y=x, 0<=x<=1 绕 x 轴旋转所得旋转体体积为 _______。",
            "answer": "π/3",
            "explanation": "用圆盘法，V=π∫_0^1 x^2 dx=π/3。",
            "difficulty": 0.48,
        },
        {
            "type": "mcq",
            "prompt": "变力 F(x) 沿直线做功通常应计算什么？",
            "options": ["∫_a^b F(x)dx", "F(a)+F(b)", "F'(x)", "F(x)/x"],
            "answer": "A",
            "explanation": "变力做功由力对位移的积分给出。",
            "difficulty": 0.34,
        },
    ],
    "differential_equation": [
        {
            "type": "blank",
            "prompt": "求解可分离变量方程 dy/dx=xy 的通解。",
            "answer": "y=C e^(x^2/2)",
            "explanation": "dy/y=x dx，积分得 ln|y|=x^2/2+C。",
            "difficulty": 0.52,
        },
        {
            "type": "mcq",
            "prompt": "一阶线性微分方程 y'+p(x)y=q(x) 的常用解法是？",
            "options": ["积分因子法", "夹逼准则", "部分分式法", "罗尔定理"],
            "answer": "A",
            "explanation": "一阶线性方程通常乘以积分因子化为乘积导数。",
            "difficulty": 0.38,
        },
        {
            "type": "blank",
            "prompt": "常系数方程 y''-3y'+2y=0 的特征根为 _______。",
            "answer": "1,2",
            "explanation": "特征方程 r^2-3r+2=0，解得 r=1,2。",
            "difficulty": 0.48,
        },
    ],
}


def _power_label(power: int) -> str:
    if power == 0:
        return "1"
    if power == 1:
        return "x"
    return f"x^{power}"


def _resources_for(topic: str) -> list[dict[str, str]]:
    resources = list(RESOURCE_BANK[topic])
    common = COMMON_DE_RESOURCES if topic == "differential_equation" else COMMON_SINGLE_VARIABLE_RESOURCES
    for item in common:
        if len(resources) >= 5:
            break
        resources.append(item)
    return resources[:5]


def _generated_questions(topic: str) -> list[dict[str, object]]:
    items = list(QUESTION_BANK[topic])
    needed = 20 - len(items)
    for idx in range(needed):
        n = idx + 2
        if topic == "function":
            value = 2 * n * n
            items.append(
                {
                    "type": "blank",
                    "prompt": f"设 f(x)=x^2+{n}x，求 f({n})。",
                    "answer": str(value),
                    "explanation": f"f({n})={n}^2+{n}*{n}={value}。",
                    "difficulty": 0.30,
                }
            )
        elif topic == "limit":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"计算极限 lim_{{x->{n}}} (x^2-{n*n})/(x-{n})。",
                    "answer": str(2 * n),
                    "explanation": f"分子分解为 (x-{n})(x+{n})，约去后取极限得 {2*n}。",
                    "difficulty": 0.38,
                }
            )
        elif topic == "continuity":
            value = 2 * n
            items.append(
                {
                    "type": "blank",
                    "prompt": f"若 f(x)=x+{n} (x!={n}), f({n})=c 在 x={n} 连续，求 c。",
                    "answer": str(value),
                    "explanation": f"连续要求 c=lim_{{x->{n}}}(x+{n})={value}。",
                    "difficulty": 0.36,
                }
            )
        elif topic == "derivative":
            coef = n + 1
            items.append(
                {
                    "type": "blank",
                    "prompt": f"求导：y=x^{coef}。",
                    "answer": f"{coef}{_power_label(coef - 1)}",
                    "explanation": f"幂函数求导公式：(x^{coef})'={coef}x^{coef-1}。",
                    "difficulty": 0.32,
                }
            )
        elif topic == "differential":
            coef = n + 1
            items.append(
                {
                    "type": "blank",
                    "prompt": f"若 y=x^{coef}，写出 dy。",
                    "answer": f"{coef}{_power_label(coef - 1)} dx",
                    "explanation": "dy=y' dx，先按幂函数求导。",
                    "difficulty": 0.34,
                }
            )
        elif topic == "application_derivative":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"函数 f(x)=x^2-{2*n}x 的最小值点横坐标是 _______。",
                    "answer": str(n),
                    "explanation": f"f'(x)=2x-{2*n}，令 f'(x)=0 得 x={n}，且二次项系数为正。",
                    "difficulty": 0.42,
                }
            )
        elif topic == "indefinite_integral":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"计算不定积分 ∫{n}x^{n-1} dx。",
                    "answer": f"x^{n}+C",
                    "explanation": f"因为 (x^{n})'={n}x^{n-1}。",
                    "difficulty": 0.35,
                }
            )
        elif topic == "technique_integral":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"计算不定积分 ∫{n}x e^x dx。",
                    "answer": f"{n}(x-1)e^x+C",
                    "explanation": "由 ∫x e^x dx=(x-1)e^x+C，再乘常数系数。",
                    "difficulty": 0.52,
                }
            )
        elif topic == "definite_integral":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"计算定积分 ∫_0^1 {n}x^{n-1} dx。",
                    "answer": "1",
                    "explanation": f"原函数为 x^{n}，代入 0 和 1 得 1。",
                    "difficulty": 0.36,
                }
            )
        elif topic == "improper_integral":
            p = n + 1
            items.append(
                {
                    "type": "blank",
                    "prompt": f"计算反常积分 ∫_1^∞ 1/x^{p} dx。",
                    "answer": f"1/{p-1}",
                    "explanation": f"p={p}>1，积分收敛，值为 1/(p-1)=1/{p-1}。",
                    "difficulty": 0.45,
                }
            )
        elif topic == "integral_application":
            numerator = n - 1
            denominator = 2 * (n + 1)
            items.append(
                {
                    "type": "blank",
                    "prompt": f"求 y=x 与 y=x^{n} 在 [0,1] 上围成的面积。",
                    "answer": f"{numerator}/{denominator}",
                    "explanation": f"面积为 ∫_0^1 (x-x^{n})dx=1/2-1/{n+1}={numerator}/{denominator}。",
                    "difficulty": 0.48,
                }
            )
        elif topic == "differential_equation":
            items.append(
                {
                    "type": "blank",
                    "prompt": f"求解微分方程 y'={n}y 的通解。",
                    "answer": f"y=C e^({n}x)",
                    "explanation": f"分离变量得 dy/y={n}dx，积分后得到 y=C e^({n}x)。",
                    "difficulty": 0.46,
                }
            )
    return items[:20]


KEYWORD_RULES = [
    ("differential_equation", ["微分方程", "齐次方程", "伯努利", "欧拉方程", "降阶", "特征方程"]),
    ("integral_application", ["定积分的应用", "几何学", "物理学", "元素法", "面积", "体积", "弧长", "水压力", "引力", "功"]),
    ("improper_integral", ["反常积分", "瑕积分", "Γ函数"]),
    ("definite_integral", ["定积分", "积分上限", "牛顿", "莱布尼茨", "微积分基本"]),
    ("technique_integral", ["分部积分", "有理函数", "积分表", "第二类换元", "换元积分法", "可化为有理"]),
    ("indefinite_integral", ["不定积分", "原函数", "基本积分表", "换元积分"]),
    ("application_derivative", ["中值定理", "洛必达", "泰勒", "单调", "凹凸", "极值", "最值", "图形", "曲率", "近似解", "二分法", "切线法", "割线法"]),
    ("differential", ["微分"]),
    ("derivative", ["导数", "求导", "高阶导数", "隐函数", "参数方程", "相关变化率", "可导"]),
    ("continuity", ["连续", "间断", "闭区间", "介值", "零点", "一致连续"]),
    ("limit", ["极限", "无穷小", "无穷大", "夹逼", "单调有界", "重要极限", "收敛"]),
    ("function", ["映射", "函数", "反函数", "复合函数", "初等函数"]),
]


def _topic_for(kp: KnowledgePoint) -> str:
    title = str(kp.title or "")
    text = f"{title} {kp.description}"
    for topic, keywords in KEYWORD_RULES:
        if any(keyword in title for keyword in keywords):
            return topic
    for topic, keywords in KEYWORD_RULES:
        if any(keyword in text for keyword in keywords):
            return topic
    return "function"


def _resource_type(value: str) -> ResourceType:
    return ResourceType(value)


def _add_resource(session: Session, *, kp: KnowledgePoint, item: dict[str, str], index: int) -> None:
    tags = f"{SEED_TAG},{kp.code},{_topic_for(kp)}"
    row = LearningResource(
        subject=kp.subject,
        grade=kp.grade,
        kp_id=int(kp.id),
        title=item["title"],
        url=item["url"],
        type=_resource_type("link"),
        category="learning" if index == 0 else "recommend",
        description=item["description"],
        tags=tags,
        detected_resource_type="link",
        preview_type="external_link",
        preview_status="ready",
        source_kind="external",
        original_file_url=item["url"],
        converted_preview_url="",
    )
    session.add(row)


def _max_assignment_order(session: Session, kp_id: int) -> int:
    rows = session.exec(select(KpQuestionAssignment).where(KpQuestionAssignment.kp_id == kp_id)).all()
    best = 0
    for row in rows:
        try:
            best = max(best, int(row.order or 0))
        except (TypeError, ValueError):
            continue
    return best


def _add_question(session: Session, *, kp: KnowledgePoint, order: int, item: dict[str, object]) -> None:
    options = item.get("options", [])
    tags = f"{SEED_TAG},{kp.code},{_topic_for(kp)}"
    prompt = f"【{kp.title}】{item['prompt']}"
    row = Question(
        subject=kp.subject,
        grade=kp.grade,
        kp_id=int(kp.id),
        type=str(item["type"]),
        prompt=prompt,
        options_json=json.dumps(options, ensure_ascii=False),
        answer=str(item["answer"]),
        explanation=str(item.get("explanation", "")),
        difficulty=float(item.get("difficulty", 0.5)),
        source="高等数学演示题库：同济版高等数学知识点自编题",
        tags=tags,
        version=QUESTION_VERSION,
        cognitive_level="apply",
        ability_subtags="计算能力,概念理解,应用建模",
    )
    session.add(row)
    session.flush()
    session.add(KpQuestionAssignment(kp_id=int(kp.id), question_id=int(row.id), order=order))


def _task_plan(kp: KnowledgePoint, topic: str) -> list[dict[str, str]]:
    return [
        {
            "title": f"{TASK_TITLE_PREFIX}{kp.title}核心概念梳理",
            "description": f"结合节点“{kp.title}”对应教材与公开课资源，梳理定义、定理、公式和适用条件，形成 1 份概念卡片，并标出本节点最容易混淆的 2 个点。",
            "link_url": _resources_for(topic)[0]["url"],
        },
        {
            "title": f"{TASK_TITLE_PREFIX}{kp.title}典型题型训练",
            "description": f"完成本节点练习题中的基础题、计算题和应用题各至少 1 题，总结该知识点的标准解题步骤与易错点，适合课堂演示展示学习闭环。",
            "link_url": _resources_for(topic)[1]["url"],
        },
    ]


def _upsert_task(session: Session, *, kp: KnowledgePoint, sort_order: int, item: dict[str, str]) -> None:
    row = session.exec(select(KpTask).where(KpTask.kp_id == int(kp.id), KpTask.title == item["title"])).first()
    if row is None:
        row = KpTask(
            subject=kp.subject,
            grade=kp.grade,
            kp_id=int(kp.id),
            title=item["title"],
        )
    row.description = item["description"]
    row.link_url = item["link_url"]
    row.type = KpTaskType.task
    row.sort_order = sort_order
    session.add(row)


def _upsert_quiz(session: Session, *, kp: KnowledgePoint, topic: str) -> None:
    quiz = session.exec(select(Quiz).where(Quiz.kp_id == int(kp.id))).first()
    if quiz is None:
        quiz = Quiz(subject=kp.subject, grade=kp.grade, kp_id=int(kp.id), pass_accuracy=0.8)
        session.add(quiz)
        session.flush()

    existing_items = session.exec(select(QuizItem).where(QuizItem.quiz_id == int(quiz.id))).all()
    for row in existing_items:
        if str(row.prompt or "").startswith(QUIZ_PROMPT_PREFIX):
            session.delete(row)
    session.flush()

    quiz_items = _generated_questions(topic)[:5]
    for index, item in enumerate(quiz_items, start=1):
        session.add(
            QuizItem(
                quiz_id=int(quiz.id),
                type=str(item["type"]),
                prompt=f"{QUIZ_PROMPT_PREFIX}[{kp.title}][{index}] {item['prompt']}",
                options_json=json.dumps(item.get("options", []), ensure_ascii=False),
                answer=str(item["answer"]),
                explanation=str(item.get("explanation", "")),
                key_item=index <= 2,
            )
        )


def seed() -> None:
    with Session(engine) as session:
        kps = session.exec(
            select(KnowledgePoint)
            .where(KnowledgePoint.code.like("HM-%"))
            .order_by(KnowledgePoint.code)
        ).all()
        kp_ids = [int(kp.id) for kp in kps if kp.id is not None]
        if not kp_ids:
            raise SystemExit("没有找到高等数学 HM-* 知识点，未写入任何内容。")

        seeded_questions = session.exec(
            select(Question).where(Question.kp_id.in_(kp_ids), Question.version == QUESTION_VERSION)
        ).all()
        question_ids = [int(q.id) for q in seeded_questions if q.id is not None]
        if question_ids:
            session.exec(delete(PracticeAttempt).where(PracticeAttempt.question_id.in_(question_ids)))
            session.exec(delete(ReviewSchedule).where(ReviewSchedule.question_id.in_(question_ids)))
            session.exec(delete(KpQuestionAssignment).where(KpQuestionAssignment.question_id.in_(question_ids)))
            for row in seeded_questions:
                session.delete(row)

        existing_quizzes = session.exec(select(Quiz).where(Quiz.kp_id.in_(kp_ids))).all()
        quiz_ids = [int(q.id) for q in existing_quizzes if q.id is not None]
        if quiz_ids:
            seeded_quiz_items = session.exec(select(QuizItem).where(QuizItem.quiz_id.in_(quiz_ids))).all()
            seeded_quiz_item_ids = [int(row.id) for row in seeded_quiz_items if row.id is not None and str(row.prompt or "").startswith(QUIZ_PROMPT_PREFIX)]
            if seeded_quiz_item_ids:
                session.exec(delete(QuizAttempt).where(QuizAttempt.quiz_id.in_(quiz_ids)))
                for row in seeded_quiz_items:
                    if row.id is not None and int(row.id) in seeded_quiz_item_ids:
                        session.delete(row)

        for row in session.exec(select(KpTask).where(KpTask.kp_id.in_(kp_ids))).all():
            if str(row.title or "").startswith(TASK_TITLE_PREFIX):
                session.delete(row)

        for row in session.exec(select(LearningResource).where(LearningResource.kp_id.in_(kp_ids))).all():
            if SEED_TAG in (row.tags or ""):
                session.delete(row)
        session.commit()

        generated = defaultdict(lambda: {"resources": 0, "questions": 0})
        for kp in kps:
            if kp.id is None:
                continue
            topic = _topic_for(kp)
            for index, item in enumerate(_resources_for(topic)):
                _add_resource(session, kp=kp, item=item, index=index)
                generated[str(kp.code)]["resources"] += 1
            start_order = _max_assignment_order(session, int(kp.id))
            for index, item in enumerate(_generated_questions(topic), start=1):
                _add_question(session, kp=kp, order=start_order + index, item=item)
                generated[str(kp.code)]["questions"] += 1
            for index, item in enumerate(_task_plan(kp, topic), start=1):
                _upsert_task(session, kp=kp, sort_order=index, item=item)
            _upsert_quiz(session, kp=kp, topic=topic)
            kp.practice_total = max(20, int(generated[str(kp.code)]["questions"]))
            session.add(kp)

        session.commit()

        visible_count = sum(1 for kp in kps if kp.subject == SUBJECT and kp.grade == GRADE)
        hidden_count = len(kps) - visible_count
        print("已生成高等数学图谱演示内容：")
        print(f"知识点 {len(kps)} 个，资源 {sum(v['resources'] for v in generated.values())} 条，练习题 {sum(v['questions'] for v in generated.values())} 题。")
        print(f"当前图谱可见节点 {visible_count} 个，归档隐藏节点 {hidden_count} 个。")
        for kp in kps[:10]:
            info = generated[str(kp.code)]
            print(f"{kp.code} {kp.title}: 资源 {info['resources']} 条，练习题 {info['questions']} 题")
        if len(kps) > 10:
            print(f"... 其余 {len(kps) - 10} 个节点同样已配置。")


if __name__ == "__main__":
    seed()
