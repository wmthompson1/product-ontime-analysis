#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT_DIR/.venv"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$ROOT_DIR/requirements.txt"
fi

export AUTH_TOKEN="${AUTH_TOKEN:-}"
export DB_PATH="${DB_PATH:-$ROOT_DIR/data/dev.sqlite}"

echo "Starting wmthompson1_sql Space (local)"
exec "$VENV/bin/python" "$ROOT_DIR/app.py"
