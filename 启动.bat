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

echo [..] build frontend
pushd frontend
call npm run build
popd
if exist "backend\static\" rmdir /s /q "backend\static"
mkdir "backend\static" 2>nul
xcopy /e /i /y "frontend\dist\*" "backend\static\" >nul

REM kill stale listeners on 8787
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8787 " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1

start "log-rca-api" cmd /c "set PYTHONPATH=backend&& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8787"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8787"
echo opened http://127.0.0.1:8787
exit /b 0
