# 高等数学答辩图谱数据来源说明

本数据包由 `backend/scripts/seed_high_math_verified_pack.py` 导入，课程名为“高等数学”，知识点编码前缀为 `HM-V`。

## 数据边界

- 知识点结构：依据国内高校《高等数学》通用教学顺序组织，包括函数极限连续、导数微分、导数应用、不定积分、定积分及应用、常微分方程、无穷级数、空间解析几何、多元函数微分法、重积分与曲线曲面积分、综合达标。
- 资源：只保存可公开访问、可核验的课程或教材页面链接，不下载、不镜像。
- 习题：不冒充外部题库；题目来源字段统一为 `curated_formula_verified`，表示按高等数学基本公式和定理人工整理、可直接验算的原创校验题。
- 学生画像演示数据：`backend/scripts/seed_three_high_math_student_profiles.py` 只用于答辩演示三类学习画像差异，属于系统生成的模拟学习行为数据，不应表述为真实学生历史记录。
- 缺失数据：未找到可靠来源的外部题库、课件原文件、视频文件不填充，不伪造。

## 公开资源来源

- OpenStax Calculus Volume 1: https://openstax.org/books/calculus-volume-1
- OpenStax Calculus Volume 2: https://openstax.org/books/calculus-volume-2
- OpenStax Calculus Volume 3: https://openstax.org/details/books/calculus-volume-3
- MIT OpenCourseWare 18.01SC Single Variable Calculus: https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/
- MIT OpenCourseWare 18.02SC Multivariable Calculus: https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/
- MIT OpenCourseWare 18.03 Differential Equations: https://ocw.mit.edu/courses/18-03-differential-equations-spring-2010/
- Khan Academy Calculus 1: https://www.khanacademy.org/math/calculus-1
- Khan Academy Calculus 2: https://www.khanacademy.org/math/calculus-2
- Khan Academy Multivariable Calculus: https://www.khanacademy.org/math/multivariable-calculus
- Paul’s Online Math Notes Calculus I: https://tutorial.math.lamar.edu/Classes/CalcI/CalcI.aspx
- Paul’s Online Math Notes Calculus II: https://tutorial.math.lamar.edu/Classes/CalcII/CalcII.aspx
- Paul’s Online Math Notes Differential Equations: https://tutorial.math.lamar.edu/Classes/DE/DE.aspx

## 当前导入规模

- 知识点：68
- 前置关系边：76
- 外部资源链接：204
- 练习题：136
- 节点小测：68
- 小测题：136
