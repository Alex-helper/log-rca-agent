# Local start without Docker: backend :8787 + frontend vite :5173
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env — fill OPENAI_API_KEY" -ForegroundColor Yellow
}

$venvPy = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "[..] create backend venv" -ForegroundColor Cyan
  python -m venv (Join-Path $Root "backend\.venv")
  & $venvPy -m pip install -r (Join-Path $Root "backend\requirements.txt")
}

$env:PYTHONPATH = Join-Path $Root "backend"
Start-Process -FilePath $venvPy -ArgumentList @(
  "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8787"
) -WorkingDirectory (Join-Path $Root "backend") -WindowStyle Minimized

Set-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) {
  npm install
}
Start-Process -FilePath "npm" -ArgumentList @("run", "dev") -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Minimized
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5173"
Write-Host "Backend http://127.0.0.1:8787  Frontend http://127.0.0.1:5173" -ForegroundColor Green
