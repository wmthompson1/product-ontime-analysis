# MCP Setup for a Copy of This Repo on Another Linux Machine

**Date:** 2026-07-04
**Context:** Setting up a clone of this public repo on another Linux box.
Question: exact MCP server entries (full JSON), startup commands/binaries per
server, and whether config lives in the repo (`.vscode/mcp.json`) or
user-level (`~/.copilot/mcp-config.json`).

---

## 1. There are no MCP config files in this repo

No `.vscode/mcp.json`, no `.mcp.json`, no `mcp-config.json` exist anywhere in
the project, and the Replit workspace has no MCP servers configured either.
So there is nothing to copy — on the other Linux box you will be **creating**
the config, not migrating it.

## 2. What the repo actually contains (3 MCP-adjacent things)

| Piece | What it is | How it starts |
|---|---|---|
| `scripts/librarian_server.py` | Real MCP server (`FastMCP`, stdio transport, name `mrp-librarian`) — lists/reads the MRP docs in `docs/my-mrp-kb/`, stages terminology research | `python scripts/librarian_server.py` |
| `docs/mcp-filesystem/` | Docs only, for an **external** filesystem server (`pip install git+https://github.com/MarcusJellinghaus/mcp_server_filesystem.git`) | `mcp-server-filesystem --project-dir <repo>` |
| `mcp_spaces/wmthompson1_sql/` | **Not** a stdio MCP server — a plain HTTP dev service (read-only SQL on port 8080) | `./run-local.sh` from that folder |

Also note: the main app's `GET /mcp/tools/get_resolves_to` is just a FastAPI
route inside `app.py` — it ships with the app itself; nothing to register in
an MCP config.

## 3. Exact JSON for the new machine

**Repo-level is the right home** (`.vscode/mcp.json`), because the entries
reference repo-relative scripts. VS Code's native file uses a `"servers"`
key; Copilot CLI's `~/.copilot/mcp-config.json` uses `"mcpServers"` — same
entries, different wrapper key.

### `.vscode/mcp.json` (VS Code / Copilot in VS Code)

```json
{
  "servers": {
    "mrp-librarian": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["${workspaceFolder}/scripts/librarian_server.py"],
      "env": {
        "MRP_DOCUMENTS_DIR": "${workspaceFolder}/docs/my-mrp-kb",
        "MRP_ENABLE_GRAPH_COMMIT": "false"
      }
    },
    "filesystem": {
      "type": "stdio",
      "command": "mcp-server-filesystem",
      "args": ["--project-dir", "${workspaceFolder}", "--console-only"]
    }
  }
}
```

### `~/.copilot/mcp-config.json` (Copilot CLI — absolute paths, no `${workspaceFolder}`)

```json
{
  "mcpServers": {
    "mrp-librarian": {
      "command": "/path/to/repo/.venv/bin/python",
      "args": ["/path/to/repo/scripts/librarian_server.py"],
      "env": {
        "MRP_DOCUMENTS_DIR": "/path/to/repo/docs/my-mrp-kb",
        "MRP_ENABLE_GRAPH_COMMIT": "false"
      }
    }
  }
}
```

## Setup notes for the librarian on the new box

- Install repo deps first (`uv pip install -r requirements.txt` etc.) — it
  imports `mcp`, `sqlglot`, `python-dotenv`.
- It reads a `.env` file, so Arango credentials (`ARANGO_HOST`,
  `ARANGO_USER`, `ARANGO_ROOT_PASSWORD`) can live there instead of the JSON —
  better than putting secrets in the config.
- Keep `MRP_ENABLE_GRAPH_COMMIT=false` (the default) — that gate stops it
  from ever writing to the graph; commits go only to the separate
  `mrp_research` DB even when enabled.
