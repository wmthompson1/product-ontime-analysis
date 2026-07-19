# GL Ground-Truth Views & Perspective Wiring

## What & Why
Give the existing `General_Ledger` perspective real substance: SME-approved ground-truth views over the new GL tables, registered end-to-end so the Query Palette, dispatcher routing, and Ask a Question flow can answer ledger questions with approved SQL — never generated SQL.

## Done looks like
- 4–6 governed views authored in SQLite dialect, e.g.: trial balance (net by account), WIP balance by work order and cost element, journal detail for a work order (parameterized with the approved `(:param IS NULL OR col op :param)` guard idiom where temporal filters apply), received-not-invoiced balance, WIP relief history.
- Each view goes through the full registration checklist: snippet registered (with the v2 join-aware structural fingerprint stamped at registration), manifest entry, fingerprint backfill, and graph re-freeze with SCHEMA_VERSION bump so the binds_table gate passes.
- Views are wired to the General_Ledger perspective (`schema_perspective_concepts` / intent rows and `schema_intent_queries` registration so Selector v1.0 sees them — inserting mid-file must bump displaced query_index rows first).
- Queries appear in the Query Palette, route correctly through the dispatcher, and pass the temporal-parameter contract check.
- All parity and grep gates in `post-merge.sh` pass.

## Out of scope
- Metric concepts with computation templates (separate task).
- New UI tabs.

## Steps
1. **Author the views** — write and manually validate the governed SQL against the bootstrap DB; date filters use the approved passive-guard idiom.
2. **Full registration** — snippet + manifest + fingerprint + intent/query rows + perspective links, following the established new-view checklist.
3. **Re-freeze & verify** — graph re-freeze, then verify palette visibility, dispatcher routing to at least two GL questions, and green gates.

## Relevant files
- `hf-space-inventory-sqlgen/solder_engine.py`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `scripts/post-merge.sh`
