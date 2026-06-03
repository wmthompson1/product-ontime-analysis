# replit_integrations

Reusable Python modules that the private Windows / SQL Server repo imports directly
from this public repo's root via `PYTHONPATH`.

---

## ⚠️ Runtime Path Execution Constraints

The local private repository maps SQLMesh models under nested structures
(`SQL-Projects/Utilities/SQLMesh/`).

### Path Alignment Rules (queue-router-agent)
- When initializing SQLMesh contexts via Python runtimes, the execution engine must
  explicitly prepend the `SQL-Projects` parent directory to `sys.path` or set the
  local shell's `PYTHONPATH` variable.
- This prevents `ModuleNotFoundError: No module named 'Utilities'` failures during
  model loading passes.

---

## 📐 Approved Architectural Decisions (Plan-008 Integration)

### 1. Query Performance Strategy
- **Decision:** Option A — Execute direct database queries on every function invocation.
- **Rationale:** Keeps memory footprints minimal within the Replit container. Since
  metadata operations pull trivial row counts from a local SQLite instance, the overhead
  is negligible and guarantees fresh, synchronized data states.

### 2. Architecture Layout & Modularization
- **Decision:** Option A — Implement procedural, module-level functional exports.
- **Rationale:** Preserves complete functional symmetry with production automation
  scripts inside `scripts/`. Avoids complex class instantiations or connection-pooling
  mechanisms where simple contextual handles are sufficient.

### 3. Cross-Repository Graph Validation
- **Decision:** Option B — Include offline ArangoDB `_key` format assertions directly
  in the metadata demo workflows.
- **Rationale:** Validates that key patterns match standard string conventions
  (e.g., double-colon layout `prefix::TABLE.COLUMN`) directly from SQLite records,
  ensuring graph sync readiness without establishing live network transports.

---

## Graph Metadata Extraction

### What these modules do

| Module | Purpose |
|---|---|
| `graph_metadata_queries.py` | Path resolver + SQLite connection wrapper; returns `pandas.DataFrame` |
| `metadata_query_templates.py` | Library of pre-built SQL strings for every semantic layer table |
| `graph_metadata_demo.py` | Runnable five-example demo script |

These modules give the private repo read access to `manufacturing.db`'s semantic
layer without duplicating SQL or importing anything from the HF Space app.

---

## Setup: PYTHONPATH requirement

The private repo (Windows, SQL Server) must have its `PYTHONPATH` set to the root
of this cloned public repo so that `replit_integrations` is importable as a package.

**PowerShell (Windows):**
```powershell
$env:PYTHONPATH = "C:\path\to\SQL-Projects"
python -c "from replit_integrations.graph_metadata_queries import get_graph_metadata; print('OK')"
```

**bash / zsh (macOS / Linux / Replit):**
```bash
export PYTHONPATH="/path/to/SQL-Projects"
python -c "from replit_integrations.graph_metadata_queries import get_graph_metadata; print('OK')"
```

Or set it permanently in your shell profile / `.env` file.

---

## Quick start

```python
from replit_integrations.graph_metadata_queries import get_graph_metadata
from replit_integrations.metadata_query_templates import (
    list_perspectives,
    intent_concept_elevations,
    foreign_key_graph,
    polymorphic_field_meanings,
)

# List all perspectives
df = get_graph_metadata(list_perspectives())
print(df[["perspective_name", "stakeholder_role"]])

# Concept elevations for a specific intent (intent_id=1)
df = get_graph_metadata(intent_concept_elevations(1), params=[1])
print(df[["concept_name", "intent_factor_weight"]])

# All foreign-key edges
df = get_graph_metadata(foreign_key_graph())
print(df.head())

# Polymorphic meanings for a specific field
sql = polymorphic_field_meanings("work_order", "status")
df = get_graph_metadata(sql, params=["work_order", "status"])
print(df)
```

---

## Database path resolution

`get_manufacturing_db_path()` resolves the SQLite path in this order:

1. **`SQLITE_DB_PATH` environment variable** — set this when running from outside
   the public repo root (e.g., from the private repo directory).
2. **Relative fallback** — `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
   relative to the current working directory.  Works when you `cd` to the repo root
   before running.

```bash
# Option A: run from repo root (fallback resolves automatically)
cd /path/to/SQL-Projects
python replit_integrations/graph_metadata_demo.py

# Option B: set env var and run from anywhere
export SQLITE_DB_PATH="/path/to/SQL-Projects/hf-space-inventory-sqlgen/app_schema/manufacturing.db"
python replit_integrations/graph_metadata_demo.py
```

---

## Available query templates

### Perspective

| Function | Returns |
|---|---|
| `list_perspectives()` | All rows from `schema_perspectives` |
| `perspective_concept_map()` | Perspective → concept relationships with concept details |
| `perspective_intent_weights()` | Perspective → intent OPERATES_WITHIN weights |

### Concept

| Function | Returns |
|---|---|
| `concept_hierarchy()` | Concepts with parent concept (REFINES relationship) |
| `concept_field_mappings()` | All field → concept CAN_MEAN mappings |
| `polymorphic_field_meanings(table_name, field_name)` | All concept meanings for one field |

`polymorphic_field_meanings` uses `?` placeholders — pass `params=[table_name, field_name]`:
```python
sql = polymorphic_field_meanings("work_order", "status")
df  = get_graph_metadata(sql, params=["work_order", "status"])
```

### Intent

| Function | Returns |
|---|---|
| `intent_concept_elevations(intent_id)` | Concept weights for one intent (1=elevated, -1=suppressed) |
| `intent_perspective_constraints(intent_id)` | Perspective constraints for one intent |
| `intent_query_mappings()` | All intent → ground truth SQL file mappings |

`intent_concept_elevations` and `intent_perspective_constraints` use a single `?`
placeholder — pass `params=[intent_id]`.

### Schema

| Function | Returns |
|---|---|
| `table_metadata()` | All rows from `schema_nodes` (ERP table registry) |
| `column_metadata(table_name)` | Column descriptions from `api_field_descriptions` for one table |
| `foreign_key_graph()` | All rows from `schema_edges` (join graph) |
| `foreign_key_edges_from_table(table_name)` | Edges where from_table OR to_table matches |

`column_metadata` and `foreign_key_edges_from_table` use `?` placeholders:
```python
df = get_graph_metadata(column_metadata("purchase_order"), params=["purchase_order"])
df = get_graph_metadata(foreign_key_edges_from_table("work_order"), params=["work_order", "work_order"])
```

### Component

| Function | Returns |
|---|---|
| `polymorphic_components()` | Fields with >1 concept meaning (meaning_count, concept_names) |
| `binding_key_resolution(component_id)` | Physical column bindings for a concept (concept_id) |

`binding_key_resolution` uses a single `?` placeholder — pass `params=[concept_id]`.

---

## Troubleshooting

### `FileNotFoundError: manufacturing.db not found`

The DB path could not be resolved.  Fix options:
- Run from the repo root: `cd /path/to/SQL-Projects && python replit_integrations/graph_metadata_demo.py`
- Set `SQLITE_DB_PATH` to the absolute path of `manufacturing.db`

### `sqlite3.OperationalError: no such table: ...`

The table name in the SQL template does not exist in your copy of `manufacturing.db`.
This can happen if migrations have not been applied.  Run the migrations in
`hf-space-inventory-sqlgen/migrations/` against your local DB.

### `ModuleNotFoundError: No module named 'replit_integrations'`

`PYTHONPATH` is not set to the repo root.  See the **Setup** section above.

### `ModuleNotFoundError: No module named 'pandas'`

Install pandas in your Python environment:
```bash
pip install pandas
```

---

## Connection pattern

Both modules use a **connection-per-call** pattern: `get_graph_metadata()` opens a
new `sqlite3` connection, executes the query with `pd.read_sql_query`, and closes it
before returning.  There is no shared persistent connection.  `close_connection()` is
a no-op stub provided for callers that follow a connect/query/close lifecycle.
