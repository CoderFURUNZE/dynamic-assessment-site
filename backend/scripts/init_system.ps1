$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

Write-Host "Initializing system database + seeding full demo data..." -ForegroundColor Cyan

.\.venv\Scripts\python.exe -m pip --version | Out-Null
.\.venv\Scripts\python.exe .\scripts\init_system.py

Write-Host "Done. Start backend: .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Green

