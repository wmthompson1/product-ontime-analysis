---
name: dab_config.json is generated, not hand-edited
description: How certified field definitions flow into dab_config.json and why publish must auto-create entity blocks.
---

# dab_config.json is a generated artifact

`dab_config.json` is fully regenerated from the SQLite `dab_field_definitions`
table (rows with `certified=1`) by `sync_db_to_dab_config.py`. The file carries a
"Do not hand-edit" note for this reason.

**Key gap:** `dab_config.json` historically shipped with only demo/legacy CRM
entities (Customer, Sales, …), but the real ERP source tables are the
manufacturing tables (`work_order`, `purchase_order`, …). So a certified
manufacturing field has no matching entity to update.

**Decision:** `sync()` defaults to `create_missing=True` — when a certified row's
table/field is absent from the config, it auto-creates the entity block (keyed by
the raw table name, `source = "<schema>.<table>"`) and the field. This makes the
"Publish to DAB" action in the Field Descriptions tab actually populate the DAB
stand-in. Pass `--no-create` (or `create_missing=False`) to restrict to
update-only.

**Why:** without auto-create, publishing the manufacturing data dictionary would
report "0 updated, N not matched" and look broken.

**How to apply:** the auto-create path is idempotent (the entity index is updated
in-loop, so re-runs find the created entity). Any new test that feeds certified
rows for tables not present in the config must expect entity creation unless it
explicitly passes `create_missing=False`.
