#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "====================================="
echo "  SafeRouteAI — Full Stack Demo"
echo "====================================="
echo ""

# 1. Start Mosquitto if Docker available
if command -v docker &> /dev/null; then
    echo "Starting Mosquitto..."
    docker compose -f docker/docker-compose.yml up -d mosquitto 2>/dev/null || true
    echo "  MQTT broker on localhost:1883"
else
    echo "  Docker not found — ensure Mosquitto is running on localhost:1883"
fi
echo ""

# 2. Start FastAPI backend
echo "Starting backend (FastAPI)..."
cd "$ROOT"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Backend PID $BACKEND_PID on http://localhost:8000"
echo ""

# 3. Start frontend (Vite dev)
echo "Starting frontend (Vite)..."
cd "$ROOT/frontend"
VITE_USE_MOCK=false VITE_API_BASE=http://localhost:8000 VITE_WS_URL=ws://localhost:8000/api/events \
    bun run dev &
FRONTEND_PID=$!
echo "  Frontend PID $FRONTEND_PID on http://localhost:5173"
echo ""

echo "====================================="
echo "  All services starting..."
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8000"
echo "  API docs : http://localhost:8000/docs"
echo "====================================="
echo ""
echo "Press Ctrl+C to stop all services."

cleanup() {
    echo "Stopping..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait
}
trap cleanup EXIT INT TERM

wait
