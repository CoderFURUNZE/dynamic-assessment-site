from pathlib import Path


# 兼容从仓库根目录启动 `uvicorn app.main:app`：
# 将真正的后端包目录 `backend/app` 加入当前包搜索路径。
_current_dir = Path(__file__).resolve().parent
_backend_app_dir = _current_dir.parent / "backend" / "app"

if _backend_app_dir.is_dir():
    __path__.append(str(_backend_app_dir))
