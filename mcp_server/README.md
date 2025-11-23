# MCP Server (FastAPI)

This folder contains a minimal FastAPI-based MCP server scaffold used for testing and running in a GitHub Space/Codespace.

Files:

- `app.py` - FastAPI application with `/`, `/health`, and `/mcp/handshake` endpoints.
- `requirements.txt` - Python dependencies.

Quick start (inside the repository root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r mcp_server/requirements.txt
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
```

Or use the provided `run.sh` which installs dependencies and starts the server:

```bash
chmod +x run.sh
./run.sh
```

Codespaces/Space notes:

- Ensure port `8000` is forwarded/exposed in the Codespace preview settings so you can access the running server.
- Set `SPACE_NAME` as an environment variable in the Space settings if you want to override the default `wmthompson1_sql`.
