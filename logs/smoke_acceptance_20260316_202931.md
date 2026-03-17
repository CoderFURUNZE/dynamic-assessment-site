# 验收冒烟测试报告

- 生成时间: 2026-03-16 20:29:32
- 总数: 20
- 通过: 20
- 失败: 0

## 结果明细

1. [PASS] 健康检查 /health
   - status=200, expected=(200,)
2. [PASS] 健康返回值校验
   - payload={'ok': True}
3. [PASS] 管理员登录
   - role=admin
4. [PASS] 教师登录
   - role=teacher
5. [PASS] 学生登录
   - role=student
6. [PASS] admin 获取 /api/auth/me
   - status=200, expected=(200,)
7. [PASS] admin /api/auth/me 结构
   - payload={'id': 2, 'username': 'admin', 'role': 'admin', 'active': True, 'full_name': '', 'student_no': '', 'class_name': '', 'phone': None}
8. [PASS] teacher 获取 /api/auth/me
   - status=200, expected=(200,)
9. [PASS] teacher /api/auth/me 结构
   - payload={'id': 1, 'username': 'teacher1', 'role': 'teacher', 'active': True, 'full_name': '', 'student_no': '', 'class_name': '', 'phone': None}
10. [PASS] student 获取 /api/auth/me
   - status=200, expected=(200,)
11. [PASS] student /api/auth/me 结构
   - payload={'id': 3, 'username': 'student1', 'role': 'student', 'active': True, 'full_name': '', 'student_no': '', 'class_name': '', 'phone': None}
12. [PASS] 教师课程管理列表 /api/admin/courses
   - status=200, expected=(200,)
13. [PASS] 管理员用户列表 /api/admin/users
   - status=200, expected=(200,)
14. [PASS] 管理员分析总览 /api/admin/analytics/overview
   - status=200, expected=(200,)
15. [PASS] 教师课程列表 /api/graph/courses
   - status=200, expected=(200,)
16. [PASS] 教师维度树 /api/portrait/dimensions/tree
   - status=200, expected=(200,)
17. [PASS] 教师阶段列表 /api/stages/courses/{course_id}
   - status=200, expected=(200,)
18. [PASS] 教师课程画像指标 /api/portrait/course-selection
   - status=200, expected=(200,)
19. [PASS] 学生课程列表 /api/graph/courses
   - status=200, expected=(200,)
20. [PASS] 学生图谱地图检查
   - 已跳过：系统无课程数据
