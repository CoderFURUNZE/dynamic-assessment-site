#!/usr/bin/env bash
# 从仓库任意位置调用后端启动脚本。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  PY="$ROOT/backend/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
exec "$PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
