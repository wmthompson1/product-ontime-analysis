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
