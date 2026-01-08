I'll search the HF SQL-gen app for MCP endpoint definitions and where they're mounted.

Searched for regex `/mcp|mcp/discover|create_gradio_interface|create_gradio` (`**/hf-space-inventory-sqlgen/**`), 39 results

Read hf-space-inventory-sqlgen/app.py#1-1), lines 1 to 220

Read hf-space-inventory-sqlgen/app.py#220-220), lines 220 to 520

Read hf-space-inventory-sqlgen/app.py#520-520), lines 520 to 920

Read hf-space-inventory-sqlgen/mcp_discovery.json)

**Summary — MCP endpoints used and how they're derived**

- **Where to look:** the FastAPI MCP handlers are implemented in app.py and a static manifest lives at mcp_discovery.json.

- **Endpoints exposed (path → purpose):**
  - `GET /mcp/discover` — Discovery manifest listing tools, resources and prompts. (app.py)
  - `POST /mcp/tools/generate_sql` — NL → SQL generator (returns SQL, explanation, tables used, complexity). (app.py)
  - `GET /mcp/tools/get_schema` — Return sample/full schema JSON. (app.py)
  - `GET /mcp/tools/get_sql_templates` — Return pre-built SQL templates (optionally by name). (app.py)
  - `POST /mcp/tools/analyze_csv` — Analyze uploaded CSV content to suggest schema/queries. (app.py)
  - `GET /mcp/tools/get_db_tables` — List DB tables. (app.py)
  - `GET /mcp/tools/get_table_ddl` — Get CREATE TABLE for one table. (app.py)
  - `GET /mcp/tools/get_all_ddl` — Get DDL for all tables. (app.py)
  - `POST /mcp/tools/execute_sql` — Execute read-only SELECT queries against the demo DB. (app.py)
  - `GET /mcp/tools/get_saved_categories` / `GET /mcp/tools/get_saved_queries` / `POST /mcp/tools/save_query` — Saved query catalog & save API. (app.py, app.py, app.py)

- **How these endpoints are derived / wired:**
  - The app defines FastAPI routes directly (see the `@app.get` / `@app.post` handlers in app.py). Each tool handler implements the behavior (e.g., `generate_sql` calls `analyze_query_intent()` + `generate_sql_from_intent()`).
  - The discovery response is constructed from Pydantic models (`MCPToolDefinition`, `MCPDiscoveryResponse`) inside `mcp_discover()` so external clients can programmatically learn tool names, descriptions and input schemas. (See app.py and the tool definitions around app.py.)
  - A static manifest, mcp_discovery.json, mirrors the same mapping (tool names → paths) and is useful for publishing or offline inspection.
  - The Gradio UI (`create_gradio_interface()` in app.py) implements the same functionality locally via internal helper functions (it does not call the HTTP endpoints internally — it reuses the same Python functions). The UI also builds MCP context packages (list of tools/resources/prompts) that match the discovery schema so external tools (e.g., Copilot) can consume them.

- **Practical implication:** clients (or HF Space consumers) should call `GET /mcp/discover` to discover tool names and input schemas, then call the corresponding `/mcp/tools/<tool_name>` endpoint with the payload shaped to the declared input_schema (e.g., POST JSON `{ "query": "..." }` to `/mcp/tools/generate_sql`) — the static mcp_discovery.json reflects that mapping.

If you want, I can:
- produce a compact table mapping tool names → request examples, or
- add a small example client snippet that calls `/mcp/discover` and then `generate_sql`. Which would you prefer?