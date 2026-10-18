@echo off
title ChokePoint - CI/CD Security Full Stack Launcher
echo ============================================================
echo          CHOKEPOINT CI/CD SECURITY AGENT - STARTUP
echo ============================================================

cd /d "%~dp0"

echo [*] Starting FalkorDB via Docker...
docker compose up -d

echo [*] Installing backend Python packages...
python -m pip install -r backend\requirements.txt
python -m pip install -e backend

echo [*] Installing frontend Node packages...
cd frontend
call npm install
cd ..

echo [*] Starting FastAPI Backend on port 8000...
start "ChokePoint FastAPI Server" cmd /k "set PYTHONPATH=%~dp0backend\src && python -m uvicorn chokepoint.api:app --reload --port 8000"

echo [*] Starting FastMCP Server on port 8001...
start "ChokePoint FastMCP Server" cmd /k "set PYTHONPATH=%~dp0backend\src && python -m chokepoint.mcp_server"

echo [*] Starting React + Vite Console on port 5173...
start "ChokePoint Web Console" cmd /k "cd frontend && npm run dev"

echo ============================================================
echo                  CHOKEPOINT SERVICES ACTIVE
echo ============================================================
echo   Web Console (React):    http://localhost:5173
echo   API ^& Swagger Docs:     http://localhost:8000/docs
echo   FastMCP Server:         http://localhost:8001
echo   FalkorDB Browser UI:    http://localhost:3000
echo ============================================================
pause
