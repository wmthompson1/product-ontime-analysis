# ArangoDB Graph Query Reference
## manufacturing_graph — Six Core Traversals

**Graph:** `manufacturing_graph`
**Main vertex collection:** `manufacturing_graph_node` (schema layer)
**Semantic vertex collections:** `intents`, `perspectives`, `concepts`, `bindings` (sync layer)

---

## Graph Architecture Note

The graph contains two parallel layers built at different times:

| Layer | Collections | Vertex IDs |
|---|---|---|
| Schema layer (older) | `FOREIGN_KEY`, `HAS_COLUMN`, `ATOMIC_FK`, `CAN_MEAN`, `ELEVATES` (uppercase) | `manufacturing_graph_node/table_*` |
| Semantic sync layer (active) | `elevates`, `operates_within`, `uses_definition`, `bound_to` (lowercase) | `intents/*`, `perspectives/*`, `concepts/*`, `bindings/*` |

The lowercase semantic layer is the one maintained by `graph_sync.py` and is the active layer for new development.

---

## Query 1 — Graph Inventory

Count all documents across every collection. Run this first to confirm the graph is healthy.

```python
import os
from arango import ArangoClient
from arangodb_persistence import ArangoDBConfig

config = ArangoDBConfig()
client = ArangoClient(hosts=config.host)
db = client.db(
    config.database_name,
    username='root',
    password=os.environ.get('ARANGO_ROOT_PASSWORD', '')
)

col_names = [c['name'] for c in db.collections() if not c['name'].startswith('_')]
for name in sorted(col_names):
    col = db.collection(name)
    print(f'{name}: {col.count()} documents')
```

**Expected output (healthy graph):**

```
ATOMIC_FK: 8        elevates: 30        operates_within: 11
ELEVATES: 22        FOREIGN_KEY: 15     perspectives: 5
bindings: 19        HAS_COLUMN: 251     uses_definition: 20
bound_to: 11        intents: 11
concepts: 19        manufacturing_graph_node: 306
```

---

## Query 2 — Intent → Perspective (OPERATES_WITHIN)

Each analytical intent is scoped to exactly one organizational perspective. This traversal confirms all 11 intents are correctly wired.

```python
aql = '''
FOR e IN operates_within
    LET intent = DOCUMENT(e._from)
    LET persp  = DOCUMENT(e._to)
    SORT intent.intent_name
    RETURN {
        intent:      intent.intent_name,
        perspective: persp.perspective_name,
        weight:      e.weight
    }
'''
for r in db.aql.execute(aql):
    print(f'{r["intent"]:35s} → {r["perspective"]}  (w={r["weight"]})')
```

**Key fields:**
- `intent.intent_name` — e.g. `defect_cost_analysis`
- `persp.perspective_name` — one of: `Quality`, `Finance`, `Operations`, `Compliance`, `Customer`
- `e.weight` — always `1` (active path)

**Expected: 11 rows, one per intent, each mapping to exactly one perspective.**

---

## Query 3 — FK Traversal Inbound from a Table

Find all tables that reference a given table through foreign key relationships. Traverses up to 3 hops.

```python
graph_name = os.getenv('ARANGO_DB', 'manufacturing_graph')
node_col = f'{graph_name}_node'

aql = '''
FOR v, e, p IN 1..3 INBOUND CONCAT(@col, '/table_suppliers') FOREIGN_KEY
    RETURN {
        table:      v.name,
        via_column: e.from_column,
        depth:      LENGTH(p.edges)
    }
'''
results = list(db.aql.execute(aql, bind_vars={'col': node_col}))
for r in sorted(results, key=lambda x: x['depth']):
    print(f'depth={r["depth"]}  {r["table"]:35s}  via {r["via_column"]}')
```

**To traverse outbound** (tables that a given table references), change `INBOUND` to `OUTBOUND`:

```aql
FOR v, e IN 1..2 OUTBOUND CONCAT(@col, '/table_non_conformant_materials') FOREIGN_KEY
    RETURN {table: v.name, via: e.from_column, to_col: e.to_column}
```

**Swap the starting node** by changing `table_suppliers` to any table name prefixed with `table_`.

---

## Query 4 — Elevated Concepts Per Intent

Each intent binary-switches exactly one concept to weight=1 (elevated) while others are neutral (0) or suppressed (-1). This query returns only the elevated concept per intent.

```python
aql = '''
FOR e IN elevates
    FILTER e.weight == 1
    LET intent  = DOCUMENT(e._from)
    LET concept = DOCUMENT(e._to)
    SORT intent.intent_name
    RETURN {
        intent:  intent.intent_name,
        concept: concept.concept_name,
        domain:  concept.domain
    }
'''
for r in db.aql.execute(aql):
    print(f'{r["intent"]:35s} ELEVATES {r["concept"]}  [{r["domain"]}]')
```

**To see all weights for one intent** (elevated + neutral + suppressed):

```aql
FOR e IN elevates
    LET intent  = DOCUMENT(e._from)
    LET concept = DOCUMENT(e._to)
    FILTER intent.intent_name == 'defect_cost_analysis'
    SORT e.weight DESC
    RETURN {concept: concept.concept_name, weight: e.weight, explanation: e.explanation}
```

**Weight semantics:** `1` = elevated (use this interpretation), `0` = neutral, `-1` = suppressed.

---

## Query 5 — Bindings Chain (Intent → Binding → Concept Anchor)

Bindings link intents to APPROVED ground truth SQL snippets. Each binding carries a concept anchor, validation status, and path to the SQL file.

```python
aql = '''
FOR e IN bound_to
    LET intent  = DOCUMENT(e._from)
    LET binding = DOCUMENT(e._to)
    SORT intent.intent_name
    RETURN {
        intent:         intent.intent_name,
        binding_key:    binding.binding_key,
        concept_anchor: binding.concept_anchor,
        status:         binding.validation_status,
        logic_type:     binding.logic_type,
        sql_file:       binding.file_path
    }
'''
for r in db.aql.execute(aql):
    print(f'{r["intent"]:35s} → {r["concept_anchor"]:30s} [{r["status"]}]')
```

**Filter to APPROVED only:**

```aql
FILTER binding.validation_status == 'APPROVED'
```

**All bindings should be APPROVED.** A non-APPROVED binding indicates a pending SME review item and will be skipped by the SolderEngine during SQL assembly.

---

## Query 6 — Atomic Columns of a Table (HAS_COLUMN)

Retrieve all columns for a given table including data type and primary key flag. Useful for schema inspection and DDL round-trip validation.

```python
aql = '''
FOR v, e IN 1..1 OUTBOUND CONCAT(@col, '/table_production_lines') HAS_COLUMN
    SORT v.column_name
    RETURN {
        column:  v.column_name,
        type:    v.data_type,
        is_pk:   v.is_primary_key
    }
'''
for r in db.aql.execute(aql, bind_vars={'col': node_col}):
    pk = ' [PK]' if r['is_pk'] else ''
    print(f'{r["column"]:30s} {r["type"]}{pk}')
```

**To list all tables and their column counts:**

```aql
FOR e IN HAS_COLUMN
    LET tbl = DOCUMENT(e._from)
    COLLECT table = tbl.name WITH COUNT INTO col_count
    SORT table
    RETURN {table: table, columns: col_count}
```

**To find all tables containing a specific column name:**

```aql
FOR v IN manufacturing_graph_node
    FILTER v.node_type == 'atomic_column'
    FILTER v.column_name == 'product_line'
    RETURN v._key
```

---

## Running All Six as a Health Check

```python
import os, sys
sys.path.insert(0, '.')
from arango import ArangoClient
from arangodb_persistence import ArangoDBConfig

config = ArangoDBConfig()
client = ArangoClient(hosts=config.host)
db = client.db(config.database_name, username='root',
               password=os.environ.get('ARANGO_ROOT_PASSWORD', ''))
graph_name = os.getenv('ARANGO_DB', 'manufacturing_graph')
node_col   = f'{graph_name}_node'

checks = {
    'intents':          ('intents',          11),
    'perspectives':     ('perspectives',      5),
    'concepts':         ('concepts',         19),
    'bindings':         ('bindings',         19),
    'FOREIGN_KEY':      ('FOREIGN_KEY',      15),
    'HAS_COLUMN':       ('HAS_COLUMN',      251),
    'operates_within':  ('operates_within',  11),
    'elevates(w=1)':    (None,               11),  # AQL check
}

print('Collection counts:')
for label, (col, expected) in checks.items():
    if col:
        actual = db.collection(col).count()
        status = '✓' if actual == expected else f'✗ (expected {expected})'
        print(f'  {label:20s} {actual:4d}  {status}')

elevated = list(db.aql.execute('FOR e IN elevates FILTER e.weight == 1 RETURN 1'))
status = '✓' if len(elevated) == 11 else f'✗ (expected 11)'
print(f'  {"elevates(w=1)":20s} {len(elevated):4d}  {status}')

approved = list(db.aql.execute(
    'FOR b IN bindings FILTER b.validation_status == "APPROVED" RETURN 1'))
print(f'  {"approved_bindings":20s} {len(approved):4d}  {"✓" if len(approved) == 19 else "✗"}')
```
