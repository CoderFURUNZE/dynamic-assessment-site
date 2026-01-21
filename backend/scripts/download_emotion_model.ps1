$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..

Write-Host "Downloading emotion ONNX model (FER+)..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe .\scripts\download_emotion_model.py
Write-Host "Done." -ForegroundColor Green

