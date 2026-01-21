# Dynamic Assessment System (MVP)

FastAPI backend + Vue3/Element Plus frontend.

## Backend (Windows / Python 3.11)
```powershell
cd D:\Project\Learning\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default accounts:
- `admin / admin123`
- `teacher1 / teacher123`
- `student1 / student123`

### Database（PostgreSQL 推荐）
1) 启动数据库（示例使用 docker-compose，包含 postgres + pgAdmin）：
```powershell
cd D:\Project\Learning
docker compose up -d db pgadmin
```
pgAdmin 默认访问 `http://localhost:5050`，邮箱/密码见 `docker-compose.yml` 中的环境变量。

2) 配置 `.env` 中的 `DATABASE_URL` 指向 Postgres，例如：  
`DATABASE_URL=postgresql+psycopg2://postgres:frz00@localhost:5432/dynamic_assessment`

3) 初始化表并可选导入演示数据：
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset   # 删除旧库/表后重建并导入 demo
# 只建表，不导入数据：
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset --no-seed
```
说明：  
- sqlite 环境下 `--reset` 会删除 sqlite 文件；Postgres 等其他数据库下则会 drop 所有表后重建。  
- 脚本已自动修正导入路径，可直接从仓库根目录运行。

### SQLite -> PostgreSQL 迁移
如果之前使用了 sqlite（`backend/app.db`），可以用脚本导入到 Postgres：
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe .\scripts\migrate_sqlite_to_pg.py --sqlite app.db --pg-url "postgresql+psycopg2://postgres:frz00@localhost:5432/dynamic_assessment" --reset
```
说明：
- `--reset` 会清空目标库并重建表，请谨慎使用。
- `--sqlite` 默认是 `backend/app.db`，也可以改成绝对路径。

## Frontend
```powershell
cd D:\Project\Learning\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## First-time demo data
Login as `admin`, open 管理端 click **Seed 导入基础 Demo 数据**.

## Health & Logs
- Health check: `http://localhost:8000/health`
- Log file: `backend/logs/app.log` (audit logs for key admin actions)

## Media (Local/Hosted Video)
- Uploads are stored under `backend/media/videos`
- Served from `http://localhost:8000/media/...`
- Configure `MEDIA_DIR` and `MEDIA_URL` in `.env` if needed

## Security Note
- Change `SECRET_KEY` in `.env` for non-test usage.
