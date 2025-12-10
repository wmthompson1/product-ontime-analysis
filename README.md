

<!-- Space registration removed: the GitHub Space was deleted and related registration instructions were archived. -->

---

## Local MCP Server smoke & tests

You can run the small FastAPI-based MCP server smoke tests locally using the provided helper script.

1. Make the helper executable:

```bash
chmod +x scripts/run_smoke_locally.sh
```

2. Run the helper (default port 8000):

```bash
./scripts/run_smoke_locally.sh 8000
```

This will create a `.venv`, install `mcp_server` dependencies, start the server, run the smoke checks, print logs on failure, and stop the server.

3. To run the unit tests for the MCP server (from an activated `.venv`):

```bash
.venv/bin/python -m pytest -q mcp_server/tests
```

If you'd like, I can add these commands to a CONTRIBUTING.md or move them closer to the top of this README.
