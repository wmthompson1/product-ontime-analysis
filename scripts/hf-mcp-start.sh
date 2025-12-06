#!/usr/bin/env bash
# Start the Hugging Face MCP HTTP server in production mode, using .env if present.
# Writes PID to ./hf-mcp-http.pid and log to ./hf-mcp-http.log
set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . .env
  set +a
fi

export WEB_APP_PORT="${WEB_APP_PORT:-3001}"
export NODE_ENV="${NODE_ENV:-production}"
LOG=hf-mcp-http.log
PID=hf-mcp-http.pid
BIN=node_modules/.bin/hf-mcp-server-http

if [ ! -x "$BIN" ]; then
  echo "Server binary not found at $BIN. Run 'npm install' first." >&2
  exit 1
fi

if [ -f "$PID" ]; then
  oldpid=$(cat "$PID" 2>/dev/null || true)
  if [ -n "$oldpid" ] && ps -p "$oldpid" >/dev/null 2>&1; then
    echo "Server already running (PID $oldpid). Use scripts/hf-mcp-stop.sh first or remove $PID." >&2
    exit 1
  else
    echo "Removing stale PID file $PID"
    rm -f "$PID"
  fi
fi

nohup "$BIN" > "$LOG" 2>&1 &
echo $! > "$PID"
sleep 1
pid=$(cat "$PID")
echo "Started HF MCP HTTP server (PID $pid). Log: $LOG"

# quick health check (no secrets printed)
if curl -fsS --max-time 5 "http://127.0.0.1:${WEB_APP_PORT}/health" >/dev/null 2>&1; then
  echo "Health check OK on port ${WEB_APP_PORT}"
else
  echo "Health check failed or endpoint not ready yet. Tail $LOG for details."
fi
