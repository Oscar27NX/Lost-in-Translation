# Launch Lost In Translation (Backend + Frontend) on Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "Starting Lost In Translation backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$backend = Start-Process -PassThru -NoNewWindow -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "lit_core.api:app", "--reload", "--port", "8000"

try {
    Write-Host "Starting Lost In Translation frontend on http://localhost:5173 ..." -ForegroundColor Cyan
    Push-Location frontend
    npm run dev
} finally {
    Pop-Location
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}
