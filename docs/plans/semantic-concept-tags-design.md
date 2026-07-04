# Semantic Layer: Concept, Tags & Discriminator

## What & Why
Design notes for enriching the manufacturing semantic layer so a routing agent
(in the private repo) can derive a column's *meaning* — not just its structure —
from the graph. Covers three intertwined ideas raised in discussion: an array of
**tags**, the AQL to **derive a column's meaning**, the **discriminator /
component-field** pattern, and the **form that `concept` takes**.

The current canonical model: only two node types (tables, columns); `ELEVATES`
is the universal semantic predicate; `weight` is a binary gate (weight=0 *is*
suppression); `perspective` is an edge property; edges live in
`manufacturing_graph_edge`. Legacy structures (`manufacturing_semantic_layer_vertices`,
`CAN_MEAN`, `SUPPRESSES`, Perspective-as-vertex) are an older generation being retired.

---

## Design notes (the write-up — preserve verbatim)

### 1. What form does "concept" take?

In the graph, **`concept` is a string property on the `ELEVATES` edge** (next to
`perspective` and `weight`). But concept has a **dual representation**:

- **In SQLite (source of truth), concept is a first-class entity** — a row in
  `schema_concepts` (`concept_id`, `concept_name` UNIQUE), wired:
  - to perspectives via `schema_perspective_concepts` (+ `priority_weight`, `relationship_type`),
  - to columns via `schema_concept_fields` (+ `context_hint`, `component_index`, `is_primary_meaning`),
  - to intents via `schema_intent_concepts` (intent-level overrides).
- **In the graph, concept is flattened to a string**, because the graph keeps
  only two node types (tables, columns). Concept rides along as edge metadata.

So concept *exists* as a structured entity; it is just denormalized to a label
when it crosses into the graph.

**The "adding concept" decision** = whether concept should have identity *inside*
the graph (today it has none — you can filter the string but can't attach a
definition/synonyms/tags, nor traverse "all columns that share this concept"):

- **A — leave it as an edge string.** Simplest, fully deterministic; concept
  stays SQLite-only as a real entity.
- **B — give concept a companion collection** (mirror `schema_concepts` into a
  `Concepts` collection), *exactly how Perspective is already handled* (an edge
  property AND a loose bridge collection). Concept stays off the structural
  graph but gains a home for `domain`/family, definition, synonyms, and **tags**,
  and AQL can look it up. Most consistent with the existing architecture.
- **C — promote concept to a real graph node** (a third node type). Most
  expressive (traverse column → concept → sibling columns), but breaks the
  "only tables + columns are nodes" purity.

**Recommendation: B** — same pattern Perspective already uses, and the natural
home for the `tags` array.

**Current direction (converging on C):** the architect is **strongly advocating
Option C — Concept as a graph node** (a third node type). Accept the tradeoff:
we give up the "only tables + columns are nodes" invariant in exchange for
richer traversal (column → concept → sibling columns) and a first-class home for
each concept's synonyms / definition / domain / tags. Implications to work
through when we resume:
- Concept becomes a real vertex; the `ELEVATES` edge moves from
  `column → column` (self-loop carrying a `concept` string) to
  `column → concept` (the `concept` string becomes the target node's identity).
- `schema_concepts` (+ perspective/intent links) is the source of truth that
  seeds the concept nodes; the exporter and parity CSVs must learn the new node
  type and edge endpoints.
- The structural-vs-semantic split, the 6-slot key scheme, and the parity
  gates all need to account for a third node type.

**Tags — settled:** used as a **lightweight filter only** (coarse role/type
labels, AQL prefilter). They do not carry meaning; with Concept as a node, tags
live naturally on the concept vertex (and optionally on column nodes).

### 2. Would an array of tags help?

Yes, but as a **discovery / prefilter layer — not as the place meaning lives.**
Meaning is deterministic and SME-curated; it lives in `ELEVATES` edges carrying
`{perspective, weight, concept}`. Tags are flat strings with no
perspective-scoping, no weight gate, no concept identity — so they cannot express
"means X under Engineering, Y under Manufacturing." Pushing meaning into tags
forfeits the Solder Pattern guarantee.

Where tags earn their place:
- **Coarse role/type labels** for fast narrowing — `date`, `monetary`,
  `quantity`, `status`, `identifier`, `polymorphic-selector`.
- **A cheap candidate prefilter** before the graph traversal / SolderEngine
  selection. Arrays index well in Arango (`FILTER @tag IN n.tags`), so a routing
  agent can shrink the search space in one cheap hop, then let `ELEVATES` do the
  precise work.

Rule of thumb: **tags for "find me columns like this"; ELEVATES for "what this
column actually means."** Keep tags as a separate denormalized property (on the
column node and/or the Concept entity), never the source of truth.

### 3. AQL to derive a column's meaning

The `elevates` edge is a self-loop on the column node, so "what does this column
mean?" is a one-hop filter:

```aql
-- Forward: what does ONE column mean? (all active, perspective-scoped meanings)
LET col = DOCUMENT('manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none')
FOR e IN manufacturing_graph_edge
  FILTER e._from == col._id
     AND e.edge_type == 'elevates'
     AND e.weight == 1                      -- binary gate: skip deactivated
  RETURN { concept: e.concept, perspective: e.perspective }
```

The reverse direction is what a routing agent actually runs — "given the
perspective + concept I inferred from the question, which columns are
pre-approved?":

```aql
-- Reverse: the candidate set the LLM picks from (the Solder Pattern)
FOR e IN manufacturing_graph_edge
  FILTER e.edge_type == 'elevates'
     AND e.weight == 1
     AND e.perspective == @perspective
     AND e.concept == @concept
  LET col = DOCUMENT(e._from)
  RETURN { table: col.table_name, column: col.column_name }
```

With a tags prefilter layered on top:

```aql
FOR n IN manufacturing_graph_node
  FILTER n.node_type == 'column' AND @tag IN n.tags     -- cheap narrowing
  FOR e IN manufacturing_graph_edge
    FILTER e._from == n._id AND e.edge_type == 'elevates' AND e.weight == 1
    RETURN { table: n.table_name, column: n.column_name, concept: e.concept }
```

Concept-enriched (Option B — joins the companion `Concepts` collection):

```aql
LET col = DOCUMENT('manufacturing_graph_node/PAYABLE:INVOICE_ID:structural:system:none:none')
FOR e IN manufacturing_graph_edge
  FILTER e._from == col._id AND e.edge_type == 'elevates' AND e.weight == 1
  LET c = FIRST(FOR x IN Concepts FILTER x.concept_name == e.concept RETURN x)
  RETURN {
    perspective: e.perspective,
    concept:     e.concept,
    domain:      c.domain,        -- the "family"
    definition:  c.definition,
    tags:        c.tags
  }
```

### 4. The discriminator / component-field pattern — already modeled

"A field that means one thing when discriminator = A, another when = B" is
exactly `requirement.component_type`:
- `component_type = PART` → Engineering / as-designed (per-unit standard)
- `component_type = WORK_ORDER` → Manufacturing / as-built (actuals)
- `component_id` is polymorphic (a part_id or a wo_id depending on that same
  discriminator).

How it is modeled today (the durable lesson):
- The **same column gets multiple `ELEVATES` edges** (one per perspective/concept),
  or maps to multiple concepts via `component_index`.
- The **value condition** ("applies when component_type = PART") lives in
  `schema_concept_fields.context_hint` in SQLite — *not* on the edge. The edge
  stays minimal (`{perspective, weight, concept}`); the "when" stays in the
  source of truth.

For any new polymorphic column (e.g. a generic `value` that means weight when
`uom='WT'`, length when `uom='LN'`): add two elevates edges + two `context_hint`
rows, and also **elevate the discriminator column itself** — bounded categorical
selectors (`uom`, `status`, `component_type`) are the best elevation candidates
because their values are what separate meaning.

Where tags help the discriminator case: tag the selector column
`polymorphic-selector` and the dependent column `polymorphic-value`, so an agent
can find these conditional pairs in one query — while the conditional *meaning*
still comes from `context_hint` + the perspective edges.

**Design fork:** today the discriminator condition is human-readable text in
`context_hint` (not traversable). If the routing agent must *programmatically*
answer "what value of which column selects this meaning?", promote it to a
structured form — either a first-class graph edge (value-column → selector-column
carrying a value→concept map, sourced from the existing `schema_edges` registry)
or a structured field on the elevates edge (`when: {column, value}`). The
architecture's instinct is to keep edges minimal and the condition in SQLite, so
only promote it if the agent truly needs to traverse it.

---

## Done looks like
- Concept has an explicit, agreed form in the graph (recommended: Option B —
  a companion `Concepts` collection mirroring `schema_concepts`, carrying
  domain/family, definition, synonyms, tags).
- A curated `tags` array exists on column nodes (and/or the Concept entity) and
  is queryable as an AQL prefilter.
- The discriminator/value-routing condition is either confirmed as
  `context_hint`-only or promoted to a machine-readable form for the routing agent.
- Parity artifacts (the columnar CSVs + reports) continue to reflect any new
  fields so the private-repo agent can confirm resync.

## Out of scope
- Promoting concept to a full graph node (Option C) unless explicitly chosen.
- Any LLM-side changes to the dispatcher/SolderEngine selection logic.
- Backfilling tags for the full ~12.5k-column live graph (start with the
  curated/elevated set).

## Steps
1. **Decide concept's form** — confirm Option B (companion `Concepts` collection)
   vs A (edge string only) vs C (graph node).
2. **Add the `Concepts` collection + tags** — mirror `schema_concepts` (plus
   domain, definition, synonyms, tags) into a loose collection alongside the
   existing Perspective bridges; keep `concept` as the edge property.
3. **Add a curated `tags` array to column nodes** — seed coarse role/type tags
   for the elevated/curated columns; expose them in the export + parity CSVs.
4. **Resolve the discriminator fork** — keep value condition in `context_hint`,
   or promote it to a structured `when`/edge form sourced from `schema_edges`.
5. **Extend parity artifacts** — make the columnar CSVs + reports include any new
   node/edge fields so resync confirmation still holds.

## Relevant files
- `replit_integrations/export_graph_metadata.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app.py`
- `hf-space-inventory-sqlgen/scripts/seed_test_db.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
