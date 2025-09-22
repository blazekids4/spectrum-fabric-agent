#!/usr/bin/env bash
set -euo pipefail

# Simple startup script for Azure Linux App Service or container usage.
# Ensures dependencies are installed (in container scenarios) and launches Uvicorn.

if [ -f requirements.txt ]; then
  echo "[startup] Installing Python dependencies..."
  pip install --no-cache-dir -r requirements.txt
fi

export PORT="${PORT:-8000}"
export BACKEND_PORT="$PORT"

echo "[startup] Starting FastAPI app on 0.0.0.0:${PORT}"
exec python -m uvicorn app:app --host 0.0.0.0 --port ${PORT}
