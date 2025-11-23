#!/usr/bin/env bash
set -euo pipefail

# Simple run script for the MCP FastAPI server
PORT=${PORT:-8000}
SPACE_NAME=${SPACE_NAME:-wmthompson1_sql}
export SPACE_NAME

python3 -m pip install --upgrade pip
pip install -r mcp_server/requirements.txt

exec uvicorn mcp_server.app:app --host 0.0.0.0 --port "$PORT" --reload
