# start_all.ps1
# Startup script for the Subscription Cancellation Prediction System (FastAPI Backend, React Frontend, and Scrum Board)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Subscription Cancellation Prediction System" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check if .venv exists
if (-not (Test-Path "$PSScriptRoot\.venv")) {
    Write-Host "[WARNING] .venv directory not found. Please make sure python environment is set up." -ForegroundColor Yellow
}

# 1. Start Backend in a new window
Write-Host "[1/3] Launching Backend (FastAPI) on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='.'; `$env:DATABASE_URL='sqlite:///./app.db'; .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $PSScriptRoot

# 2. Start Frontend in a new window
Write-Host "[2/3] Launching Frontend (React) on http://localhost:3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm start" -WorkingDirectory "$PSScriptRoot\frontend"

# 3. Start Scrum Board in a new window
Write-Host "[3/3] Launching Scrum Board on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev" -WorkingDirectory "$PSScriptRoot\scrum-board"

Write-Host "----------------------------------------------------------" -ForegroundColor Cyan
Write-Host "All processes have been spawned in separate windows!" -ForegroundColor Yellow
Write-Host "You can close those individual terminal windows to stop each service." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
