$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$script = Join-Path $root "backend\scripts\write_regression.py"
$ensureBackend = Join-Path $root "scripts\ensure_backend_server.ps1"

if (-not (Test-Path $python)) {
  throw "Python venv not found: $python"
}

& $ensureBackend
& $python $script @args
