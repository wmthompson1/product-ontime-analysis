# Graph Registration

This document explains how the schema persister registers a Gharial graph in ArangoDB and provides a small helper script to register the graph manually or from CI.

Overview
-
- By default `scripts/persist_to_arango.py` will attempt to persist edges and nodes and register a Gharial graph that wires `<graph>_edges` to `<graph>_nodes`.
- If you prefer to skip automatic graph registration, run the persister with `--no-register` and then run the registration helper separately.

Helper script
-
Use the `scripts/register_graph.sh` script to register the graph explicitly. The script reads values from your `.env` (if present) or from the environment.

Usage example
```
# make sure env is loaded
set -a && source .env && set +a
./scripts/register_graph.sh
```

Environment variables
-
- `DATABASE_HOST` (default: `http://localhost:8529`)
- `DATABASE_USERNAME` (default: `root`)
- `DATABASE_PASSWORD` (no default — recommended)
- `DATABASE_NAME` (default: `manufacturing_graphs`)
- `GRAPH_NAME` (default: `manufacturing_schema_v1`)

CI integration
-
In CI you can run the persister followed by the register script (or use `--no-register` and call the script explicitly):

```
python3 scripts/persist_to_arango.py --no-register
./scripts/register_graph.sh
```

Notes
-
- The helper is idempotent: Arango will return success if the graph already exists. The script prints the JSON response from the Arango API.
