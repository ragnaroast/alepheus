# ============================================================================
# ChokePoint - One-Click Full Stack Startup Script (Windows PowerShell)
# ============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         CHOKEPOINT CI/CD SECURITY AGENT - STARTUP          " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$WorkspaceRoot = $PSScriptRoot
Set-Location $WorkspaceRoot

# 1. Start FalkorDB Container
Write-Host "`n[*] Starting FalkorDB Graph Database via Docker..." -ForegroundColor Yellow
try {
    docker compose up -d
    Write-Host "[+] FalkorDB is running on port 6379 (Browser UI at http://localhost:3000)" -ForegroundColor Green
} catch {
    Write-Host "[!] Warning: Docker did not start automatically. Please ensure Docker Desktop is running." -ForegroundColor Red
}

# 2. Setup Python Backend Environment
Write-Host "`n[*] Verifying Python environment & installing backend packages..." -ForegroundColor Yellow
python -m pip install -r backend\requirements.txt
python -m pip install -e backend

# 3. Setup Frontend Console
Write-Host "`n[*] Verifying Node.js dependencies for React console..." -ForegroundColor Yellow
Set-Location "$WorkspaceRoot\frontend"
npm install
Set-Location $WorkspaceRoot

# 4. Launch Backend Services in New Windows
Write-Host "`n[*] Launching FastAPI Backend Server (Port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WorkspaceRoot'; `$env:PYTHONPATH='$WorkspaceRoot\backend\src'; python -m uvicorn chokepoint.api:app --reload --port 8000"

Write-Host "[*] Launching FastMCP Server (Port 8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WorkspaceRoot'; `$env:PYTHONPATH='$WorkspaceRoot\backend\src'; python -m chokepoint.mcp_server"

Write-Host "[*] Launching React + Vite Web Console (Port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WorkspaceRoot\frontend'; npm run dev"

# 5. Service URLs Summary
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "                 CHOKEPOINT SERVICES ACTIVE                 " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Web Console (React):    http://localhost:5173" -ForegroundColor White
Write-Host "  API & Swagger Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  FastMCP Server (SSE):   http://localhost:8001" -ForegroundColor White
Write-Host "  FalkorDB Browser UI:    http://localhost:3000" -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Green
Write-Host "Press any key to close this launcher..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
