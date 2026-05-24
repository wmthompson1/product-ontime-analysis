# ArangoDB Graph Query Reference — DefineRelationship Mockup Edition
## manufacturing_graph — Mockup UI Data Mappings (Draft, not yet connected)

**Graph:** `manufacturing_graph`
**Reference doc:** `docs/arango_graph_queries.md` (original six core traversals)
**Mockup file:** `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`

This document maps each UI panel in the DefineRelationship mockup to the AQL query that will
power it once the Arango connection is wired. All stubs in the mockup call these by name — see
the `// --- DRAFT ARANGO LAYER ---` section at the top of the TSX.

---

## Architecture Change Note (post-Task #1)

The collection topology changed after the legacy perspective graph was retired. The original doc
(`arango_graph_queries.md`) still references `operates_within`, `uses_definition`, and
`perspectives` — those collections are retired. The **current** topology for new queries is:

| Layer | Active collections |
|---|---|
| Schema (ERP tables) | `manufacturing_graph_node`, `FOREIGN_KEY`, `ATOMIC_FK`, `HAS_COLUMN` |
| Semantic — intents/concepts | `intents`, `concepts`, `bindings`, `elevates`, `bound_to` |
| Semantic — bridge rows | `Perspective_Intents` (key: perspective__intent), `Perspective_Concepts` (key: perspective__concept) |

**Retired:** `perspectives` vertex collection, `operates_within` edge, `uses_definition` edge.

**Updated collection inventory (post-bridge model):**

```
ATOMIC_FK: 8          HAS_COLUMN: 251       Perspective_Intents: 11
bindings: 19          intents: 11           Perspective_Concepts: 20
bound_to: 11          concepts: 19
elevates: 30          FOREIGN_KEY: 15
manufacturing_graph_node: 306
```

---

## Query M1 — Load Entity Namespaces (Source & Target Panels)

Powers: the grouped results list in both **Select Source Entity** and **Select Target Entity**
columns. Returns all ERP tables (grouped under their ERP instance key) and semantic layer nodes
(intents, concepts, bindings — grouped under `"semantic_layer"`), formatted to match the
`SearchResult` / `GroupedResults` types in the mockup.

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
graph_name = os.getenv('ARANGO_DB', 'manufacturing_graph')
node_col   = f'{graph_name}_node'

# ERP tables — from the schema layer
aql_erp = '''
FOR v IN manufacturing_graph_node
    FILTER v.node_type == 'table'
    SORT v.name
    RETURN {
        table_name:     v.name,
        qualified_name: CONCAT('dbo.', UPPER(v.name)),
        namespace:      'ERP_Instance_1'
    }
'''

# Semantic layer nodes — intents, concepts, bindings
aql_semantic = '''
LET intent_nodes = (
    FOR i IN intents
        SORT i.intent_name
        RETURN {table_name: i.intent_name, qualified_name: CONCAT('intents/', i._key), namespace: 'semantic_layer'}
)
LET concept_nodes = (
    FOR c IN concepts
        SORT c.concept_name
        RETURN {table_name: c.concept_name, qualified_name: CONCAT('concepts/', c._key), namespace: 'semantic_layer'}
)
LET binding_nodes = (
    FOR b IN bindings
        SORT b.binding_key
        RETURN {table_name: b.binding_key, qualified_name: CONCAT('bindings/', b._key), namespace: 'semantic_layer'}
)
RETURN APPEND(APPEND(intent_nodes, concept_nodes), binding_nodes)
'''

erp_rows      = list(db.aql.execute(aql_erp))
semantic_rows = list(db.aql.execute(aql_semantic))[0]

grouped = {
    'ERP_Instance_1': [{'table_name': r['table_name'], 'qualified_name': r['qualified_name']} for r in erp_rows],
    'semantic_layer':  [{'table_name': r['table_name'], 'qualified_name': r['qualified_name']} for r in semantic_rows],
}
result = {
    'matches_found': len(erp_rows) + len(semantic_rows),
    'grouped_results': grouped,
}
```

**Mockup stub:** `fetchEntityNamespaces()` in DefineRelationship.tsx.
**Returns:** `SearchResult` object — same shape as `MOCK_SEARCH_DATA`.

---

## Query M2 — Load Intent List

Powers: the **Choose Intent** dropdown in the Define Relationship (Edge) panel.

```python
aql = '''
FOR i IN intents
    SORT i.intent_name
    RETURN i.intent_name
'''
intents = list(db.aql.execute(aql))
# → ["Avoid_Cost", "Defect_Cost_Analysis", "Quality_Defect", ...]
```

**Mockup stub:** `fetchIntents()` in DefineRelationship.tsx.
**Returns:** `string[]` — direct drop-in for the `INTENTS` constant.

---

## Query M3 — Load Concept List

Powers: the **Choose Concept** dropdown in the Define Relationship (Edge) panel.

```python
aql = '''
FOR c IN concepts
    SORT c.concept_name
    RETURN c.concept_name
'''
concepts = list(db.aql.execute(aql))
# → ["DefectSeverity", "DeliveryPerformance", "OEE", ...]
```

**Mockup stub:** `fetchConcepts()` in DefineRelationship.tsx.
**Returns:** `string[]` — direct drop-in for the `CONCEPTS` constant.

---

## Query M4 — Load Category / Perspective List

Powers: the **Category pill bar** at the top of the workspace. After Task #1, perspectives
live as a property on bridge rows in `Perspective_Intents`, not as a separate vertex collection.

```python
aql = '''
FOR row IN Perspective_Intents
    COLLECT perspective = row.perspective
    SORT perspective
    RETURN perspective
'''
categories = list(db.aql.execute(aql))
# → ["Customer_Order", "Demand_Forecast", "Engineering", ...]

# Alternative: read directly from SQLite (source of truth)
# SELECT DISTINCT perspective_name FROM schema_perspectives ORDER BY perspective_name
```

**Mockup stub:** `fetchCategories()` in DefineRelationship.tsx.
**Returns:** `string[]` — direct drop-in for the `CATEGORIES` constant (without the "ALL" sentinel, which is added by the UI).
**Note:** SQLite is the canonical source; the Arango form above is a consistency check.

---

## Query M5 — Resolve Perspective_Intents Bridge Key

Powers: the violet **Perspective_Intents** cell in the Live Identity Preview strip.
Given a selected (intent, perspective) pair, returns the exact bridge-row `_key` stored in
`Perspective_Intents`.

```python
aql = '''
FOR row IN Perspective_Intents
    FILTER row.perspective == @perspective
    FILTER row.intent      == @intent
    LIMIT 1
    RETURN row._key
'''
rows = list(db.aql.execute(aql, bind_vars={
    'perspective': 'Engineering',
    'intent':      'Avoid_Cost',
}))
bridge_key = rows[0] if rows else None
# → "AVO_001_Engineering"
```

**Mockup stub:** `fetchIntentBridgeKey(intent, perspective)` in DefineRelationship.tsx.
**Returns:** `string | null` — null when perspective is "ALL" (no bridge row to look up).
**Key format:** `{XXX}_{NNN}_{Perspective}` where XXX = first 3 chars of intent name (uppercase).
**Current mockup behaviour:** computes the key locally using `seg3(intent)` — the live query
is the authoritative form that will replace it.

---

## Query M6 — Resolve Perspective_Concepts Bridge Key

Powers: the fuchsia **Perspective_Concepts** cell in the Live Identity Preview strip.

```python
aql = '''
FOR row IN Perspective_Concepts
    FILTER row.perspective == @perspective
    FILTER row.concept     == @concept
    LIMIT 1
    RETURN row._key
'''
rows = list(db.aql.execute(aql, bind_vars={
    'perspective': 'Engineering',
    'concept':     'DefectSeverity',
}))
bridge_key = rows[0] if rows else None
# → "DEF_001_Engineering"
```

**Mockup stub:** `fetchConceptBridgeKey(concept, perspective)` in DefineRelationship.tsx.
**Returns:** `string | null`.
**Key format:** `{CCC}_{NNN}_{Perspective}` where CCC = first 3 chars of concept name (uppercase).

---

## Query M7 — Commit New Edge ("Add to Graph")

Powers: the **Add to Graph** button. The target collection depends on the selected predicate.

### Predicate routing table

| UI Predicate | Arango target | Write type |
|---|---|---|
| `FOREIGN_KEY` | `FOREIGN_KEY` edge collection | Edge `{_from, _to, from_column, to_column}` |
| `ELEVATES` | `elevates` edge collection | Edge `{_from, _to, weight: 1, explanation}` |
| `SUPPRESSES` | `elevates` edge collection | Edge `{_from, _to, weight: -1, explanation}` |
| `MAPS_TO_CONCEPT` | `CAN_MEAN` edge collection (schema layer) | Edge `{_from, _to}` |
| `HAS_COLUMN` | `HAS_COLUMN` edge collection | Edge `{_from, _to}` |
| `BOUND_TO` | `bound_to` edge collection | Edge `{_from, _to, binding_key, concept_anchor}` |
| `OPERATES_WITHIN` | **retired** — write to `Perspective_Intents` document collection instead | Document `{_key, perspective, intent}` |

### ELEVATES example

```python
def commit_elevates_edge(db, source_id: str, target_id: str, intent: str, weight: int = 1) -> dict:
    """
    source_id: e.g. "manufacturing_graph_node/table_production_orders"
    target_id: e.g. "concepts/DEFECT_SEVERITY_COST"
    """
    aql = '''
    INSERT {
        _from:       @source,
        _to:         @target,
        weight:      @weight,
        intent_name: @intent,
        created_by:  'define_relationship_ui'
    } INTO elevates
    RETURN NEW
    '''
    result = list(db.aql.execute(aql, bind_vars={
        'source': source_id,
        'target': target_id,
        'weight': weight,
        'intent': intent,
    }))
    return result[0]
```

### OPERATES_WITHIN → Perspective_Intents bridge row (bridge model)

```python
def commit_perspective_intent_bridge(db, intent: str, perspective: str, seq: int = 1) -> dict:
    """
    Writes a new Perspective_Intents bridge row.
    Replaces the retired OPERATES_WITHIN edge approach.
    _key convention: {XXX}_{NNN}_{Perspective}
    """
    seg3 = lambda s: ''.join(c for c in s if c.isalpha())[:3].upper()
    key = f'{seg3(intent)}_{str(seq).zfill(3)}_{perspective}'
    doc = {
        '_key':        key,
        'perspective': perspective,
        'intent':      intent,
        'created_by':  'define_relationship_ui',
    }
    db.collection('Perspective_Intents').insert(doc, overwrite=True)
    return doc
```

**Mockup stub:** `commitEdge(predicate, sourceId, targetId, intent, perspective)` —
currently a no-op console.log in DefineRelationship.tsx (see the Add to Graph button handler).

---

## Query M8 — Edge Key Assembly (rel_edge_id)

Powers: the cyan **rel_edge_id** cell in the Live Identity Preview strip. This is a computed
value, not a live query — the mockup assembles it locally via `assembleEdgeId()`. The formula
is documented here for when the edge is persisted to Arango as the `_key` of the committed edge.

```
_key format:  {LLL}_{RRR}_{XXX}_{NNN}_{Perspective}
  LLL = first 3 chars of source table name (uppercase, alpha only)
  RRR = first 3 chars of target table name (uppercase, alpha only)
  XXX = first 3 chars of intent name (uppercase, alpha only)
  NNN = zero-padded collision counter (001, 002, …)
  Perspective = the active category/perspective string

Example: PRO_INT_AVO_001_Engineering
  PRO = production_orders  RRR = intents  AVO = Avoid_Cost  001  Engineering
```

**Collision check query** — before inserting, verify the proposed key doesn't exist:

```python
aql = '''
FOR e IN elevates
    FILTER e._key == @proposed_key
    RETURN 1
'''
exists = list(db.aql.execute(aql, bind_vars={'proposed_key': 'PRO_INT_AVO_001_Engineering'}))
# If exists is non-empty, increment NNN and retry.
```

---

## Integration Checklist (when Arango is ready to connect)

- [ ] Replace `fetchEntityNamespaces()` body: call `/mcp/tools/list_graph_entities` or run M1 AQL directly
- [ ] Replace `fetchIntents()` body: call `/mcp/tools/get_intents` or run M2 AQL
- [ ] Replace `fetchConcepts()` body: call `/mcp/tools/get_concepts` or run M3 AQL
- [ ] Replace `fetchCategories()` body: call `/mcp/tools/get_perspectives` or run M4 AQL
- [ ] Replace `fetchIntentBridgeKey()` body: call M5 AQL (drop the local `seg3` computation)
- [ ] Replace `fetchConceptBridgeKey()` body: call M6 AQL (drop the local `seg3` computation)
- [ ] Wire the **Add to Graph** button to `commitEdge()` using M7 routing table
- [ ] Implement collision counter increment for M8 edge-key uniqueness
- [ ] Add error boundary / fallback to mock data when the API is unreachable
