# Entry Point 020: ArangoDB Graph Persistence - Safe Usage Guide

Persist manufacturing schema graphs directly from SQLite to ArangoDB for faster session loading, team collaboration, and governed semantic layer operations.

## Safety Policy

### Credential Safety
- **Never hardcode passwords** in source files or commit them to version control.
- Store credentials in environment variables or Replit Secrets (`ARANGO_HOST`, `ARANGO_USER`, `ARANGO_ROOT_PASSWORD`, `ARANGO_DB`).
- The `ArangoDBConfig` class reads from environment variables automatically — no credentials appear in code.
- When logging connection info, `get_connection_info()` masks the password field.

### Write Safety
- **`overwrite=False` is the default.** Calling `persist_from_dicts()` without `overwrite=True` will **insert or update** documents, never drop existing collections.
- **`overwrite=True` drops the entire named graph** and its collections before re-creating. Use only when you intend a full replacement (e.g., refreshing from SQLite after drift).
- Individual node persistence uses **upsert logic**: if a document key already exists, it updates; otherwise it inserts. This prevents duplicate-key errors on re-runs.
- Edge inserts do **not** upsert — if you re-run without `overwrite=True`, you may get duplicate edges. Use `overwrite=True` for idempotent full syncs.

### Read Safety
- `load_graph()` is read-only — it queries vertex and edge collections and returns `{"nodes": [...], "edges": [...]}`. It never modifies ArangoDB.
- `list_graphs()` is read-only — returns graph names only.
- `test_connection()` is read-only — returns version and graph list.

### Destructive Operations (Require Explicit Confirmation)
- `delete_graph(name, drop_collections=True)` — permanently removes the named graph **and all its collections**. Data cannot be recovered unless you have a backup.
- `persist_from_dicts(..., overwrite=True)` — drops and re-creates. Equivalent to delete + insert.
- **Rule:** Never call destructive operations in automated scripts without a confirmation prompt or `--force` flag reviewed by a human.

### Database Creation Safety
- `_ensure_database_exists()` attempts to create the target database via `_system`. On cloud instances where `_system` access is restricted, it silently skips creation and assumes the database already exists.
- This means cloud deployments require **pre-creating the database** through the ArangoDB Cloud console.

### Collection Naming Safety
- Vertex collections are named from the `node_collection_field` key in each node dict (defaults to `"vertices"`).
- Edge collections are named from the `edge_relationship_field` key in each edge dict (defaults to `"edges"`).
- Document `_key` values are sanitized: `/` and spaces are replaced with `_` to comply with ArangoDB key constraints.

## Setup

### 1. Install ArangoDB

**macOS (Homebrew)**
```bash
brew install arangodb
brew services start arangodb
```

**Linux (apt)**
```bash
curl -OL https://download.arangodb.com/arangodb311/DEBIAN/Release.key
sudo apt-key add - < Release.key
echo 'deb https://download.arangodb.com/arangodb311/DEBIAN/ /' | sudo tee /etc/apt/sources.list.d/arangodb.list
sudo apt-get update
sudo apt-get install arangodb3
```

**Default Access**: http://localhost:8529

### 2. Install Python Dependencies

```bash
pip install python-arango
```

### 3. Set Environment Variables

In Replit Secrets or a local `.env` file:
```bash
ARANGO_HOST=http://localhost:8529
ARANGO_USER=root
ARANGO_ROOT_PASSWORD=your_password
ARANGO_DB=manufacturing_semantic_layer
```

## Data Flow

```
SQLite (schema_intents, schema_perspectives, schema_concepts, ...)
        |
        | Direct read via sqlite3
        v
Python dicts (nodes[], edges[])
        |
        | arangodb_persistence.persist_from_dicts()
        v
ArangoDB (named graph with vertex + edge collections)
        |
        | arangodb_persistence.load_graph()  -> {"nodes": [...], "edges": [...]}
        v
Python dicts (for use in SolderEngine, Dispatcher, Gradio UI)
```

No intermediate graph library is needed. Data flows directly from SQLite to ArangoDB using the `python-arango` client.

## Usage Patterns

### Pattern 1: Persist Semantic Layer from SQLite to ArangoDB

```python
import sqlite3
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

DB_PATH = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

node_list = []
for row in conn.execute("SELECT concept_id, concept_name, description FROM schema_concepts"):
    node_list.append({
        "id": f"concept_{row['concept_name']}",
        "table": "semantic_node",
        "node_type": "Concept",
        "name": row["concept_name"],
        "description": row["description"] or "",
    })

edge_list = []
for row in conn.execute("""
    SELECT p.perspective_name, c.concept_name
    FROM schema_perspective_concepts pc
    JOIN schema_perspectives p ON pc.perspective_id = p.perspective_id
    JOIN schema_concepts c ON pc.concept_id = c.concept_id
"""):
    edge_list.append({
        "from": f"perspective_{row['perspective_name']}",
        "to": f"concept_{row['concept_name']}",
        "relationship": "semantic_edge",
        "edge_type": "USES_DEFINITION",
    })
conn.close()

config = ArangoDBConfig()
persistence = ArangoDBGraphPersistence(config)

stats = persistence.persist_from_dicts(
    name="manufacturing_semantic_layer",
    nodes=node_list,
    edges=edge_list,
    vertex_collection="semantic_node",
    edge_collection="semantic_edge",
    overwrite=True
)

print(f"Persisted: {stats['nodes_inserted']} nodes, {stats['edges_inserted']} edges")
```

### Pattern 2: Load and Inspect a Persisted Graph

```python
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

config = ArangoDBConfig()
persistence = ArangoDBGraphPersistence(config)

status = persistence.test_connection()
print(f"Connected: {status['connected']}")
print(f"Available graphs: {status.get('graphs', [])}")

graph_data = persistence.load_graph(name="manufacturing_semantic_layer")

print(f"Nodes: {len(graph_data['nodes'])}")
for node in graph_data["nodes"][:5]:
    print(f"  {node.get('name', node.get('_key'))}: {node.get('description', '')}")

print(f"Edges: {len(graph_data['edges'])}")
for edge in graph_data["edges"][:5]:
    print(f"  {edge['_from']} -> {edge['_to']} ({edge.get('edge_type', '')})")
```

### Pattern 3: Safe Graph Replacement (with confirmation)

```python
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

config = ArangoDBConfig()
persistence = ArangoDBGraphPersistence(config)

graph_name = "manufacturing_schema"
existing = persistence.list_graphs()

if graph_name in existing:
    confirm = input(f"Graph '{graph_name}' exists. Overwrite? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted. No changes made.")
        exit()

stats = persistence.persist_from_dicts(
    name=graph_name,
    nodes=node_list,
    edges=edge_list,
    overwrite=True
)
print(f"Graph replaced: {stats}")
```

### Pattern 4: AQL Traversal (Native ArangoDB Query)

```python
from arango import ArangoClient
import os

client = ArangoClient(hosts=os.getenv("ARANGO_HOST", "http://localhost:8529"))
db = client.db(
    os.getenv("ARANGO_DB", "manufacturing_semantic_layer"),
    username=os.getenv("ARANGO_USER", "root"),
    password=os.getenv("ARANGO_ROOT_PASSWORD", "")
)

aql = """
FOR v, e, p IN 1..3 OUTBOUND @start_node
    GRAPH 'manufacturing_schema'
    RETURN {
        node: v.label,
        relationship: e.relationship_type,
        join_column: e.join_column,
        path_length: LENGTH(p.edges)
    }
"""
cursor = db.aql.execute(aql, bind_vars={"start_node": "schema_node/inventory"})
for doc in cursor:
    print(f"  {doc['node']} via {doc['relationship']} on {doc['join_column']}")
```

## Safety Checklist

| Action | Safe? | Notes |
|--------|-------|-------|
| `test_connection()` | Read-only | Returns version, graph list |
| `list_graphs()` | Read-only | Returns graph names |
| `load_graph()` | Read-only | Queries collections, returns `{"nodes": [...], "edges": [...]}` |
| `persist_from_dicts(overwrite=False)` | Insert/Update | Upserts nodes, inserts edges |
| `persist_from_dicts(overwrite=True)` | **Destructive** | Drops and re-creates graph |
| `delete_graph()` | **Destructive** | Removes graph and collections permanently |

## Refresh Script

When ArangoDB data drifts from the SQLite source of truth (e.g., manual edits in the web UI), run:

```bash
python refresh_arango_from_sqlite.py            # full refresh (overwrite=True)
python refresh_arango_from_sqlite.py --dry-run   # preview without writing
python refresh_arango_from_sqlite.py --db /path/to/manufacturing.db
```

This script is container-agnostic — it works the same whether ArangoDB runs in Docker, Podman, a VM, bare metal, or ArangoDB Cloud. Only the `ARANGO_*` environment variables need to point to the right host.

## Integration Architecture

```
+---------------------------------------------------+
| SQLite (manufacturing.db)                         |
| schema_intents, schema_perspectives,              |
| schema_concepts, schema_concept_fields,           |
| ground_truth_registry                             |
+-------------------------+-------------------------+
                          |
                          | sqlite3 read (read-only)
                          v
+---------------------------------------------------+
| arangodb_persistence.py                           |
| - ArangoDBConfig (env var credentials)            |
| - ArangoDBGraphPersistence (persist/load/delete)  |
| - Upsert logic for safe re-runs                   |
| - Overwrite protection by default                 |
+-------------------------+-------------------------+
                          |
                          | python-arango client
                          v
+---------------------------------------------------+
| ArangoDB                                          |
| - Named graphs with vertex + edge collections     |
| - AQL traversal for join pathfinding              |
| - Team collaboration via shared database          |
| - Cloud or local deployment                       |
+---------------------------------------------------+
```

## Environment Variable Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `ARANGO_HOST` | ArangoDB server URL | `http://localhost:8529` |
| `ARANGO_USER` | Database username | `root` |
| `ARANGO_ROOT_PASSWORD` | Database password | (empty) |
| `ARANGO_DB` | Target database name | `manufacturing_semantic_layer` |

## References

- **python-arango**: [python-arango docs](https://docs.python-arango.com/)
- **ArangoDB AQL**: [AQL Documentation](https://www.arangodb.com/docs/stable/aql/)
- **ArangoDB Downloads**: [arangodb.com/download](https://www.arangodb.com/download/)
- **Entry Point 018**: Structured RAG with Graph-Theoretic Determinism
