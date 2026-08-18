$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Error "Missing .venv. Run: py -3.12 -m venv .venv"
    exit 1
}

$root = Get-Location

Write-Host "Starting SmartSeg (AI engine, backend, frontend)..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root'; .\.venv\Scripts\Activate.ps1; cd ai-engine; Write-Host '[AI ENGINE]' -ForegroundColor Green; python main.py"
)

Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root'; .\.venv\Scripts\Activate.ps1; cd backend; Write-Host '[BACKEND]' -ForegroundColor Yellow; uvicorn main:app --reload"
)

Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; Write-Host '[FRONTEND]' -ForegroundColor Magenta; npm run dev"
)

Write-Host "All three services launching in separate windows." -ForegroundColor Cyan
Write-Host "Dashboard: http://localhost:5173" -ForegroundColor Cyan
Write-Host "API docs:  http://localhost:8000/docs" -ForegroundColor Cyan