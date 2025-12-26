#!/usr/bin/env bash
# Stop the Hugging Face MCP HTTP server started by hf-mcp-start.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PID=hf-mcp-http.pid
LOG=hf-mcp-http.log

if [ ! -f "$PID" ]; then
  echo "No PID file ($PID) found; server may not be running." >&2
  exit 0
fi

pid=$(cat "$PID" 2>/dev/null || echo "")
if [ -z "$pid" ]; then
  echo "PID file empty; removing" >&2
  rm -f "$PID"
  exit 0
fi

if ps -p "$pid" >/dev/null 2>&1; then
  echo "Stopping HF MCP server (PID $pid)"
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
rm -f "$PID"
echo "Stopped. Check $LOG for details."