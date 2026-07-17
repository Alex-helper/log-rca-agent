@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [..] create venv
  python -m venv .venv
  .venv\Scripts\pip install -r backend\requirements.txt
)

if not exist "frontend\node_modules\" (
  echo [..] npm install frontend
  pushd frontend
  call npm install
  popd
)

REM free ports if stale
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8787 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul

start "log-rca-api" cmd /c "set PYTHONPATH=backend&& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787"
start "log-rca-ui" cmd /c "cd /d "%~dp0frontend" && npm run dev -- --host 127.0.0.1 --port 5173"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo API http://127.0.0.1:8787
echo UI  http://127.0.0.1:5173
exit /b 0
