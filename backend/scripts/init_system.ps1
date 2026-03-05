$ErrorActionPreference = "Stop"
param(
    [switch]$Reset,
    [switch]$NoSeed
)

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

Write-Host "Initializing system database" -ForegroundColor Cyan

$argsList = @()
if ($Reset) { $argsList += "--reset" }
if ($NoSeed) { $argsList += "--no-seed" }

# ensure venv python exists
if (!(Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Python venv not found. Create it first: py -3.11 -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# run init
.\.venv\Scripts\python.exe .\scripts\init_system.py @argsList

Write-Host "Done. Start backend: .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Green
