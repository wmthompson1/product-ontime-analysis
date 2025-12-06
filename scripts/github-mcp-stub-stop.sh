#!/usr/bin/env bash
# Stop the github-mcp stub server
set -euo pipefail
cd "$(dirname "$0")/.."
STUB_PID=gmcp-stub.pid
STUB_LOG=gmcp-stub.log

if [ ! -f "$STUB_PID" ]; then
  echo "No stub PID file ($STUB_PID) found; stub may not be running." >&2
  exit 0
fi

pid=$(cat "$STUB_PID" 2>/dev/null || echo "")
if [ -z "$pid" ]; then
  echo "PID file empty; removing" >&2
  rm -f "$STUB_PID"
  exit 0
fi

if ps -p "$pid" >/dev/null 2>&1; then
  echo "Stopping stub (PID $pid)"
  kill "$pid" || true
  sleep 1
  if ps -p "$pid" >/dev/null 2>&1; then
    echo "PID $pid still running; sending SIGKILL"
    kill -9 "$pid" || true
    sleep 1
  fi
else
  echo "Process $pid not running; removing PID file"
fi
rm -f "$STUB_PID"
echo "Stopped stub. Check $STUB_LOG for details."