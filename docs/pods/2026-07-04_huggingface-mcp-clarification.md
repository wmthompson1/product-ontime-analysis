# "HuggingFace MCP" Clarification — How the App's Tabs Actually Connect

**Date:** 2026-07-04
**Context:** Question while setting up a repo copy on another Linux machine:
how was "the HuggingFace MCP" set up for the app's tabs — server entry JSON,
command + args, env vars, stdio vs HTTP, auth?

---

## Answer: there was never an MCP server entry to set up

Two separate things both sound like "HuggingFace MCP" — neither is a
registered MCP server:

## 1. The app's tabs — the app *is* the "MCP," not a client of one

`hf-space-inventory-sqlgen/app.py` is an **MCP-inspired HTTP API**:

- REST routes follow the MCP *discovery pattern* — `GET /mcp/discover` lists
  the tools, and `/mcp/tools/...` routes serve them (including
  `get_resolves_to`).
- The Gradio tabs don't go through any MCP client at all — they call the
  same Python functions in-process.
- **Caveat:** this is plain HTTP/REST that *mimics* MCP discovery. It is
  **not** the official MCP JSON-RPC protocol, so there is no valid
  `mcp.json` server entry for it — an MCP client (Copilot, Claude, etc.)
  cannot consume it directly. That is why no config JSON exists.

**Command:** `cd hf-space-inventory-sqlgen && python app.py`
(FastAPI + Gradio, port 8080)
**Transport:** HTTP
**Auth:** read-only endpoints are open; the write/sensitive ones (query
save, sync) require header `X-API-Key: <QUERY_API_KEY>` and return 503 if
`QUERY_API_KEY` is unset — fail closed.

## 2. The actual HuggingFace connection — an API client, not MCP

The "Ask a Question" dispatcher (`production_dispatcher.py`) calls the
**HF Inference API** directly via `huggingface_hub.InferenceClient`
(Mistral-7B as a closed-vocabulary classifier only — it never generates SQL):

- **Env var:** `HF_TOKEN` (HF access token, passed as `api_key` to the client)
- No server process, no JSON entry — just an outbound API call, with a
  **Demo Mode (Mock)** toggle in the UI so it runs without the token.

## Env vars the app needs (new machine)

| Var | Purpose |
|---|---|
| `HF_TOKEN` | HF Inference API for the dispatcher (optional — demo mode works without it) |
| `QUERY_API_KEY` | Guards the save/sync endpoints (unset = those endpoints disabled) |
| `ARANGO_HOST` / `ARANGO_USER` / `ARANGO_ROOT_PASSWORD` / `ARANGO_DB` | Graph tabs |
| `SQL_MCP_SOURCE_DATABASE` / `SQL_MCP_DEFAULT_SCHEMA` | Defaults `manufacturing` / `dbo` — only override if mirroring a different source |
| `ERP_INSTANCE_NAME` | UI label (default `ERP_Instance_1`) |

## Bottom line

Nothing to add to `.vscode/mcp.json` or `~/.copilot/mcp-config.json` for
this — just run the app and set the env vars. The only real MCP server in
the repo is `mrp-librarian` (`scripts/librarian_server.py`); see
`2026-07-04_mcp-setup-for-repo-copy-on-linux.md` in this folder.
