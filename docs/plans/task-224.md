---
title: Catch missing SQL snippet before a concept appears in the graph but returns empty results
---
# Catch missing SQL snippet before a concept appears in the graph but returns empty results

  ## What & Why
  The SolderEngine silently returns a "no approved snippet" comment block when an elevated concept
  has no manifest entry. There are no automated tests that assert every elevated MRP concept
  (ReorderPoint, LeadTime, OnHandQuantity) resolves to a non-empty SQL snippet. This gap means a
  future schema change or manifest edit could break the MRP query flow without any CI signal.

  ## Done looks like
  - A test asserts that `solder.solder('inventory_planning')` and `solder.solder('inventory_stock_status')`
    return SQL that does NOT start with `--` or `/*` (i.e. is real SQL, not a comment stub)
  - A test asserts that all three manifest entries (REORDERPOINT, ONHANDQUANTITY, LEADTIME)
    resolve to a valid file path and non-empty SQL text

  ## Relevant files
  - `hf-space-inventory-sqlgen/tests/` — add a new `test_mrp_query_palette.py`
  - `hf-space-inventory-sqlgen/solder_engine.py` — `resolve_by_binding_key`
  - `hf-space-inventory-sqlgen/app_schema/ground_truth/reviewer_manifest.json`