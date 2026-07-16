@echo off
:: start_all.bat
:: Double-click this script to run FastAPI backend, React frontend, and the Scrum Board.

echo ==========================================================
echo  Starting Subscription Cancellation Prediction System
echo ==========================================================

echo [1/3] Launching Backend (FastAPI) on http://localhost:8000...
start "Backend Server (FastAPI)" cmd /k "set PYTHONPATH=.&& set DATABASE_URL=sqlite:///./app.db&& .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

echo [2/3] Launching Frontend (React) on http://localhost:3000...
cd frontend
start "React Frontend" cmd /k "npm start"
cd ..

echo [3/3] Launching Scrum Board on http://localhost:5173...
cd scrum-board
start "Scrum Board" cmd /k "npm run dev"
cd ..

echo ----------------------------------------------------------
echo All services have been launched in separate Command Prompt windows!
echo Keep those windows open to keep the services running.
echo ==========================================================
pause
