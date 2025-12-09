

- **Register Space:** Attempt registration with the MCP token you provide (or run locally).  
  ```bash
  cd '/Users/williamthompson/bbb/20241019 Python/mcp_spaces/wmthompson1_sql'
  MCP_AUTH=YOUR_VALID_TOKEN ./mcp_register_space.sh
  ```
- **Test authenticated endpoints:** Start the Space with an `AUTH_TOKEN` and run example requests.
  ```bash
  # start (foreground) with auth
  AUTH_TOKEN='space-secret' PORT=8081 ./run-local.sh

  # from another shell: authenticated test
  curl -H "Authorization: Bearer space-secret" http://127.0.0.1:8081/schema
  curl -H "Authorization: Bearer space-secret" -H "Content-Type: application/json" \
    -d '{"sql":"SELECT name FROM sqlite_master WHERE type=\"table\" LIMIT 1"}' \
    http://127.0.0.1:8081/query
  ```
- **Stop / cleanup:** Stop the running Space and free ports (I can do this for you).
  ```bash
  # kill by recorded PID
  kill "$(cat mcp_spaces/wmthompson1_sql/run.pid)" || true
  rm -f mcp_spaces/wmthompson1_sql/run.pid
  ```
- **Document / automate:** I can add a short `README.md` snippet showing how to run/register/test the Space.

Which would you like me to do now?

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
