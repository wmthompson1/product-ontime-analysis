#!/usr/bin/env bash
# Start a GitHub MCP HTTP server in production mode, using .env if present.
# Writes PID to ./gmcp-http.pid and log to ./gmcp-http.log
set -euo pipefail
cd "$(dirname "$0")/.."
# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . .env
  set +a
fi

export WEB_APP_PORT="${WEB_APP_PORT:-8081}"
export NODE_ENV="${NODE_ENV:-production}"
LOG=gmcp-http.log
PID=gmcp-http.pid
# Allow overriding BIN via env; default to a conventional bin path
BIN="${GITHUB_MCP_BIN:-node_modules/.bin/github-mcp-server-http}"

# Support a --stub argument to run the local python stub instead of the real binary
USE_STUB=0
if [ "${1:-}" = "--stub" ]; then
  USE_STUB=1
fi

if [ "$USE_STUB" -eq 1 ]; then
  # Start the stub Python server if present (scripts/github-mcp-stub.py)
  STUB_PY=scripts/github-mcp-stub.py
  STUB_LOG=gmcp-stub.log
  STUB_PID=gmcp-stub.pid

  if [ -f "$STUB_PID" ]; then
    oldpid=$(cat "$STUB_PID" 2>/dev/null || true)
    if [ -n "$oldpid" ] && ps -p "$oldpid" >/dev/null 2>&1; then
      echo "Stub already running (PID $oldpid). Use scripts/github-mcp-stub-stop.sh first or remove $STUB_PID." >&2
      exit 0
    else
      echo "Removing stale stub PID file $STUB_PID"
      rm -f "$STUB_PID"
    fi
  fi

  if [ ! -x "$STUB_PY" ]; then
    if [ -f "$STUB_PY" ]; then
      echo "Starting stub via python3 $STUB_PY"
      nohup python3 "$STUB_PY" > "$STUB_LOG" 2>&1 &
      echo $! > "$STUB_PID"
      echo "Started stub (PID $(cat $STUB_PID)). Log: $STUB_LOG"
    else
      echo "Stub script not found at $STUB_PY" >&2
      exit 1
    fi
  else
    nohup "$STUB_PY" > "$STUB_LOG" 2>&1 &
    echo $! > "$STUB_PID"
    echo "Started stub (PID $(cat $STUB_PID)). Log: $STUB_LOG"
  fi

  # quick health check (no secrets printed)
  if curl -fsS --max-time 5 "http://127.0.0.1:${WEB_APP_PORT}/health" >/dev/null 2>&1; then
    echo "Stub health check OK on port ${WEB_APP_PORT}"
  else
    echo "Stub health check failed or endpoint not ready yet. Tail $STUB_LOG for details."
  fi

  exit 0
fi

if [ ! -x "$BIN" ]; then
  echo "Server binary not found at $BIN. Run 'npm install' or set GITHUB_MCP_BIN to the correct path." >&2
  exit 1
fi

if [ -f "$PID" ]; then
  oldpid=$(cat "$PID" 2>/dev/null || true)
  if [ -n "$oldpid" ] && ps -p "$oldpid" >/dev/null 2>&1; then
    echo "Server already running (PID $oldpid). Use scripts/github-mcp-stop.sh first or remove $PID." >&2
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
echo "Started GitHub MCP HTTP server (PID $pid). Log: $LOG"

# quick health check (no secrets printed)
if curl -fsS --max-time 5 "http://127.0.0.1:${WEB_APP_PORT}/health" >/dev/null 2>&1; then
  echo "Health check OK on port ${WEB_APP_PORT}"
else
  echo "Health check failed or endpoint not ready yet. Tail $LOG for details."
fi
