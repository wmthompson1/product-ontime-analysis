# ArangoDB Fixtures and Persistence Helpers

This folder contains test fixtures and helper scripts for working with the
manufacturing semantic layer in ArangoDB.

Files:

- `vertices.json`, `edges.json` - Small fixture datasets for testing the
  `026_AQL_Path_Resolution_Test.aql` queries and local experiments.
- `import_vertices.js`, `import_edges.js` - JS helpers used by `arangosh`
  to import the fixtures into an ArangoDB instance mounted with the
  repository workspace.
- `run_persist.sh` - Convenience script to run `026_Entry_Point_NCM_Elevation_ArangoDB.py`
  with sane defaults and optional Docker-managed ArangoDB for local testing.

Important runtime note for `nx_arangodb`:

- The `nx_arangodb` library requires the following environment variables to
  be set before it attempts to connect:

  - `DATABASE_HOST` (e.g. `http://localhost:8529`)
  - `DATABASE_USERNAME` (e.g. `root`)
  - `DATABASE_PASSWORD` (must be a non-empty string; `nx_arangodb` treats an
    empty string as "not set")
  - `DATABASE_NAME` (e.g. `networkx_graphs`)

- If ArangoDB is running with `ARANGO_NO_AUTH=1`, set `DATABASE_PASSWORD` to a
  non-empty placeholder (for example `pass123`) so `nx_arangodb` will attempt
  the connection. Example:

```
export DATABASE_HOST=http://localhost:18529
export DATABASE_USERNAME=root
export DATABASE_PASSWORD=pass123
export DATABASE_NAME=networkx_graphs
./.venv/bin/python 026_Entry_Point_NCM_Elevation_ArangoDB.py
```

The `run_persist.sh` script in this folder automates these steps and can
optionally start a temporary ArangoDB Docker container for local testing.
