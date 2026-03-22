#!/bin/bash
set -e

# Ensure database directory exists (Railway Volume mounted at /data)
mkdir -p "${DATABASE_DIR:-/data}"

# Start bot in background
echo "Starting bot..."
python bot_v2.py &
BOT_PID=$!

# Trap to kill bot when this script exits
trap "kill $BOT_PID 2>/dev/null" EXIT

# Start API in foreground (Railway expects the web process to bind $PORT)
echo "Starting API on port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
