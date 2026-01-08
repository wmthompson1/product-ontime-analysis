#!/usr/bin/env bash
set -euo pipefail

# Local Postgres + Gradio app helper (Homebrew workflow)
# Usage: run this on your macOS dev machine (where Homebrew and psql are available)

# 1) Check prerequisites
if ! command -v brew >/dev/null 2>&1; then
  echo "ERROR: Homebrew not found. Install Homebrew first: https://brew.sh/"
  exit 2
fi

# Ensure Postgres 14 is installed (user can change if they prefer another version)
if ! brew list postgresql@14 >/dev/null 2>&1; then
  echo "postgresql@14 not installed via brew. Installing..."
  brew install postgresql@14
fi

# 2) Start Postgres via brew services
echo "Starting postgresql@14 via Homebrew..."
brew services start postgresql@14

# 3) Create DB if missing
DBNAME="manufacturing_analytics"
if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql not found in PATH. Ensure Homebrew's postgres bin is in your PATH." 
  echo "You may need: export PATH=\"/opt/homebrew/opt/postgresql@14/bin:$PATH\"" 
  exit 3
fi

if ! psql -lqt | cut -d \| -f 1 | grep -qw "$DBNAME"; then
  echo "Creating database: $DBNAME"
  createdb "$DBNAME"
else
  echo "Database $DBNAME already exists"
fi

# 4) Load schema
SCHEMA_FILE="schema/schema.sql"
if [ ! -f "$SCHEMA_FILE" ]; then
  echo "ERROR: schema file not found at $SCHEMA_FILE. Run this script from the repo root." >&2
  exit 4
fi

echo "Loading schema into $DBNAME (this may warn about extensions like 'vector')..."
psql "$DBNAME" -f "$SCHEMA_FILE" || true

# 5) Verify table count
echo "Tables in public schema (first 30 lines):"
psql -d "$DBNAME" -c "\dt public.*" | sed -n '1,30p'

echo "Count of public tables:"
psql -d "$DBNAME" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"

# 6) Start/Restart Gradio app pointing to the DB
# If you want to run the app locally, ensure you have created and activated the .venv, or run with .venv/bin/python
PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Warning: $PYTHON_BIN not found or not executable. Run './scripts/venv_setup.sh' first to create .venv." >&2
fi

# Kill prior app process if present
if [ -f /tmp/hf_gradio.pid ]; then
  oldpid=$(cat /tmp/hf_gradio.pid || true)
  if [ -n "$oldpid" ] && ps -p "$oldpid" >/dev/null 2>&1; then
    echo "Stopping previous Gradio pid=$oldpid"
    kill "$oldpid" || true
    sleep 1
    if ps -p "$oldpid" >/dev/null 2>&1; then
      echo "Process still alive; killing"; kill -9 "$oldpid" || true
    fi
  fi
  rm -f /tmp/hf_gradio.pid || true
fi

# Export DATABASE_URL and launch
export DATABASE_URL="postgresql://postgres@127.0.0.1:5432/$DBNAME"
# If you set a password for your local user, use: postgresql://user:pass@127.0.0.1:5432/$DBNAME

echo "Starting Gradio app with DATABASE_URL=$DATABASE_URL"
$PYTHON_BIN hf-space-inventory-sqlgen/app.py &>/tmp/hf_gradio.log & echo $! > /tmp/hf_gradio.pid

# 7) Wait for readiness and then run quick checks
for i in {1..30}; do
  if curl -sSf http://127.0.0.1:5000/mcp/discover >/dev/null 2>&1; then
    echo "Gradio app ready"; break
  fi
  sleep 0.5
done

if ! curl -sSf http://127.0.0.1:5000/mcp/discover >/dev/null 2>&1; then
  echo "ERROR: Gradio app did not become ready. Tail last 120 lines of /tmp/hf_gradio.log" >&2
  tail -n 120 /tmp/hf_gradio.log || true
  exit 5
fi

# Print verification results
echo "\n--- GET /mcp/tools/get_db_tables ---"
curl -sS http://127.0.0.1:5000/mcp/tools/get_db_tables | python -m json.tool || true

echo "\n--- GET /mcp/tools/get_all_ddl (table count) ---"
curl -sS http://127.0.0.1:5000/mcp/tools/get_all_ddl | python - <<PY
import sys,json
j=json.load(sys.stdin)
if isinstance(j.get('tables',[]), list):
    print('tables_count:', len(j.get('tables',[])))
elif isinstance(j.get('ddl',{}), dict):
    print('ddl_count:', len(j.get('ddl',{})))
else:
    print('unknown structure')
PY

echo "\n--- GET /mcp/tools/get_saved_categories ---"
curl -sS http://127.0.0.1:5000/mcp/tools/get_saved_categories | python -m json.tool || true

# show a sample generate_sql
echo "\n--- POST /mcp/tools/generate_sql (sample) ---"
curl -sS -X POST http://127.0.0.1:5000/mcp/tools/generate_sql -H 'Content-Type: application/json' -d '{"query":"Show me low stock items that need reorder","include_explanation":true}' | python -m json.tool || true

echo "\nLog tail (/tmp/hf_gradio.log):"
tail -n 80 /tmp/hf_gradio.log || true

echo "\nAll done. Gradio UI at http://127.0.0.1:5000/gradio/"
