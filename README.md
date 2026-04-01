# 动态评价系统（MVP）

FastAPI 后端 + Vue3/Element Plus 前端。

## 后端（Windows / Python 3.11）
```powershell
cd D:\Project\Learning\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

说明：
- 现在也支持在仓库根目录直接执行 `uvicorn app.main:app`。
- 如果使用项目脚本启动，优先执行 `scripts/run_backend.sh`。

默认账号：
- `admin / admin123`
- `teacher1 / teacher123`
- `student1 / student123`

## 数据库（推荐 PostgreSQL）
1) 启动数据库（Docker Compose 示例，包含 postgres + pgAdmin）：
```powershell
cd D:\Project\Learning
docker compose up -d db pgadmin
```

pgAdmin 默认访问：`http://localhost:5050`

2) 配置 `.env` 的 `DATABASE_URL` 指向 Postgres：
```
DATABASE_URL=postgresql+psycopg2://postgres:frz00@localhost:5432/dynamic_assessment
```

3) 初始化/重置数据库并可选导入 Demo：
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset   # 清表后重建并导入 demo
# 只建表，不导入：
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset --no-seed
```

或使用 PowerShell 一键脚本：
```powershell
cd D:\Project\Learning\backend
.\scripts\init_system.ps1 -Reset
.\scripts\init_system.ps1 -Reset -NoSeed
```

说明：
- SQLite 环境下 `--reset` 会删除 sqlite 文件；PostgreSQL 等则执行 drop all tables 再重建。

## SQLite -> PostgreSQL 迁移
若之前使用 sqlite（`backend/app.db`），可执行迁移脚本：
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe .\scripts\migrate_sqlite_to_pg.py --sqlite app.db --pg-url "postgresql+psycopg2://postgres:frz00@localhost:5432/dynamic_assessment" --reset
```
说明：
- `--reset` 会清空目标库并重建表，请谨慎使用。

## 前端
```powershell
cd D:\Project\Learning\frontend
npm install
npm run dev
```
打开 `http://localhost:5173`。

## 首次 Demo 数据
登录 `admin`，管理端点击 **Seed 数据结构 Demo** / **Seed 全科数据**。

## 当前 V1 主线
- 教师创建阶段并导入阶段数据
- 系统生成学习者画像与动态评价
- 教师查看班级分析和单学生成长轨迹
- 学生查看课程总览、知识图谱、推荐建议和学习报告

## 演示与答辩材料
- 演示路径文档：`docs/demo_walkthrough.md`
- 管理员端占位入口：`/admin/extensions`
- 教师端占位入口：`/teacher/extensions`

## 健康检查与日志
- Health: `http://localhost:8000/health`
- 日志文件：`backend/logs/app.log`（包含管理端关键操作审计）

## 媒体（本地/自托管视频）
- 上传视频默认存储在 `backend/media/videos`
- 访问地址：`http://localhost:8000/media/...`

## 安全提示
- 非测试环境请更换 `.env` 中的 `SECRET_KEY`。
