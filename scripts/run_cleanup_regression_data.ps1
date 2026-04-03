$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$script = Join-Path $root "backend\scripts\cleanup_regression_data.py"

if (-not (Test-Path $python)) {
  throw "Python venv not found: $python"
}

& $python $script @args
