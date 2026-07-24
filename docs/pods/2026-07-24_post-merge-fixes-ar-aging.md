# Post-Merge Fixes — AR Aging Governed View (2026-07-24)

Three post-merge gaps corrected after Task #281 (AR aging governed view) merged
without re-exporting the graph metadata.

---

## Root Cause

The Task #281 merge ran without re-freezing `graph_metadata.json`, leaving three
artifacts stale. Additionally, the `ledger_events.ttl` ontology vocabulary gate
failed because `:AccountsReceivable` was referenced as a flow-property range but
never declared as a term.

---

## Fixes Applied

### 1. Ontology TTL — free-floating `:AccountsReceivable`
Declared `:AccountsReceivable` as an `owl:Class` in `ledger_events.ttl`.  
The `:collectsAccountsReceivable` property's `rdfs:range` was pointing at an
undeclared term, failing the `ledger_events_vocab_check.py` gate:

> `[FAIL] every referenced :Term is declared here or in the SKOS scheme — free-floating: ['AccountsReceivable']`

Fix: added alongside `:WorkOrder` (same pattern — endurant entity class, not a
flow concept declared in the SKOS scheme).

### 2. Graph metadata re-frozen at SCHEMA_VERSION 32 (`ar_aging_binding_node`)
The AR aging manifest entry (`receivables_araging_20260724_000001`) added
`base_tables: ["receivable"]` but `export_graph_metadata.py` was never re-run,
so the binding node and its `binds_table` edge were missing from
`graph_metadata.json`. The structural fingerprint test expected 88 `binds_table`
edges but the committed JSON had 87.

Fix: bumped `SCHEMA_VERSION = 32`, `MILESTONE_NAME = "ar_aging_binding_node"`,
re-ran the export. Result:

| Metric | Before | After |
|---|---|---|
| binding nodes | 33 | 34 |
| binds_table edges | 87 | 88 |
| column nodes | 331 | 333 |
| total nodes | 446 | 448 |
| total edges | 545 | 547 |

### 3. Structural fingerprint test frozen count updated (331 → 333)
`receivable_payment` table columns added by Task #280 (shipment migration:
`shipped_qty`, `shipped_date`) increased the column node count by 2. The
assertion `check(len(column_nodes) == 331, ...)` needed updating to 333.

### 4. Field descriptions — two missing columns
`customer_order_line.shipped_qty` and `customer_order_line.shipped_date` were
graph column nodes with no entry in `field_descriptions.csv`.  
Added both rows; coverage is now **333/333**. PASS.

### 5. Palette wiring migration registered in bootstrap_db.py
`add_ar_aging_palette_wiring.py` was run post-merge (wiring the AR aging query
to Receivables intent 19, query_index 3) but was not yet in the bootstrap chain.
Added it as the final step so fresh-clone bootstraps include it automatically.

---

## Gates Passing After Fix

| Gate | Result |
|---|---|
| `ledger_events_vocab_check.py` | PASSED |
| `sql_graph_parity_check.py` | OK — 448 nodes / 547 edges |
| `test_structural_fingerprint.py` | 83/83 passed |
| `field_description_coverage_check.py` | 333/333 PASS |
| `test_ar_aging_report.py` | ALL CHECKS PASSED (1 skip expected) |
| `test_gl_posting.py` | 26/26 |
| `test_ledger_bindings.py` | 22 checks PASSED |
| `test_skos_ledger.py` | PASSED |

---

## Design Lesson — New Binding Node Checklist

When a new governed view (snippet) is APPROVED in `reviewer_manifest.json`:
1. Re-run `export_graph_metadata.py` with a bumped `SCHEMA_VERSION` to mint the
   binding node + `binds_table` edges.
2. Update the frozen column count in `test_structural_fingerprint.py` if new
   tables/columns were added by the same task.
3. Add field descriptions for any new graph column nodes before running the
   coverage check.
4. Register the palette wiring migration in `bootstrap_db.py`.

These four steps are ALL required; skipping any one will fail a post-merge gate.
