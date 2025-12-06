GitHub MCP Server — Local start/stop guide

This document mirrors the HF MCP guide and explains how to run a local GitHub MCP HTTP server for testing.

Prereqs
- Node.js + npm (use `nvm` to install Node LTS per-user)
- `npm install` run in the workspace root to install dependencies
- Put your GitHub MCP-related token (if needed) in `.env`. Common env names used by scripts:
  - `GITHUB_MCP_TOKEN` — if the server expects a GitHub-specific token
  - `DEFAULT_GITHUB_TOKEN` — fallback token recognized by some servers

Security
- Do NOT commit `.env` to git. `.env` is already added to `.gitignore`.
- Use dedicated/local tokens for testing.

Files created by scripts
- `gmcp-http.pid` — PID for the HTTP server process
- `gmcp-http.log` — server logs

Scripts
- Start server (production HTTP entrypoint):

```bash
chmod +x scripts/github-mcp-start.sh scripts/github-mcp-stop.sh
./scripts/github-mcp-start.sh
```

- Stop server:

```bash
./scripts/github-mcp-stop.sh
```

Notes
- The start script attempts to run `node_modules/.bin/github-mcp-server-http` by default. If your GitHub MCP server binary is elsewhere, set `GITHUB_MCP_BIN` to its path before running the start script, e.g.:

```bash
GITHUB_MCP_BIN=/path/to/bin/github-mcp-server-http ./scripts/github-mcp-start.sh
```

- The script loads `.env` (if present) into the environment before starting the server. Add tokens like `GITHUB_MCP_TOKEN` or `DEFAULT_GITHUB_TOKEN` to `.env`.

- If you prefer a JSON-only API (no web UI), look for a `--json` mode in your server and add it to the start command (similar to the HF guide).

Testing
- Health check:

```bash
curl -v http://127.0.0.1:8081/health
```

- Schema:

```bash
curl -H "Authorization: Bearer $YOUR_TOKEN" http://127.0.0.1:8081/schema
```

If you'd like, I can:
- Start the GitHub MCP HTTP server now (on port 8081) and verify `/health`/`/schema` responses, or
- Restart it in `--json` mode so endpoints return JSON suitable for programmatic tests.
