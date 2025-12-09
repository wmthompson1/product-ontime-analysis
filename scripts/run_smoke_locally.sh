#!/usr/bin/env bash
set -euo pipefail

# Run the repository smoke tests locally:
# - create a venv (.venv)
# - install mcp_server requirements
# - start uvicorn in background (logs -> /tmp/uvicorn.log; pid -> /tmp/uvicorn.pid)
# - wait for readiness, run `scripts/smoke_test.sh`, show logs on failure, then stop server

PORT=${1:-8000}
BASE_URL="http://127.0.0.1:$PORT"
VENV=".venv"
REQ="mcp_server/requirements.txt"
LOG="/tmp/uvicorn.log"
PID="/tmp/uvicorn.pid"

echo "Preparing venv ($VENV)..."
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
if [ -f "$REQ" ]; then
  "$VENV/bin/pip" install -r "$REQ"
else
  echo "Warning: $REQ not found"
fi

echo "Starting uvicorn on port $PORT (logs -> $LOG)"
"$VENV/bin/python" -m uvicorn mcp_server.app:app --host 127.0.0.1 --port "$PORT" --log-level info &>"$LOG" &
echo $! > "$PID"

echo "Waiting for server to be ready at $BASE_URL/..."
for i in {1..20}; do
  if curl -sSf "$BASE_URL/" >/dev/null 2>&1; then
    echo "server up"
    break
  fi
  sleep 1
done

echo "Running smoke tests against $BASE_URL"
bash ./scripts/smoke_test.sh "$BASE_URL"
SMOKE_EXIT=$?

if [ $SMOKE_EXIT -ne 0 ]; then
  echo "Smoke tests failed (exit $SMOKE_EXIT). Showing last 200 lines of $LOG"
  tail -n 200 "$LOG" || true
fi

echo "Stopping server..."
if [ -f "$PID" ]; then kill "$(cat "$PID")" || true; fi

exit $SMOKE_EXIT
