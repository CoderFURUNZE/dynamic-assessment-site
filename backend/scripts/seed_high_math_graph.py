from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.db.models import (
    ChapterEdge,
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
        "code": "HM-01-01",
        "chapter": "第一章 函数与极限",
        "title": "映射与函数",
        "description": "理解映射、函数及其基本表示方法，为极限与微积分学习建立对象基础。",
        "x": 120,
        "y": -600,
        "children": [
            ("HM-01-01-01", "映射", "理解映射的定义、对应关系和基本表达。"),
            ("HM-01-01-02", "函数", "掌握函数概念、定义域、值域、表示法和常见性质。"),
        ],
    },
    {
        "code": "HM-01-02",
        "chapter": "第一章 函数与极限",
        "title": "数列的极限",
        "description": "建立数列极限的精确定义，理解收敛数列的基本性质。",
        "x": 360,
        "y": -600,
        "children": [
            ("HM-01-02-01", "数列极限的定义", "用 epsilon-N 语言刻画数列趋近过程。"),
            ("HM-01-02-02", "收敛数列的性质", "掌握唯一性、有界性、保号性和四则运算等性质。"),
        ],
    },
    {
        "code": "HM-01-03",
        "chapter": "第一章 函数与极限",
        "title": "函数的极限",
        "description": "掌握函数极限的定义、左右极限及其运算性质。",
        "x": 600,
        "y": -600,
        "children": [
            ("HM-01-03-01", "函数极限的定义", "理解自变量趋于一点或无穷时函数值的趋近。"),
            ("HM-01-03-02", "函数极限的性质", "掌握唯一性、局部有界性、保号性和四则运算法则。"),
        ],
    },
    {
        "code": "HM-01-04",
        "chapter": "第一章 函数与极限",
        "title": "无穷小与无穷大",
        "description": "理解无穷小、无穷大的概念及其与函数极限的关系。",
        "x": 840,
        "y": -600,
        "children": [
            ("HM-01-04-01", "无穷小", "理解无穷小的定义、性质及其在极限计算中的作用。"),
            ("HM-01-04-02", "无穷大", "理解无穷大的定义及其与无穷小的倒数关系。"),
        ],
    },
    {
        "code": "HM-01-05",
        "chapter": "第一章 函数与极限",
        "title": "极限运算法则",
        "description": "掌握极限的四则运算和复合运算规则。",
        "x": 1080,
        "y": -600,
        "children": [
            ("HM-01-05-01", "极限四则运算", "利用和、差、积、商法则计算基础极限。"),
        ],
    },
    {
        "code": "HM-01-06",
        "chapter": "第一章 函数与极限",
        "title": "极限存在准则与两个重要极限",
        "description": "掌握夹逼准则、单调有界准则和两个重要极限。",
        "x": 1320,
        "y": -600,
        "children": [
            ("HM-01-06-01", "夹逼准则", "通过上下界函数控制目标函数极限。"),
            ("HM-01-06-02", "单调有界准则", "用单调性和有界性判断数列极限存在。"),
            ("HM-01-06-03", "两个重要极限", "掌握 sin x / x 和 (1 + 1 / x)^x 型极限。"),
        ],
    },
    {
        "code": "HM-01-07",
        "chapter": "第一章 函数与极限",
        "title": "无穷小的比较",
        "description": "掌握等价无穷小、同阶无穷小、高阶无穷小的比较方法。",
        "x": 1560,
        "y": -600,
        "children": [
            ("HM-01-07-01", "无穷小阶的比较", "用比值极限判断无穷小之间的阶数关系。"),
        ],
    },
    {
        "code": "HM-01-08",
        "chapter": "第一章 函数与极限",
        "title": "函数的连续性与间断点",
        "description": "理解连续函数定义、左右连续和常见间断点类型。",
        "x": 1800,
        "y": -600,
        "children": [
            ("HM-01-08-01", "函数的连续性", "掌握一点连续、区间连续和连续函数运算。"),
            ("HM-01-08-02", "函数的间断点", "识别可去、跳跃、无穷和振荡间断点。"),
        ],
    },
    {
        "code": "HM-01-09",
        "chapter": "第一章 函数与极限",
        "title": "连续函数的运算与初等函数的连续性",
        "description": "掌握连续函数四则运算、复合运算和初等函数连续性。",
        "x": 2040,
        "y": -600,
        "children": [
            ("HM-01-09-01", "连续函数的和差积商", "判断由连续函数组合得到的新函数连续性。"),
            ("HM-01-09-02", "反函数与复合函数的连续性", "理解反函数、复合函数在连续性中的传递规则。"),
            ("HM-01-09-03", "初等函数的连续性", "利用基本初等函数连续性处理极限与函数性质。"),
        ],
    },
    {
        "code": "HM-01-10",
        "chapter": "第一章 函数与极限",
        "title": "闭区间上连续函数的性质",
        "description": "掌握闭区间连续函数的重要定理及其应用。",
        "x": 2280,
        "y": -600,
        "children": [
            ("HM-01-10-01", "有界性与最大最小值定理", "理解闭区间连续函数必有界并能取到最值。"),
            ("HM-01-10-02", "零点定理与介值定理", "利用符号变化和连续性证明方程有根或取值存在。"),
            ("HM-01-10-03", "一致连续性", "理解闭区间连续函数一致连续的结论。"),
        ],
    },
    {
        "code": "HM-02-01",
        "chapter": "第二章 导数与微分",
        "title": "导数概念",
        "description": "从变化率问题出发理解导数定义、几何意义及可导与连续的关系。",
        "x": 120,
        "y": -360,
        "children": [
            ("HM-02-01-01", "导数引例", "通过速度、切线斜率等问题建立导数直观。"),
            ("HM-02-01-02", "导数的定义", "用差商极限定义函数在一点的导数。"),
            ("HM-02-01-03", "导数的几何意义", "理解导数表示曲线切线斜率。"),
            ("HM-02-01-04", "函数可导性与连续性的关系", "掌握可导必连续、连续不一定可导。"),
        ],
    },
    {
        "code": "HM-02-02",
        "chapter": "第二章 导数与微分",
        "title": "函数的求导法则",
        "description": "掌握常用求导规则和基本导数公式。",
        "x": 360,
        "y": -360,
        "children": [
            ("HM-02-02-01", "函数和差积商的求导法则", "计算由基本函数四则组合得到的导数。"),
            ("HM-02-02-02", "反函数的求导法则", "利用反函数导数公式处理反三角等函数。"),
            ("HM-02-02-03", "复合函数的求导法则", "掌握链式法则及多层复合函数求导。"),
            ("HM-02-02-04", "基本求导法则与导数公式", "熟练应用基本初等函数导数公式。"),
        ],
    },
    {
        "code": "HM-02-03",
        "chapter": "第二章 导数与微分",
        "title": "高阶导数",
        "description": "理解二阶及更高阶导数的定义、记号和计算方法。",
        "x": 600,
        "y": -360,
        "children": [
            ("HM-02-03-01", "高阶导数的定义", "递推理解高阶导数并掌握常用记号。"),
            ("HM-02-03-02", "高阶导数的计算", "计算多项式、指数、三角等函数的高阶导数。"),
        ],
    },
    {
        "code": "HM-02-04",
        "chapter": "第二章 导数与微分",
        "title": "隐函数及由参数方程确定的函数的导数",
        "description": "掌握隐函数、参数方程求导和相关变化率问题。",
        "x": 840,
        "y": -360,
        "children": [
            ("HM-02-04-01", "隐函数的导数", "对方程两边求导并求出隐函数导数。"),
            ("HM-02-04-02", "参数方程确定函数的导数", "利用参数导数关系求 dy/dx。"),
            ("HM-02-04-03", "相关变化率", "建立变量关系并用导数描述联动变化。"),
        ],
    },
    {
        "code": "HM-02-05",
        "chapter": "第二章 导数与微分",
        "title": "函数的微分",
        "description": "理解微分定义、几何意义、微分公式和近似计算应用。",
        "x": 1080,
        "y": -360,
        "children": [
            ("HM-02-05-01", "微分的定义", "理解微分是函数增量的线性主部。"),
            ("HM-02-05-02", "微分的几何意义", "用切线增量解释函数微分。"),
            ("HM-02-05-03", "基本初等函数微分公式与微分运算法则", "掌握微分形式下的运算规则。"),
            ("HM-02-05-04", "微分在近似计算中的应用", "用微分估算函数值和误差。"),
        ],
    },
    {
        "code": "HM-03-01",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "微分中值定理",
        "description": "掌握罗尔定理、拉格朗日中值定理和柯西中值定理。",
        "x": 120,
        "y": -120,
        "children": [
            ("HM-03-01-01", "罗尔定理", "理解端点函数值相等时导数为零点的存在性。"),
            ("HM-03-01-02", "拉格朗日中值定理", "用平均变化率联系某点瞬时变化率。"),
            ("HM-03-01-03", "柯西中值定理", "推广中值定理并服务于洛必达法则。"),
        ],
    },
    {
        "code": "HM-03-02",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "洛必达法则",
        "description": "用导数比值处理未定式极限。",
        "x": 360,
        "y": -120,
        "children": [
            ("HM-03-02-01", "洛必达法则", "掌握 0/0、无穷/无穷等未定式极限处理。"),
        ],
    },
    {
        "code": "HM-03-03",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "泰勒公式",
        "description": "理解用多项式近似函数的思想和余项表达。",
        "x": 600,
        "y": -120,
        "children": [
            ("HM-03-03-01", "泰勒公式", "掌握带余项的泰勒展开和常用函数展开。"),
        ],
    },
    {
        "code": "HM-03-04",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "函数的单调性与曲线的凹凸性",
        "description": "利用一阶和二阶导数判断函数图形性质。",
        "x": 840,
        "y": -120,
        "children": [
            ("HM-03-04-01", "函数单调性的判定法", "用一阶导数符号判断单调区间。"),
            ("HM-03-04-02", "曲线的凹凸性与拐点", "用二阶导数判断凹凸性并寻找拐点。"),
        ],
    },
    {
        "code": "HM-03-05",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "函数的极值与最大值最小值",
        "description": "掌握函数极值、最值的判定与求解。",
        "x": 1080,
        "y": -120,
        "children": [
            ("HM-03-05-01", "函数的极值及其求法", "利用导数符号变化和二阶导数判断极值。"),
            ("HM-03-05-02", "最大值最小值问题", "结合端点和驻点求闭区间或实际问题最值。"),
        ],
    },
    {
        "code": "HM-03-06",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "函数图形的描绘",
        "description": "综合定义域、单调性、凹凸性、极值和渐近线描绘函数图形。",
        "x": 1320,
        "y": -120,
        "children": [
            ("HM-03-06-01", "函数图形分析", "综合导数工具分析并绘制函数曲线。"),
        ],
    },
    {
        "code": "HM-03-07",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "曲率",
        "description": "理解曲率、曲率圆、曲率半径及相关几何量。",
        "x": 1560,
        "y": -120,
        "children": [
            ("HM-03-07-01", "弧微分", "理解曲线弧长微元的表达。"),
            ("HM-03-07-02", "曲率及其计算公式", "掌握平面曲线曲率计算。"),
            ("HM-03-07-03", "曲率圆与曲率半径", "理解曲率半径和密切圆的几何意义。"),
            ("HM-03-07-04", "曲率中心的计算公式", "计算曲率中心并理解其位置变化。"),
            ("HM-03-07-05", "渐屈线与渐伸线", "了解由曲率中心轨迹和反向构造形成的曲线。"),
        ],
    },
    {
        "code": "HM-03-08",
        "chapter": "第三章 微分中值定理与导数的应用",
        "title": "方程的近似解",
        "description": "掌握二分法、切线法和割线法求方程近似根。",
        "x": 1800,
        "y": -120,
        "children": [
            ("HM-03-08-01", "二分法", "利用区间套和零点定理逼近方程根。"),
            ("HM-03-08-02", "切线法", "用牛顿迭代思想求近似根。"),
            ("HM-03-08-03", "割线法", "用割线近似切线构造迭代。"),
        ],
    },
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
    ("HM-01-01", "HM-01-02"),
    ("HM-01-02", "HM-01-03"),
    ("HM-01-03", "HM-01-04"),
    ("HM-01-04", "HM-01-05"),
    ("HM-01-05", "HM-01-06"),
    ("HM-01-06", "HM-01-07"),
    ("HM-01-07", "HM-01-08"),
    ("HM-01-08", "HM-01-09"),
    ("HM-01-09", "HM-01-10"),
    ("HM-01-10", "HM-02-01"),
    ("HM-02-01", "HM-02-02"),
    ("HM-02-02", "HM-02-03"),
    ("HM-02-02", "HM-02-04"),
    ("HM-02-03", "HM-02-05"),
    ("HM-02-04", "HM-02-05"),
    ("HM-02-05", "HM-03-01"),
    ("HM-03-01", "HM-03-02"),
    ("HM-03-01", "HM-03-03"),
    ("HM-03-03", "HM-03-04"),
    ("HM-03-04", "HM-03-05"),
    ("HM-03-05", "HM-03-06"),
    ("HM-03-04", "HM-03-07"),
    ("HM-03-05", "HM-03-08"),
    ("HM-03-01", "HM-04-01"),
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

VISIBLE_SECTION_PREFIXES = ("HM-01", "HM-02", "HM-03")
HIDDEN_SUBJECT = f"{SUBJECT}-答辩隐藏"


def is_visible_code(code: str) -> bool:
    return code.startswith(VISIBLE_SECTION_PREFIXES)


ACTIVE_SECTIONS = [section for section in SECTIONS if is_visible_code(str(section["code"]))]


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


def archive_hidden_high_math_nodes(session: Session, active_codes: set[str]) -> int:
    active_ids = {
        int(kp.id)
        for kp in session.exec(
            select(KnowledgePoint).where(
                KnowledgePoint.subject == SUBJECT,
                KnowledgePoint.grade == GRADE,
                KnowledgePoint.code.in_(active_codes),
            )
        ).all()
        if kp.id is not None
    }
    active_chapters = {str(section["chapter"]) for section in ACTIVE_SECTIONS}

    hidden_edges = session.exec(select(KnowledgeEdge).where(KnowledgeEdge.subject == SUBJECT, KnowledgeEdge.grade == GRADE)).all()
    for edge in hidden_edges:
        if int(edge.prereq_id) not in active_ids or int(edge.next_id) not in active_ids:
            session.delete(edge)

    hidden_chapter_edges = session.exec(
        select(ChapterEdge).where(ChapterEdge.subject == SUBJECT, ChapterEdge.grade == GRADE)
    ).all()
    for edge in hidden_chapter_edges:
        if edge.source_chapter not in active_chapters or edge.target_chapter not in active_chapters:
            session.delete(edge)

    archived = 0
    stale_kps = session.exec(
        select(KnowledgePoint).where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)
    ).all()
    for kp in stale_kps:
        if kp.code in active_codes:
            continue
        kp.subject = HIDDEN_SUBJECT
        session.add(kp)
        archived += 1
    session.commit()
    return archived


def main() -> None:
    with Session(engine) as session:
        ensure_teacher_access(session)
        code_map: dict[str, int] = {}
        created_or_updated = 0

        active_codes = {str(section["code"]) for section in ACTIVE_SECTIONS}
        for section in ACTIVE_SECTIONS:
            active_codes.update(str(item[0]) for item in section["children"])

        for section in ACTIVE_SECTIONS:
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
        for section in ACTIVE_SECTIONS:
            parent = section["code"]
            children = [item[0] for item in section["children"]]
            for child in children:
                if add_edge(session, code_map, parent, child, RelationType.contains):
                    edge_count += 1
            for source, target in zip(children, children[1:]):
                if add_edge(session, code_map, source, target, RelationType.prerequisite):
                    edge_count += 1

        for source, target in SECTION_PREREQS:
            if source not in code_map or target not in code_map:
                continue
            if add_edge(session, code_map, source, target, RelationType.prerequisite):
                edge_count += 1

        session.commit()
        archived = archive_hidden_high_math_nodes(session, active_codes)
        kp_total = len(session.exec(select(KnowledgePoint).where(KnowledgePoint.subject == SUBJECT, KnowledgePoint.grade == GRADE)).all())
        edge_total = len(session.exec(select(KnowledgeEdge).where(KnowledgeEdge.subject == SUBJECT, KnowledgeEdge.grade == GRADE)).all())
        print(f"seeded subject={SUBJECT} grade={GRADE} touched_kps={created_or_updated} new_edges={edge_count} archived_kps={archived} total_kps={kp_total} total_edges={edge_total}")


if __name__ == "__main__":
    main()
