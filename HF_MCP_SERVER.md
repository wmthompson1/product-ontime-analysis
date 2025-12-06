HF MCP Server — Local start/stop guide

This document explains how to run the local Hugging Face MCP server used for testing and integration.

Pre-reqs
- Node.js + npm (use `nvm` to install Node LTS per-user)
- `npm install` run in the workspace root to install dependencies
- A valid Hugging Face API token in `.env` as `HUGGINGFACE_API_TOKEN`. For the HF MCP server we also copy this to `DEFAULT_HF_TOKEN` so the server has a fallback.

Security
- Do NOT commit `.env` to git. `.env` is already added to `.gitignore`.
- Use short-lived or dedicated tokens for local testing; do not reuse personal access tokens for unrelated services.

Files added by scripts
- `hf-mcp-http.pid` — PID for the HTTP server process
- `hf-mcp-http.log` — server logs

Useful scripts
- Start server (production HTTP entrypoint):

```bash
# Make executable once
chmod +x scripts/hf-mcp-start.sh scripts/hf-mcp-stop.sh

# Start (reads .env automatically)
./scripts/hf-mcp-start.sh
```

- Stop server:

```bash
./scripts/hf-mcp-stop.sh
```

- Start server with JSON-only API (recommended for programmatic tests):

```bash
# If you want JSON endpoints instead of the web UI, restart in json mode
WEB_APP_PORT=3001 NODE_ENV=production node_modules/.bin/hf-mcp-server-http --json > hf-mcp-http.log 2>&1 & echo $! > hf-mcp-http.pid
```

Health checks and quick verification

```bash
# Health (returns UI by default; use --json mode to get JSON)
curl -v http://127.0.0.1:3001/health

# Schema (if JSON mode enabled or server supports it)
curl -H "Authorization: Bearer $YOUR_TOKEN" http://127.0.0.1:3001/schema

# Tail logs
tail -f hf-mcp-http.log
```

Notes
- The server may start in a "dev" mode if launched from certain entrypoints; the production `hf-mcp-server-http` entrypoint avoids Vite dev middleware and serves the HTTP API directly.
- If the server fails during startup due to missing build files (Vite/esbuild errors), prefer using the production HTTP entrypoint or install the additional `@llmindset/app` package.

If you'd like, I can also:
- Restart the server in `--json` mode now and verify `/health`/`/schema` return JSON
- Hook VS Code extension testing (tail logs while you trigger commands)
