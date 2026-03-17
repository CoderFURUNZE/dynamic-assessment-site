# 计算机网络三阶段演示数据包

## 1. 数据包用途
用于快速演示“教师按阶段导入数据 -> 系统生成阶段评价与画像变化 -> 学生端查看结果”的完整链路。

## 2. 适用前提
1. 已执行全量种子：`POST /api/admin/seed/full` 或运行 `backend/scripts/init_system.py`（默认会 seed）。
2. 存在课程 `计算机网络`（`CN`）。
3. 存在学生账号：`student1`、`student2`、`student3`。

## 3. 文件说明
每个阶段 6 份 CSV，对应：
- `video`
- `assignment`
- `quiz`
- `attendance`
- `task`
- `participation`

阶段文件命名：
- `stage1_*.csv`
- `stage2_*.csv`
- `stage3_*.csv`

## 4. 教师端导入顺序（推荐）
1. 在教师端「阶段管理」创建 3 个阶段：
   - 阶段1：基础认知
   - 阶段2：结构理解
   - 阶段3：综合应用
2. 在「阶段数据导入」中，按阶段依次导入：
   - `stage1_video.csv` -> `stage1_assignment.csv` -> `stage1_quiz.csv` -> `stage1_attendance.csv` -> `stage1_task.csv` -> `stage1_participation.csv`
   - 阶段2同理
   - 阶段3同理
3. 每次导入后，系统会自动触发阶段快照重算。

## 5. 预期演示效果
- `student1`：阶段评分持续上升，呈“进步”趋势。
- `student2`：稳步上升，偏“踏实学习型”。
- `student3`：低完成+迟交+缺勤，风险提示更明显。

## 6. 常见问题
- 导入报 `kp_code not found`：说明知识点种子未准备好，请先执行全量 seed。
- 导入报 `student not found`：确认学生账号是否为 `student1~3`。
- 看不到阶段结果：确认导入时选中了正确课程和阶段。
