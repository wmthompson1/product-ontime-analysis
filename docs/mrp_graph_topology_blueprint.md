# MRP Graph-Topology Blueprint — the Road Not Taken for the 7 MRP Concepts

**Status:** Architect/SME decision-support draft (Task #239 — blueprint only)
**Scope:** This document is **intelligence-gathering only.** It changes no code,
no manifest, no snippets, no graph, no `.obda`/`.ttl` files, and no
`graph_metadata.json`. Its purpose is to lay out, rigorously and with evidence,
what a *true* canonical-graph-path implementation — plus its Ontop/SPARQL and
SQLGlot parity consequences — would look like for the seven MRP/inventory
concepts, so the team can deliberately choose "stay pure-SQL" vs. "pivot to graph
topology" instead of taking Task #237's recommendation on faith.
**Dialect:** SQLite (`manufacturing.db`) — the synthetic ground-truth target.
**Inputs taken as given:** the set semantics defined in
`docs/mrp_set_semantics_criteria.md` (Task #237) and the pure-SQL snippets
authored to them (Task #238). This document does **not** redefine the set
semantics; it stress-tests the *modeling-surface* recommendation.

The seven concepts (manifest anchors in UPPERCASE; concept-node names in
TitleCase): **AllocatedQuantity, AvailableToPromise, LeadTimeDemand, SafetyStock,
MinimumStockQuantity, MaximumStockQuantity, EconomicOrderQuantity.**

---

## 1. Baseline and the boundary

### 1.1 What #237 concluded (restated)

Task #237 concluded that **all seven concepts should express their set membership
and time-phasing in the SQL snippet, not in the ArangoDB graph** (criteria §3).
The stated rationale: the semantic graph's job is *routing* — mapping a concept to
its anchor column and perspective via the existing `resolves_to` edges — and it
"cannot express row-level predicates like 'only `Open` orders whose `need_by_date`
falls in bucket M2' or 'on-hand plus firm receipts minus committed demand'."

That claim is **correct**, but it was asserted rather than demonstrated. The rest
of this document demonstrates it per concept, shows exactly where the boundary
sits, and identifies the one genuinely useful thing the graph *could* add
(navigation/interoperability) that pure-SQL does not.

### 1.2 The three-way classification

For each concept, the operative question is: *what kind of logic is it?* Three
categories, only the first of which a property graph can carry:

- **(a) Routing / navigation** — "this concept is anchored to this column under
  this perspective," or "this concept depends on these other concepts / these
  tables." This is exactly what the canonical graph already models with
  `resolves_to` (column→concept) and could model with new dependency edges
  (concept→concept, concept→table). A graph carries this natively.
- **(b) Row-level state predicate** — "count only `customer_order` rows whose
  `status = 'Open'`," "exclude `Cancelled` POs." A property graph stores nodes and
  edges, not per-row `WHERE` filters over live fact tables. The canonical graph
  here is a **schema/metadata graph** (23 tables, 230 columns, 43 concepts) — it
  has **no per-transaction-row vertices**, so a row-level predicate has nothing to
  attach to. This is not expressible as topology.
- **(c) Time-phased bucket arithmetic** — "net demand against supply across Past
  Due + M0..M5, carrying a running Projected Available Balance forward." This is
  ordered, stateful, cross-row arithmetic (window/running-sum semantics). Graph
  traversal has no notion of monthly buckets or a running balance. Not expressible
  as topology.

### 1.3 Per-concept classification (with reasons)

| Concept | Dominant logic class | Why the graph cannot carry the *definition* | Is there a *routing* facet a graph could add? |
|---|---|---|---|
| **AllocatedQuantity** | (b) row-level state predicate | Its value is `SUM(order_qty)` over `customer_order_line` rows whose parent `customer_order.status='Open'`. The graph has no order-line row vertices to filter. | Yes — a "depends-on-table" / "depends-on-concept" edge to `customer_order` state could *document* the dependency (navigation), never compute it. |
| **AvailableToPromise** | (b) + (c) | ATP = on-hand + scheduled receipts − Open demand, **time-phased** (cumulative PAB per bucket). Both a multi-table row-level netting and ordered bucket arithmetic — neither is topology. | Yes — dependency edges to AllocatedQuantity and to the supply tables (WO/PO) would make its composition navigable. |
| **LeadTimeDemand** | (c) + (b) | avg daily demand (Open-order demand over the §2.2 horizon) × `lead_time_days`. The rate is horizon-window arithmetic; the demand set is state-filtered. | Yes — a `resolves_to`/dependency edge to `part.lead_time_days` and to AllocatedQuantity documents inputs. |
| **SafetyStock** | (c) + (b) inherited | `reorder_point − LeadTimeDemand`; inherits LeadTimeDemand's window + state logic verbatim. | Yes — a concept→concept "derived-from LeadTimeDemand" edge is the *cleanest* graph use in the whole set (pure dependency, no arithmetic). |
| **MinimumStockQuantity** | (a) routing (policy proxy) | Value is simply `part.reorder_point` — a single column, no filter, no phasing. There is nothing *arithmetic* to keep out of the graph. | Yes — this is the best-fit candidate: a `resolves_to` edge to `part.reorder_point` already models it; a "policy-proxy" annotation is pure metadata. |
| **MaximumStockQuantity** | (a) routing + (b) light | `reorder_point + AVG(po_line.quantity)` restricted to non-Cancelled POs. The AVG-over-real-POs is a state-filtered aggregate. | Partial — dependency edges to `part.reorder_point` and `po_line.quantity` document inputs; the Cancelled-exclusion cannot live on an edge. |
| **EconomicOrderQuantity** | (a) routing + (b) light | Proxy = `AVG(po_line.quantity)` over real POs, fallback `reorder_point`. State-filtered aggregate + fallback branch. | Partial — same as Max; the fallback branch is snippet logic, not topology. |

**Boundary verdict:** for **six of the seven** concepts the *authoritative
definition* (the number the SolderEngine must return) is category (b) and/or (c)
and therefore **cannot** be carried by graph topology. The lone exception is
**MinimumStockQuantity**, whose definition *is* pure category (a) — a bare
`part.reorder_point` read already expressible by an existing `resolves_to`
elevation (§2.3) — but even there the graph only *routes* to the column; it does
not compute anything, because there is nothing to compute. Max/EOQ are mostly (a)
routing with a light (b) state-filtered aggregate on top, so their headline number
still needs SQL. Across the board the graph's only honest contribution is category
(a): **navigation and interoperability metadata** — "what does this concept depend
on / resolve to" — which is documentation *about* the definition, not the
definition itself. #237's SQL-only recommendation holds under scrutiny.

---

## 2. Hypothetical edge design (if we pivoted anyway)

This section answers "if the team *did* want the routing/navigation facet in the
graph, what would the edges look like?" — specified against the real fixed 6-slot
composite `_key` scheme and reserved-token rules. **None of these are proposed for
implementation here**; they are the concrete shape a future pivot would take.

### 2.1 The fixed 6-slot key scheme (recap of the real constraints)

From `graph_metadata.json` `key_scheme`:

```
template: table|concept : column|entity : family : perspective : predicate|none : unique_id|none
slots: 6   delimiter: ":"   fixed_width: true
forbidden in any component: ":", "/", ""    (empty)
```

- A **node** iff slots 5-6 == `none:none`.
  - concept node if slot 3 == `semantic` → `<ConceptName>:entity:semantic:canonical:none:none`
  - table node if slot 2 == `entity` (structural) → `<table>:entity:structural:system:none:none`
  - else column node → `<table>:<column>:structural:system:none:none`
- An **edge** otherwise; its family is slot 3 (`structural` or `semantic`).
- Reserved tokens: `entity` (slot 2 placeholder for a table/concept), `none`
  (slots 5-6 placeholder for a node), `system` (structural perspective scope),
  `canonical` (concept perspective-agnostic scope). A concept may **never** be
  named any grammar token (`entity`, `none`, `system`, `canonical`, `structural`,
  `semantic`); the exporter hard-fails on a collision.

The **existing** semantic edge shape (what all 37 `resolves_to` edges use):

```
form: <table>:<column>:semantic:<perspective>:resolves_to:<uid>   (_from = column node, _to = concept node)
example: PAYABLE:INVOICE_ID:semantic:Payables:resolves_to:PAY_RES_PAY_INV_1A2B3C4D
```

The `resolves_to` uid is **concept-stable and derived** (not counted):
`<perspective>_RES_<table>_<column>_<8-hex SHA1 of perspective|table|column|concept|field>`.
This is the M2 invariant: adding/removing one meaning never renumbers a column's
other edges.

### 2.2 Candidate edge families for the MRP concepts

Two kinds of "navigation" edge are conceivable. Both would be **new semantic
predicates** and would need the grammar, the exporter, the loader, and both parity
gates taught about them — a non-trivial platform change flagged in §3.

**(i) `depends_on` — concept → concept (composition/derivation).**
The single genuinely clean graph use in this set.

| Field | Value |
|---|---|
| Predicate name | `depends_on` |
| `_from` node kind | concept node (`<Concept>:entity:semantic:canonical:none:none`) |
| `_to` node kind | concept node |
| Cardinality | many-to-many (a concept can depend on several; several can depend on one) |
| Edge properties | optional `role` (e.g. `subtrahend`, `input`); binary `weight` gate to mirror `resolves_to` |
| Key form (hypothetical) | `<FromConcept>:entity:semantic:canonical:depends_on:<uid>` — the key template (`table\|concept : column\|entity : ...`) **already** permits a concept in slot 1 with `entity` in slot 2, so the *slot grammar* itself does not change. What must be extended is the **predicate/rule + exporter support**: `depends_on` is a new edge type the emit rules, predicate allow-list, and loader do not yet know about. |
| Concrete instances | `SafetyStock —depends_on→ LeadTimeDemand`; `AvailableToPromise —depends_on→ AllocatedQuantity`; `LeadTimeDemand —depends_on→ AllocatedQuantity` |
| Two-endpoint prune? | No — both endpoints are concept nodes (single namespace); prunes cleanly per-concept. |

**(ii) `derives_from` / dependency — concept → table or concept → column.**
Documents which physical inputs a concept's SQL reads.

| Field | Value |
|---|---|
| Predicate name | `derives_from` (concept→column) |
| `_from` node kind | concept node |
| `_to` node kind | column node (`<table>:<column>:structural:system:none:none`) |
| Cardinality | many-to-many |
| Edge properties | optional `input_role` (`demand_set`, `supply_set`, `lead_time`, `lot_size`); `state_filter` free-text (documentation only — **the graph cannot enforce it**) |
| Key form (hypothetical) | `<Concept>:entity:semantic:canonical:derives_from:<uid>` — the slot grammar accommodates a concept in slot 1, but `derives_from` is a **new predicate** (from-endpoint is a concept, to-endpoint is a column in a *different* table), so it needs new emit-rule/predicate-allow-list/exporter/loader support (not a change to the 6-slot template itself). |
| Concrete instances | `MaximumStockQuantity —derives_from→ po_line.quantity` (input_role=`lot_size`, state_filter=`purchase_order.status<>'Cancelled'`); `AllocatedQuantity —derives_from→ customer_order_line.order_qty` (input_role=`demand_set`, state_filter=`customer_order.status='Open'`) |
| **Two-endpoint prune?** | **Yes — critical.** Like the existing `references` (FK) edges, a `derives_from` edge spans **two table endpoints** (the concept's canonical namespace *and* a physical column's table). Per the established prune rule (see memory: *Pruning two-endpoint edges*), such edges must be **pruned/counted once over all stale names, not inside the per-table loop**, or a dry-run double-counts them. Any exporter/loader work would have to replicate the two-endpoint handling already used for `references`. |

**Why AvailableToPromise / LeadTimeDemand / SafetyStock still can't be "modeled"
by these edges:** the edges above only record *that* ATP depends on AllocatedQuantity
and on supply columns. The **netting** (on-hand + receipts − demand, cumulatively,
per bucket) is nowhere on any edge. A consumer traversing the graph learns the
composition but must still execute the SQL to get a number. That is the precise
boundary: **topology can describe the recipe; only SQL can cook it.**

### 2.3 The special case that fits best: MinimumStockQuantity

MinimumStockQuantity = `part.reorder_point` with **no filter, no phasing, no
aggregation**. It is already fully expressible with the **existing** `resolves_to`
edge — a column→concept elevation from `part.reorder_point` to a
`MinimumStockQuantity` concept node under an inventory-policy perspective, carrying
a "policy-proxy" note purely as metadata. No new predicate, no grammar change, no
two-endpoint issue. If any single concept were ever to "go graph," this is the one
that costs nothing — but note it *still* wouldn't need the graph to compute
anything; the value is a bare column read.

---

## 3. The full canonical graph path (what a pivot would actually cost)

If the team adopted any of §2's edges, this is the exact end-to-end machinery each
change would have to travel. It is deliberately heavyweight — that weight is the
core of the cost/benefit in §5.

1. **Seed the edges.** Author the new elevations in a `seed_elevations.py`-style
   batch (the same file that seeded the 37 `resolves_to` edges in batches 6-8 and
   the 43 concept nodes). For a *new predicate* (`depends_on` / `derives_from`)
   this is not just new rows — the seed, the key-grammar validator, and the
   exporter's predicate allow-list all need the new predicate added first.
2. **Re-export / materialize.** Run `export_graph_metadata.py`, which is
   **PRAGMA-based** for columns and materializes the canonical graph into the flat
   `sql_graph_nodes` / `sql_graph_edges` SQLite tables, then serializes
   `graph_metadata.json` **from those tables** (materialize → read-back). New edges
   get new rows and new `ordinal` values; emission order is deterministic and
   asserted downstream. Col-node count must still equal the PRAGMA count.
3. **Bump `SCHEMA_VERSION` + freeze the snapshot.** Increment `SCHEMA_VERSION`
   (currently **19**, milestone `mrp_demand_supply_foundation`; counts today: 296
   nodes / 306 edges = 23 table + 230 column + 43 concept; 230 has_column + 39
   references + 37 resolves_to). A new frozen `graph_metadata.v{N}.json` snapshot is
   written. **Frozen-once cost:** these versioned snapshots are frozen-once by
   convention — you bump `SCHEMA_VERSION` to re-freeze, and the committed snapshot
   becomes a permanent artifact for private-repo diffing. Every pivot burns a
   version number and a committed file.
4. **Resync the live graph.** Run `load_canonical_to_arango.py` to push the new
   nodes/edges into the live ArangoDB `manufacturing_graph`. **Caveat:** the live
   graph currently carries pre-existing drift (extra `concept_*` nodes → ~399 live
   vs. 296 canonical), so a resync must reconcile that first or the AQL gate stays
   red for reasons unrelated to the new edges.
5. **Pass both parity gates:**
   - **`sql_graph_parity_check.py` (SQLite ↔ `graph_metadata.json`)** — proves the
     JSON is field-for-field identical to the `sql_graph_*` tables, **including
     emission order**. This is **file-vs-SQLite, offline, deterministic**, and is
     the **authoritative acceptance gate** — it runs in `scripts/post-merge.sh` and
     cannot be skipped.
   - **`sql_aql_parity_check.py` (SQLite ↔ live ArangoDB via AQL)** — flattens the
     live graph (drops server `_rev`), compares field-for-field (order **not**
     asserted, since AQL is unordered). It **skips (exit 0) when ArangoDB is
     unreachable/unconfigured** (`--skip-on-missing`), so CI without a graph still
     passes. **Shared-cloud parity race:** because the live ArangoDB is a shared
     cloud instance, another process/agent resyncing concurrently can make this
     gate transiently disagree; it is therefore **not** the acceptance gate for a
     schema change — treat a genuine, stable diff as a fail and an unreachable/racing
     graph as a skip.

**Net:** a graph pivot for even one concept touches the seed, a predicate
allow-list/grammar extension, the exporter, a `SCHEMA_VERSION` bump, a new frozen
snapshot, a live resync (against known drift), and must keep the authoritative
file-vs-SQLite gate green. That is the true price of moving one line of navigation
metadata from SQL into topology.

---

## 4. Ontop/SPARQL and SQLGlot consequences

### 4.1 Ontop/SPARQL republication (interoperability dimension)

The POC at `poc/ontop-ontology-poc/` already proves the SQL layer can be
republished as a **virtual** OWL/SPARQL graph via Ontop (OBDA: maps SQLite → OWL,
answers SPARQL by rewriting to SQL — no data movement, no triplestore). Ontop is
the **publishing/interoperability layer, not an authoring or governance layer**;
SQL stays the single source of truth. So the question per concept is *not* "can the
graph compute it" (it can't, per §1) but "can the concept's **already-computed SQL
result** be published as triples another aerospace/enterprise system could query?"

Per concept, what republication would require and whether it is expressible:

| Concept | New `.obda` mapping | New `.ttl` term(s) | OWL 2 QL / SPARQL expressible? | Ontop+SQLite serialization notes |
|---|---|---|---|---|
| **AllocatedQuantity** | `source` = the corrected Open-demand `SUM` grouped by part; `target` mints `:part/{part_id} :allocatedQuantity {qty}` | datatype property `:allocatedQuantity` (range `xsd:double`) | Yes — single aggregated datatype property per part. | Use **`COALESCE(...,0)`** in both the `.obda` source and the grounding SQL so a part with no open demand still publishes `0` (SUM/COUNT showcases want COALESCE, **not** NULL-drop). |
| **AvailableToPromise** | Hardest. ATP is **per (part, bucket)** cumulative PAB. Would mint `:part/{part_id}/bucket/{k} :atp {qty}` or a reified `:AtpCell`. | class `:AtpCell` + properties `:atpBucket`, `:atpValue`, link `:hasAtpCell` | Partially — a reified per-bucket cell is expressible, but the **cumulative running balance** is computed in the source SQL, not by SPARQL. | **ATP scalar-split gotcha:** a non-aggregated value beside a `SUM` forces a `GROUP BY` that SQLite chokes on; the POC's demand-parity check splits ATP into separate scalar SPARQL queries (on-hand; summed open qty) and subtracts in Python. Any ATP republication inherits this split. Multi-table `OPTIONAL` (demand + supply) needs the **SQLGlot lift** (below). |
| **LeadTimeDemand** | `source` = avg-daily-demand-over-horizon × `lead_time_days`; `target` mints `:part/{part_id} :leadTimeDemand {qty}` | datatype property `:leadTimeDemand` | Yes — scalar per part. | Single-triple, single-table after the SQL does the rate math; SQLite-safe. |
| **SafetyStock** | `source` = `reorder_point − leadTimeDemand`; scalar per part | datatype property `:safetyStock` | Yes. | Scalar; SQLite-safe. Its `depends_on LeadTimeDemand` (§2) would map cleanly as `rdfs:subPropertyOf`-style documentation but adds no query power. |
| **MinimumStockQuantity** | `source` = `reorder_point`; scalar per part | `:minimumStockQuantity` | Yes — trivial. | Scalar; SQLite-safe. Best-fit concept for republication too. |
| **MaximumStockQuantity** | `source` = `reorder_point + AVG(po_line.quantity)` over non-Cancelled POs | `:maximumStockQuantity` | Yes — scalar per part. | The Cancelled-exclusion lives in source SQL. If mapped via an `OPTIONAL` over `po_line`+`purchase_order` (two tables), it needs the **SQLGlot lift**; if pre-aggregated in the source query, it's a plain scalar. |
| **EconomicOrderQuantity** | `source` = `AVG(po_line.quantity)` over real POs with `reorder_point` fallback | `:economicOrderQuantity` | Yes — scalar per part; fallback branch is source-side `CASE`. | Same two-table caveat as Max; pre-aggregate to stay single-triple/SQLite-safe. |

**"Define once, many perspectives" → OWL hierarchy.** The POC already models the
Ops/Supplier/Finance perspectives of one shared on-time definition as
`rdfs:subPropertyOf` a single parent property, all bound to the **same** mapping
SQL so they carry identical values (the standards-based restatement of
define-once-identical-SQL). If Min/Max/EOQ were ever published under multiple
perspectives, the same sub-property pattern applies.

**Known Ontop+SQLite serialization limits that any MRP republication inherits:**
- **Single-triple `OPTIONAL`.** A multi-triple `OPTIONAL` spanning >1 physical
  table (e.g. ATP's demand + supply, or Max/EOQ's `po_line`+`purchase_order`)
  serializes to a nested `LEFT JOIN` with stacked `ON` clauses that SQLite rejects
  (`near "ON"`). Fix: the **SQLGlot lift** (`sql_lift.py`) scrapes Ontop's
  DEBUG-level "Resulting native query" and re-parenthesizes the inner join so it
  parses. The lift is a **no-op** for single-triple or same-table OPTIONALs, so it
  is safe to run over all of them. A multi-table concept (ATP, and Max/EOQ if not
  pre-aggregated) is exactly the case that **needs** the lift.
- **SUM/COUNT + COALESCE vs. NULL-drop.** On-time/quality showcases deliberately
  emit **no triple** for a NULL so SPARQL `AVG` matches SQL `AVG` (NULL-drop).
  MRP **SUM/COUNT** concepts (AllocatedQuantity, and any count guard) want the
  **opposite**: `COALESCE(col,0)` in **both** the `.obda` source and the grounding
  SQL so a NULL never drops a row and the published population equals the governed
  population. Assert a COUNT alongside the SUM to catch population drift.
- **No `rdfs:domain` on link properties** — it makes Ontop infer the subject class
  from two sources and emit invalid `UNION`/`LEFT JOIN` SQL. Give link properties a
  `range` only.

### 4.2 New parity checker + CI wiring (if republished)

Each republished concept would need a **parity check** that recomputes the value
purely from graph triples and asserts it equals the governed SQL result, following
the established **read-only snapshot** pattern: open the live WAL DB read-only, take
a `sqlite3` backup snapshot, and point **both** Ontop and the grounding SQL at the
snapshot (never the live WAL file twice). A concept with **no** SolderEngine
template (most of these are plain approved snippets, not M4 metrics) grounds parity
against the **direct governed SQL**, not SolderEngine — do **not** invent a metric
template just to reuse a parity helper (that is scope creep into the semantic
layer). Wiring:
- Register each new `(label, obda, ttl)` in `mapping_drift_check.py`
  `DEFAULT_SHOWCASES`. That offline drift guard runs in `scripts/post-merge.sh`.
- **The drift/generation gates are regex parsers, not RDF parsers.** They see
  `a owl:Class`/`owl:*Property` declarations, local `rdfs:subPropertyOf`, and
  `.obda` byte-equivalence + vocabulary closure. Everything else
  (`skos:definition`, `rdfs:comment`, external-IRI alignment) is **invisible** —
  so enriching *already-declared* terms with annotations keeps both gates green,
  but a brand-new `:Term` with no `.obda` backing **fails** ontology→mapping
  closure. New mapped terms must ship mapping + parity together.
- Add a JVM-dependent step for the new parity check to
  `.github/workflows/ontop-interop-ci.yml` (Java 17 + pinned Ontop CLI via
  `ontop_poc_setup.py`). Keep JVM checks **out** of `post-merge.sh` (offline drift
  guard only there).

### 4.3 SQLGlot dimension — plain snippet vs. M4 `computation_template` metric

Independent of the graph, each concept's SQL surface is a choice between a **plain
approved snippet** (a whole `SELECT` file, transpiled on demand by SolderEngine via
`sqlglot.transpile(read="sqlite", write=<dialect>)`) and an **M4
`computation_template` metric** (a dialect-agnostic template with named
`{variable}` placeholders bound to physical columns via `resolves_to` edges
carrying `variable_name`; SolderEngine substitutes variables → table-qualified
columns and transpiles, guaranteeing **define-once → identical SQL** across
perspectives, and **failing closed** on missing/extra/conflicting/static/
unresolvable-join bindings).

| Concept | Better surface | Reason |
|---|---|---|
| AllocatedQuantity | plain snippet | Multi-row `SUM` with a join + by-bucket breakdown; too much shape for a single `{variable}` template. |
| AvailableToPromise | plain snippet | Time-phased netting reusing `mrp_engine` logic; not a scalar template. |
| LeadTimeDemand | plain snippet | Rate over a horizon window + join; templating buys nothing. |
| SafetyStock | plain snippet | Derived from LeadTimeDemand's shape; same reasoning. |
| **MinimumStockQuantity** | **M4 metric candidate** | A one-line scalar (`{reorder_point}`) — the natural define-once template; #237 explicitly flagged it as an optional promotion. |
| **MaximumStockQuantity** | plain snippet (metric only if pre-aggregated) | The `AVG`-over-real-POs is a subquery, not a bare column; a template would have to embed a subquery, which strains the "one distinct binding per placeholder" model. |
| **EconomicOrderQuantity** | plain snippet | Proxy + fallback `CASE`; not a clean scalar template. |

**Multi-dialect implication:** whichever surface is chosen, SolderEngine transpiles
SQLite → T-SQL/PostgreSQL/MySQL/BigQuery on demand. Plain snippets transpile the
whole authored `SELECT`; M4 metrics transpile the assembled expression. The
synthetic ground truth is always authored in **SQLite** (the target dialect);
real-source T-SQL files remain reference benchmarks only, never the synthetic
target. Promoting a concept to M4 is the **only** surface change that would touch
the graph (it needs `resolves_to` edges carrying `variable_name`) — and even then
it adds *binding* edges, not *topology* that computes the value.

---

## 5. Decision matrix and critical-path verdict

### 5.1 Per-concept decision matrix

Legend — **Pure-SQL:** authored snippet, no graph change (status quo).
**Graph-topology:** add `depends_on`/`derives_from` navigation edges (§2) via the
full canonical path (§3). **M4-metric:** promote to a `computation_template` metric
(§4.3).

| Concept | Pure-SQL | Graph-topology | M4-metric | Recommendation |
|---|---|---|---|---|
| **AllocatedQuantity** | ✅ definition lives here (state-filtered SUM) | ⚠️ only documents inputs; two-endpoint `derives_from`; cannot compute | ✖️ too much shape | **Pure-SQL.** Graph adds navigation-only metadata at full canonical-path cost — defer. |
| **AvailableToPromise** | ✅ time-phased netting (reuse `mrp_engine`) | ✖️ cannot carry buckets/running balance; only a composition edge | ✖️ not scalar | **Pure-SQL.** Highest-value *interoperability* candidate for Ontop republication *later*, but never graph-computed. |
| **LeadTimeDemand** | ✅ rate × lead time | ⚠️ `derives_from part.lead_time_days` documents only | ✖️ not scalar | **Pure-SQL.** |
| **SafetyStock** | ✅ `reorder_point − LeadTimeDemand` | ⚠️ **cleanest** graph use: `depends_on LeadTimeDemand` (concept→concept, no two-endpoint issue) — pure documentation | ✖️ not scalar | **Pure-SQL now.** If the team ever wants a navigable concept-dependency map, SafetyStock→LeadTimeDemand is the first, cheapest edge to add. |
| **MinimumStockQuantity** | ✅ `reorder_point` | ✅ already expressible via existing `resolves_to` (no new predicate) | ✅ natural scalar template | **Pure-SQL, with optional M4 promotion.** The one concept where graph/metric cost is near-zero — but the value (a bare column read) is also near-zero. Promote to M4 only if a define-once cross-dialect scalar is independently wanted. |
| **MaximumStockQuantity** | ✅ `reorder_point + AVG(real POs)` | ⚠️ two-endpoint `derives_from`; Cancelled-filter can't live on edge | ⚠️ only if pre-aggregated | **Pure-SQL.** |
| **EconomicOrderQuantity** | ✅ `AVG(real POs)` + ROP fallback | ⚠️ same as Max; fallback is snippet logic | ✖️ fallback branch resists templating | **Pure-SQL.** |

### 5.2 Cost/benefit summary

- **Benefit of a graph pivot:** at best, a **navigable concept-dependency /
  input-lineage map** (SafetyStock→LeadTimeDemand→AllocatedQuantity→columns) and a
  **standards-based SPARQL republication** other systems could consume. Both are
  *interoperability/documentation* wins, not computation wins.
- **Cost of a graph pivot:** for the `derives_from` family, a **new semantic
  predicate** (grammar extension + exporter allow-list + loader), **two-endpoint
  prune handling** (matching the `references`/FK edges), a **`SCHEMA_VERSION` bump +
  frozen snapshot per change**, a **live resync against known drift**, and keeping
  the authoritative file-vs-SQLite parity gate green. For republication, add
  `.obda`/`.ttl` authoring, the **SQLGlot lift** for multi-table concepts (ATP,
  Max/EOQ), the **COALESCE-vs-NULL-drop** discipline, the **ATP scalar-split**, a
  new **snapshot-based parity checker**, and a **CI (Java+Ontop) step**.
- **Asymmetry:** the cost is paid in platform/graph/CI machinery; the benefit never
  includes computing the concept (that stays in SQL regardless). The graph can
  describe the recipe; only SQL cooks it.

### 5.3 Critical-path verdict

**Adopting graph topology for any of the seven concepts does NOT put SPARQL or
SQLGlot work on the critical path for the current iteration — and none of it should
be adopted now.**

- The **authoritative definitions are all pure-SQL** (categories (b)/(c)); the
  graph provably cannot carry them. So the current iteration ships on pure-SQL
  snippets (#238) with **zero** graph, Ontop, or SPARQL dependency. #237's
  recommendation stands.
- Every graph/Ontop item above is **additive interoperability**, safely
  **deferrable** behind its own future task. Nothing here blocks #238; #238 does
  not block any of it.
- **If** the team later wants a navigable dependency map, the recommended **first,
  cheapest** step is the single concept→concept `depends_on` edge
  **SafetyStock → LeadTimeDemand** (no new two-endpoint handling, no arithmetic) —
  as a deliberate, separately-scoped pivot, not a reflex.
- **If** the team later wants SPARQL interoperability, **AvailableToPromise** is the
  highest-value republication target (and the one that most exercises the SQLGlot
  lift + ATP scalar-split) — again, a separate future task, never on this
  iteration's path.

**Bottom line:** stay pure-SQL for all seven concepts now. Treat graph topology and
Ontop/SPARQL as an optional, well-understood future interoperability layer whose
entry cost and boundaries are now documented — a deliberate choice, not a default.

---

## 6. This document is a blueprint only

No code, manifest, snippet, graph, `.obda`/`.ttl`, or `graph_metadata.json` change
is made by this task. Every edge, mapping, ontology term, parity checker, and CI
step described above is **hypothetical** — the specification of a road not taken,
provided so a future decision is informed rather than reflexive.
