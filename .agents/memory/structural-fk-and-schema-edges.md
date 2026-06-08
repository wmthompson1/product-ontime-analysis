---
name: Structural FK layer, schema_edges registry, canonical versioning
description: How declared FKs, the schema_edges logical registry, and the frozen graph_metadata snapshots behave in the SQLite source-of-truth.
---

# Declared FKs are structural metadata, not data validation

The manufacturing.db runs with runtime FK enforcement **OFF** (PRAGMA foreign_keys
defaults off; nothing turns it on at app start). Declaring a FOREIGN KEY therefore
records a *relationship*, it does not validate data. Declaring FKs "over" existing
orphan rows is the **established norm** here (pre-existing FKs already sit over dirty
data, e.g. inventory_transaction has ~181 orphan part_id rows).

**part_id orphans are real data dirt, not a fixable migration bug:** `part` holds
only ~31 parts (P-10010..P-10040); child tables mix `P-`/`PN-` prefixes, reference a
`PN-100x0` family that does not exist, and `po_line.part_id` even stores service codes
(`ANODIZE-III` etc). Do not try to "repair" these by prefix rewriting — they are
genuinely inconsistent synthetic data. Declare the FK anyway (it is structural).

**Why:** the graph models declared schema relationships; data cleanliness is a
separate concern and enforcement is intentionally off.

**How to apply:** to add FK relationships, rebuild the table with appended
`FOREIGN KEY` clauses (PRAGMA can't ALTER-ADD a FK), copy rows, recreate indexes,
run `foreign_key_check` as a report (tolerate orphans), commit. Always back up the
DB first. `operation.vendor_id -> suppliers.supplier_id` is a deliberate cross-named
FK (vendor == supplier here), user-approved.

# schema_edges is a logical FK registry — one row per relationship

`schema_edges` is meant to hold exactly ONE row per (from_table, to_table,
join_column) — it is the deferred ELEVATES/NL layer's registry (carries
natural_language_alias, few_shot_example, context). The seed
(`seed_erp_synthetic.py:seed_schema_edges`) uses `INSERT OR IGNORE`, but **without a
unique index OR IGNORE never conflicts**, so repeated seeding silently bloated it to
~1900 rows (~101 identical dups per relationship, differing only in created_at).

Fix: dedup keeping `MIN(rowid)` per (from_table,to_table,join_column) and add
`CREATE UNIQUE INDEX ux_schema_edges_logical` — that makes the existing INSERT OR
IGNORE genuinely idempotent. App consumers (database_hints_loader, main.py Define-
Relationship endpoint, metadata_query_templates) all query by relationship, so dedup
is strictly beneficial (was producing duplicate hints).

# Canonical graph_metadata snapshots are frozen-once

`export_graph_metadata.py` writes `graph_metadata.json` (latest, always overwritten)
plus `graph_metadata.v{SCHEMA_VERSION}.json` (a milestone snapshot, **created once,
never clobbered**). To record a meaningful content change you must bump
`SCHEMA_VERSION` (+ `MILESTONE_NAME`) so a new frozen snapshot is written; otherwise
latest and the old snapshot drift while sharing one version stamp. History:
v3=`wave4_traceability` (18 references, pre-FK-completion), v4=`structural_fk_complete`
(37 references). The exporter **excludes schema_* metadata tables** (it models the
domain, not its own bookkeeping), so total declared FKs 46 = 37 real ERP + 9 on
schema_* tables; canonical references count == 37.
