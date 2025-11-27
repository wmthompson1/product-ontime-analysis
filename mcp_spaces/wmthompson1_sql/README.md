# wmthompson1_sql — Local SQL assistant (dev)

This directory is a local, non-Docker Space you can run for development and local testing.

Quick steps

1. Open a terminal in this folder:

```bash
cd "$(pwd)/mcp_spaces/wmthompson1_sql"
```

2. Run the Space locally (creates `.venv` automatically on first run):

```bash
./run-local.sh
```

3. The app listens on port `8080` by default. Try:

```bash
curl localhost:8080/health
curl -X POST -H "Content-Type: application/json" -d '{"sql":"SELECT name FROM sqlite_master WHERE type=\"table\""}' http://localhost:8080/query
```

Notes
- To require an authorization token, set `AUTH_TOKEN` in the environment before starting, or provide it using the `space.json` input when registering.
- To make this Space discoverable by GitHub MCP server UI you typically need to publish `space.json` in a GitHub repo or push an image to a registry—this server's UI lists repo/image-based Spaces only.

Security
- This is a development, read-only helper. Queries are sanitized to allow only SELECT/PRAGMA/EXPLAIN/WITH statements and simple limits; do not expose this service to untrusted networks without additional hardening.

---

Recommended start / stop commands

Run (foreground, useful for debugging):

```bash
cd "$(pwd)/mcp_spaces/wmthompson1_sql"
# start (default PORT=8080)
./run-local.sh
```

Run (background, with log + pid):

```bash
cd "$(pwd)/mcp_spaces/wmthompson1_sql"
# start background on PORT 8081 and write pid/log
PORT=8081 ./run-local.sh > run.log 2>&1 & echo $! > run.pid
# view logs
tail -f run.log
```

Run with an authorization token (do NOT use a long-lived GitHub PAT for local testing):

```bash
# start with a short-lived/local token
AUTH_TOKEN='my-local-token' PORT=8081 ./run-local.sh > run.log 2>&1 & echo $! > run.pid
# test authenticated endpoint
curl -H "Authorization: Bearer my-local-token" http://127.0.0.1:8081/schema
```

Stop the server (if started with `run.pid`):

```bash
if [ -f run.pid ]; then kill "$(cat run.pid)" || true; rm -f run.pid; fi
```

Find and stop by port (if run.pid not present):

```bash
lsof -iTCP:8081 -sTCP:LISTEN -n -P
# then kill <PID>
```

Reverting workspace MCP config

If you added a local server to the workspace `./.vscode/mcp.json` during testing and want to remove it, restore the file to only include the `Authorization` input and an empty `servers` object, for example:

```jsonc
{
	"inputs": [
		{ "id": "Authorization", "type": "promptString", "password": true }
	],
	"servers": {}
}
```

Security note
- If you accidentally used a real GitHub Personal Access Token (PAT) as `AUTH_TOKEN` for local testing, revoke/rotate it in GitHub immediately and use a dedicated short-lived string for local runs.

Troubleshooting
- If a port is already in use, pick another `PORT` value when starting (e.g., `PORT=8081`).
- Use `tail -f run.log` to see incoming requests and verify VS Code interactions when running `MCP: List Servers`.

If you prefer, I can add a small `make` shim or a launchd plist for easier start/stop — tell me which you prefer.
