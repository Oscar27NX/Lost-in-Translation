#!/usr/bin/env bash
set -euo pipefail

echo "Starting Lost In Translation backend on http://127.0.0.1:8000 ..."
.venv/bin/uvicorn lit_core.api:app --reload --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

echo "Starting Lost In Translation frontend on http://localhost:5173 ..."
cd frontend
npm run dev
