@echo off
setlocal
set PROJECT_DIR=%~dp0

echo Starting backend...
start "backend" cmd /k "cd /d %PROJECT_DIR%backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Starting frontend...
start "frontend" cmd /k "cd /d %PROJECT_DIR%frontend && npm run dev"

echo Done.