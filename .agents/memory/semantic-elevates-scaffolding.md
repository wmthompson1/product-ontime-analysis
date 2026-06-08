---
name: Semantic elevates scaffolding
description: How the canonical exporter wires the semantic elevates layer so plumbing is live but content stays empty until SME curation.
---

The exporter builds semantic `elevates` edges from SQLite (the source of truth).
The plumbing landed first as scaffolding (zero content); the **first SME batch of
3 elevations is now seeded** (see "First batch" below).

**Source join (SQLite):** `schema_concept_fields` (table,field→concept) ⋈
`schema_perspective_concepts` (concept→perspective + priority_weight) ⋈
`schema_perspectives` (id→name) ⋈ `schema_concepts` (id→name).

**Edge shape (locked, matches `graph_metadata_canonical_example.json`):** a
self-loop on the column node — `_from == _to == column_id` — family `semantic`,
type `elevates`, carrying `perspective`, `weight`, `concept`. Key is the 6-slot
`table:column:semantic:{perspective}:elevates:{uid}`; uid via the same
abbreviated allocator as references (`PAY_ELE_PAY_INV_001`).

**Why zero edges emit today:** the only curated `schema_concept_fields` rows
target `stg_manufacturing_flat`, a staging table that is NOT one of the 22
canonical business nodes. The builder guards endpoints exactly like references
edges — a column not in the exported node set is skipped and recorded in
`integrity["semantic_elevations_skipped"]`, never emitted as a dangling edge. It
lights up automatically when an SME maps a real ERP column.

**Invariants enforced:** perspective may never be the reserved token `system`
(owned by the structural layer) — `semantic_edge_key` hard-fails on it. The
loader cross-checks the dual invariant: structural edges are always `system`,
semantic edges never are.

**Curation heuristic (what makes a good elevation candidate):** rank by
discriminator (distinct-value) count, but the sweet spot is **bounded
categorical / status / type columns** — NOT unique IDs or free measures.
Unique IDs and continuous measures have the highest distinct counts yet carry no
*categorical* business meaning; near-constant flags carry too little. The real
semantic signal is a column with a small bounded set of business-meaningful
values (statuses, match states, types, site/location).
**Why:** those bounded categoricals are what actually separate rows by business
meaning under a perspective.

**How to apply:** to add real elevations, insert `schema_concept_fields` rows
pointing at canonical business `table.column` pairs (lowercase, matching node
keys) + link the concept to a perspective in `schema_perspective_concepts`, then
re-run the exporter and loader. No code change needed. All three semantic tables
carry UNIQUE natural keys (concept_name; (perspective_id,concept_id);
(table_name,field_name,concept_id)) so seeding via `INSERT OR IGNORE` + name
lookups is fully idempotent — there is a reusable name-based seeder script for
this (lives next to the exporter).

**First batch (seeded):** three bounded-categorical elevations —
inventory_transaction.site_id → Inventory_Transactions / WarehouseLocation;
invoice_header.three_way_match_status → Payables / ThreeWayMatchState;
customer_order.status → Receivables / OrderAccountingState (existing concept).
Result: exporter emits 3 `elevates` edges; live graph 231 nodes / 249 edges.

**Trace duality (durable domain rule):** inventory is traced at the **move**
(inventory_transaction; lot/serial genealogy in `trace`/`trace_inventory_trace`
bridges to a transaction_id), so its elevation is the warehouse site of the
move. Customer orders are traced at **shipment**, and there is no separate ship
table — the shipped state lives in `customer_order.status`. Shipment is also the
AR revenue-recognition trigger, which is why customer_order.status maps to the
existing "revenue recognition" order-state concept under Receivables.
