@echo off
chcp 65001 >nul
cd /d "%~dp0"

call "%~dp0启动.bat"

set CF=%~dp0..\求职助手\tools\cloudflared.exe
if not exist "%CF%" set CF=%~dp0tools\cloudflared.exe
if not exist "%CF%" (
  echo [!] cloudflared.exe not found
  exit /b 1
)

if not exist logs mkdir logs
if exist logs\tunnel.log del /f /q logs\tunnel.log

echo [..] starting Cloudflare Quick Tunnel -^> http://127.0.0.1:8787
start "log-rca-tunnel" cmd /c ""%CF%" tunnel --url http://127.0.0.1:8787 --no-autoupdate > logs\tunnel.log 2>&1"

echo waiting for public URL...
set URL=
for /l %%i in (1,1,40) do (
  timeout /t 1 /nobreak >nul
  for /f "usebackq delims=" %%u in (`powershell -NoProfile -Command "if(Test-Path 'logs\\tunnel.log'){ $t=Get-Content 'logs\\tunnel.log' -Raw; if($t -match 'https://[a-z0-9-]+\.trycloudflare\.com'){ $Matches[0] }}"`) do set URL=%%u
  if defined URL goto :got
)
echo [!] failed to get public URL — see logs\tunnel.log
exit /b 1

:got
echo %URL%> logs\public_url.txt
echo.
echo PUBLIC DEMO: %URL%
echo.
start "" "%URL%"
exit /b 0
