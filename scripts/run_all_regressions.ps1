$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$cleanupAfter = $false
if ($args -contains "-CleanupAfter") {
  $cleanupAfter = $true
}

& (Join-Path $root "scripts\ensure_backend_server.ps1")

Write-Host "[1/4] backend smoke"
& (Join-Path $root "backend\.venv\Scripts\python.exe") (Join-Path $root "backend\scripts\smoke_acceptance.py")

Write-Host "[2/4] backend extended"
& (Join-Path $root "backend\.venv\Scripts\python.exe") (Join-Path $root "backend\scripts\crawl_api_smoke.py")

Write-Host "[3/4] backend write"
& (Join-Path $root "scripts\run_backend_write_regression.ps1")

Write-Host "[4/4] frontend render"
& (Join-Path $root "scripts\run_frontend_render_regression.ps1")

if ($cleanupAfter) {
  Write-Host "[5/5] cleanup regression data"
  & (Join-Path $root "scripts\run_cleanup_regression_data.ps1")
}
