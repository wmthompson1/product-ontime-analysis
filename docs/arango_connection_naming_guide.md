# ArangoDB Connection & Naming Guide

## How the Connection Works Today

The project connects to ArangoDB using four environment variables. Three are
stored as **secrets** (never visible in code) and one doubles as both a secret
and a shared environment variable:

| Variable               | Purpose                         | Where Set        |
|------------------------|---------------------------------|------------------|
| `ARANGO_HOST`          | Cloud endpoint URL              | Secret           |
| `ARANGO_USER`          | Database username               | Secret           |
| `ARANGO_ROOT_PASSWORD` | Database password               | Secret           |
| `ARANGO_DB`            | Database name **and** graph name| Secret + `.env`  |

The single most important thing to know:

> **`ARANGO_DB` controls both the database name and the graph name.**
> They are the same value: `manufacturing_graph`.

This means the ArangoDB database is called `manufacturing_graph`, and inside
that database lives a named graph also called `manufacturing_graph`.

---

## Where Each File Reads the Name

### 1. `arangodb_persistence.py` — The Foundation

`ArangoDBConfig` is the central connection class. Every script that talks to
ArangoDB goes through it:

```
ArangoDBConfig.__init__()
    database_name = os.getenv("ARANGO_DB")   ← reads from environment
    if not resolved:
        raise RuntimeError(...)              ← fail-fast if missing
    self.database_name = resolved
```

This is the **only place** the database connection is established. It reads
`ARANGO_DB` from the environment and uses it to connect to the correct
ArangoDB database. If `ARANGO_DB` is not set, the code refuses to run.

The graph name is passed separately when you call `persist_graph()` or
`load_graph()` — but by convention, scripts always pass the same value.

### 2. `solder_engine_extended.py` — The Query Layer

The extended engine reads the graph name at module level:

```
GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"
```

This sets two things:
- **GRAPH_NAME** — used in every AQL query as `GRAPH @graph_name`
- **VERTEX_COLLECTION** — the vertex collection name, always `{graph_name}_node`

The fallback `"manufacturing_graph"` means it works even without the env var
set, but in production the env var should always be present.

### 3. `config.py` — Shared Config

A simpler read with no fallback:

```
ARANGO_DB = getenv_compat("ARANGO_DB")
```

Used by scripts that import from `config.py` rather than building their own
`ArangoDBConfig`.

### 4. Loader Scripts (Fixtures, Semantic Graph, Refresh)

Every loader script follows the same pattern:

```
graph_name = os.getenv("ARANGO_DB", "manufacturing_graph")
COLLECTION = f"{graph_name}_node"
```

This includes:
- `load_atomic_nodes.py` — 251 column-level vertices
- `load_fk_edges.py` — 15 foreign key edges
- `load_bridge_edges.py` — table-to-concept bridges
- `persist_semantic_graph_to_arango.py` — 40 semantic nodes, 72 edges
- `refresh_arango_from_sqlite.py` — full graph rebuild

---

## The Naming Convention

Everything derives from `ARANGO_DB = manufacturing_graph`:

| Resource           | Name                          | How Derived             |
|--------------------|-------------------------------|-------------------------|
| ArangoDB database  | `manufacturing_graph`         | `ARANGO_DB` env var     |
| Named graph        | `manufacturing_graph`         | `ARANGO_DB` env var     |
| Vertex collection  | `manufacturing_graph_node`    | `{ARANGO_DB}_node`      |
| Edge collection    | `manufacturing_graph_edge`    | `{ARANGO_DB}_edge`      |
| Node `_key`        | `production_lines.line_id`    | `{table}.{column}`      |

If you ever changed `ARANGO_DB` to something else (say `mfg_v2`), every
collection and graph would follow automatically:

- Database: `mfg_v2`
- Graph: `mfg_v2`
- Vertices: `mfg_v2_node`
- Edges: `mfg_v2_edge`

No code changes needed — the naming flows from the single env var.

---

## How to Verify Your Connection

### Quick Check: Is the env var set?

In the Replit shell:

```bash
echo $ARANGO_DB
```

You should see: `manufacturing_graph`

### Quick Check: Can Python connect?

```python
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
config = ArangoDBConfig()
print(config.get_connection_info())
persistence = ArangoDBGraphPersistence(config)
print("Connected:", persistence._db.name)
```

### Quick Check: Does the graph exist?

```python
from solder_engine_extended import SolderEngineExtended
engine = SolderEngineExtended()
tables = engine.get_available_tables()
print(f"{len(tables)} tables in graph")
```

---

## Common Issues

**"ARANGO_DB is not set" RuntimeError**
The `ArangoDBConfig` fail-fast guard fired. Make sure `ARANGO_DB` is set in
both the Replit Secrets panel and as a shared environment variable. The value
should be `manufacturing_graph`.

**"manufacturing_graph_node collection not found"**
The database exists but the graph hasn't been populated yet. Run the atomic
node loader first:

```bash
python Utilities/ArangoFixtures/load_atomic_nodes.py
```

**Collections show `_system` instead of `manufacturing_graph`**
An older script (`persist_networkx_to_arango.py`) reads `ARANGO_DB` without a
fallback and may default to `_system` if the var is missing. Always ensure the
env var is set before running any loader.

**Graph name mismatch between database and code**
If someone hardcoded a different graph name (like `manufacturing_schema` in
the early `020_Entry_Point` scripts), those writes went to a different graph.
The current standard is `manufacturing_graph` everywhere, driven by `ARANGO_DB`.
