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

Resource endpoint (Git repo path)
--------------------------------

This MCP server supports a simple resource lookup endpoint that follows a Git-style repo path resource shape used in some MCP contexts.

Endpoint: `POST /mcp/resource`

Payload example:

```json
{
	"resource": {
		"type": "git:repo_path",
		"path": "mcp_server/sample_schemas"
	}
}
```

Behavior:
- If `resource.type` is `git:repo_path` and `resource.path` points to a directory inside the repository, the endpoint returns a manifest of files in that folder.
- If the path points to a file, the endpoint returns a small sample of that file.

Testing:
- Use `mcp_server/test_resource.sh` to POST a resource payload and print the JSON response. Example:

```bash
./mcp_server/test_resource.sh http://127.0.0.1:8000 mcp_server/sample_schemas
```

Notes:
- The server resolves paths relative to the repository workspace and rejects paths that resolve outside the repository for safety.
