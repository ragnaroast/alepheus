#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "============================================================"
echo "         CHOKEPOINT CI/CD SECURITY AGENT - STARTUP          "
echo "============================================================"

echo "[*] Starting FalkorDB via Docker Compose..."
docker compose up -d

echo "[*] Installing Python dependencies..."
export PYTHONPATH="$DIR/backend/src:$PYTHONPATH"
pip install -r backend/requirements.txt

echo "[*] Installing React console dependencies..."
cd "$DIR/frontend"
npm install
cd "$DIR"

echo "[*] Starting FastAPI Backend on port 8000..."
python -m uvicorn chokepoint.api:app --reload --port 8000 &

echo "[*] Starting FastMCP Server on port 8001..."
python -m chokepoint.mcp_server &

echo "[*] Starting React + Vite Console on port 5173..."
cd "$DIR/frontend" && npm run dev &

echo "============================================================"
echo "                  CHOKEPOINT SERVICES ACTIVE                "
echo "============================================================"
echo "  Web Console (React):    http://localhost:5173"
echo "  API & Swagger Docs:     http://localhost:8000/docs"
echo "  FastMCP Server:         http://localhost:8001"
echo "  FalkorDB Browser UI:    http://localhost:3000"
echo "============================================================"
wait
