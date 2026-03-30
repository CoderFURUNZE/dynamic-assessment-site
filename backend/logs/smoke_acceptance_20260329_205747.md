# 验收冒烟测试报告

- 生成时间: 2026-03-29 20:57:48
- 总数: 29
- 通过: 29
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
   - payload={'id': 1, 'username': 'admin', 'role': 'admin', 'active': True, 'full_name': '系统管理员', 'student_no': '', 'class_name': '', 'phone': None}
8. [PASS] teacher 获取 /api/auth/me
   - status=200, expected=(200,)
9. [PASS] teacher /api/auth/me 结构
   - payload={'id': 2, 'username': 'teacher1', 'role': 'teacher', 'active': True, 'full_name': '王敏', 'student_no': '', 'class_name': '', 'phone': None}
10. [PASS] student 获取 /api/auth/me
   - status=200, expected=(200,)
11. [PASS] student /api/auth/me 结构
   - payload={'id': 3, 'username': 'student1', 'role': 'student', 'active': True, 'full_name': '李晨', 'student_no': '2026001', 'class_name': '计科2301', 'phone': None}
12. [PASS] 教师访问管理员课程接口应被拒绝 /api/admin/courses
   - status=403, expected=(403,)
13. [PASS] 管理员课程管理列表 /api/admin/courses
   - status=200, expected=(200,)
14. [PASS] 管理员用户列表 /api/admin/users
   - status=200, expected=(200,)
15. [PASS] 管理员分析总览 /api/admin/analytics/overview
   - status=200, expected=(200,)
16. [PASS] 教师课程列表 /api/graph/courses
   - status=200, expected=(200,)
17. [PASS] 教师维度树 /api/portrait/dimensions/tree
   - status=200, expected=(200,)
18. [PASS] 教师阶段列表 /api/stages/courses/{course_id}
   - status=200, expected=(200,)
19. [PASS] 教师课程画像指标 /api/portrait/course-selection
   - status=200, expected=(200,)
20. [PASS] 学生已选课程列表 /api/graph/courses
   - status=200, expected=(200,)
21. [PASS] 学生可学习课程列表 /api/graph/available-courses
   - status=200, expected=(200,)
22. [PASS] 教师课程分析 /api/admin/analytics/overview
   - status=200, expected=(200,)
23. [PASS] 教师分析含班级练习认知汇总字段
   - ability_practice_cohort present
24. [PASS] 学生画像 /api/eval/profile
   - status=200, expected=(200,)
25. [PASS] 学生画像含 ability_practice_stats
   - ok
26. [PASS] 学生图谱地图 /api/graph/map
   - status=200, expected=(200,)
27. [PASS] 学生节点详情 /api/graph/node/{kp_id}
   - status=200, expected=(200,)
28. [PASS] 练习下一题 /api/practice/next
   - status=200, expected=(200,)
29. [PASS] 练习 next 响应结构
   - ok
