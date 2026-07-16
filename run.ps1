# Start Backend in a new window
Start-Process powershell -ArgumentList "-NoExit -Command `"`$env:PYTHONPATH='.'; `$env:DATABASE_URL='sqlite:///./app.db'; .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`"" -WindowStyle Normal

# Start Frontend in a new window
Start-Process powershell -ArgumentList "-NoExit -Command `"cd frontend; npm start`"" -WindowStyle Normal
