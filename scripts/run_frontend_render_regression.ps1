$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$runnerDir = Join-Path $root "tmp-playwright-runner"
$frontendDir = Join-Path $root "frontend"
$logFile = Join-Path $root "logs\frontend_dev_5173.log"
$runnerPackage = Join-Path $runnerDir "package.json"
$runnerModules = Join-Path $runnerDir "node_modules\playwright"
$scriptPath = Join-Path $root "scripts\frontend_render_regression.js"

if (-not (Test-Path $runnerDir)) {
  New-Item -ItemType Directory -Force $runnerDir | Out-Null
}

if (-not (Test-Path $runnerPackage)) {
  '{"name":"tmp-playwright-runner","private":true}' | Set-Content $runnerPackage
}

if (-not (Test-Path $runnerModules)) {
  Push-Location $runnerDir
  try {
    npm install playwright
  }
  finally {
    Pop-Location
  }
}

$frontendReady = $false
try {
  $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 2
  if ($resp.StatusCode -eq 200) {
    $frontendReady = $true
  }
}
catch {
  $frontendReady = $false
}

if (-not $frontendReady) {
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c","npm run dev -- --host 127.0.0.1 --port 5173 > `"$logFile`" 2>&1" -WorkingDirectory $frontendDir | Out-Null
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
      $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 2
      if ($resp.StatusCode -eq 200) {
        $frontendReady = $true
        break
      }
    }
    catch {
    }
  }
}

if (-not $frontendReady) {
  throw "Frontend dev server did not become ready on http://127.0.0.1:5173"
}

$env:NODE_PATH = Join-Path $runnerDir "node_modules"
Push-Location $runnerDir
try {
  node $scriptPath @args
}
finally {
  Pop-Location
}
