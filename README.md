# 动态评价系统（MVP）

FastAPI 后端 + Vue 3 / Element Plus 前端 + MySQL 数据库。

## 后端（Windows / Python 3.11）
```powershell
cd D:\Project\Learning\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

默认账号：
- `admin / admin123`
- `teacher1 / teacher123`
- `student1 / student123`

## 数据库（仅 MySQL）
1. 启动数据库与管理界面：
```powershell
cd D:\Project\Learning
docker compose up -d db adminer
```

或使用脚本：
```powershell
cd D:\Project\Learning\backend
.\scripts\mysql_up.ps1
```

2. 配置 `backend/.env`：
```env
DATABASE_URL=mysql+pymysql://root:root123@localhost:3306/dynamic_assessment?charset=utf8mb4
```

3. 初始化或重置数据库：
```powershell
cd D:\Project\Learning\backend
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset
.\.venv\Scripts\python.exe .\scripts\init_system.py --reset --no-seed
```

说明：
- `--reset` 会清空 MySQL 当前库中的业务表后重建。

Adminer 默认访问地址：`http://localhost:8080`

## 前端
```powershell
cd D:\Project\Learning\frontend
npm install
npm run dev
```

访问：`http://localhost:5173`

## 冒烟测试
```powershell
cd D:\Project\Learning
py -3.11 .\backend\scripts\smoke_acceptance.py
```

## 当前主线
- 教师创建阶段并导入阶段数据
- 系统生成学习者画像与动态评价
- 教师查看班级分析和单学生成长轨迹
- 学生查看课程总览、知识图谱、推荐建议和学习报告

## 健康检查与日志
- Health: `http://localhost:8000/health`
- 日志文件：`backend/logs/app.log`

## 媒体
- 上传视频默认存储在 `backend/media/videos`
- 访问地址：`http://localhost:8000/media/...`

## 安全提示
- 非测试环境请更换 `.env` 中的 `SECRET_KEY`。
