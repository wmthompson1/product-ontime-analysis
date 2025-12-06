#!/usr/bin/env bash
# Start the github-mcp stub server (wrapper)
set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  . .env
  set +a
fi

STUB_PY=scripts/github-mcp-stub.py
STUB_LOG=gmcp-stub.log
STUB_PID=gmcp-stub.pid

if [ -f "$STUB_PID" ]; then
  oldpid=$(cat "$STUB_PID" 2>/dev/null || true)
  if [ -n "$oldpid" ] && ps -p "$oldpid" >/dev/null 2>&1; then
    echo "Stub already running (PID $oldpid)." >&2
    exit 0
  else
    echo "Removing stale stub PID file $STUB_PID"
    rm -f "$STUB_PID"
  fi
fi

if [ ! -f "$STUB_PY" ]; then
  echo "Stub script missing at $STUB_PY" >&2
  exit 1
fi

nohup python3 "$STUB_PY" > "$STUB_LOG" 2>&1 &
echo $! > "$STUB_PID"
echo "Started github-mcp stub (PID $(cat $STUB_PID)). Log: $STUB_LOG"

if curl -fsS --max-time 5 "http://127.0.0.1:${WEB_APP_PORT:-8081}/health" >/dev/null 2>&1; then
  echo "Stub health check OK"
else
  echo "Stub health check failed or endpoint not ready yet. Tail $STUB_LOG for details."
fi
