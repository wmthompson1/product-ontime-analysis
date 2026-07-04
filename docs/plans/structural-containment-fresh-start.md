# Structural Containment Fresh Start

## What & Why
The current semantic layer has two problems that need a clean rebuild:

1. **Intent→Perspective mapping is wrong.** `schema_intent_perspectives` has many intents per perspective (Payables has 4, Receivables has 4, Quality has 2). The invariant is one-and-only-one intent per perspective. The table's unique constraint is on `(intent_id, perspective_id)` but should be `UNIQUE(perspective_id)`. The seed data needs to be wiped and re-seeded correctly.

2. **Perspective mapping needs to be user-designed.** Rather than guessing which intent belongs to which perspective, the correct mapping will be established at the start of this task — then enforced structurally.

"Structural containment" is the organizing principle: each perspective contains exactly one intent, which is the structural anchor for all semantic routing within that perspective.

## Done looks like
- `schema_intent_perspectives` has `UNIQUE(perspective_id)` enforced at the DB level
- Each perspective maps to at most one intent (one-to-one)
- `schema_sqlite.sql` DDL updated to reflect the new constraint
- A migration script wipes and re-seeds `schema_intent_perspectives` with the correct mapping
- ArangoDB `elevates` and `bound_to` edges carry a single `perspective` string (not a list) matching the enforced 1:1 model
- Graph sync runs clean with no warnings
- post-merge.sh stays green

## Out of scope
- Adding new intents or perspectives (existing set only)
- Purchasing / WIP digital twin data (separate task)
- Changing the `contains` edge structure (table→column containment is already correct)

## Steps
1. **Establish the correct mapping** — At the start of this task, the executor must stop and present the full intent list and perspective list to confirm the correct one-to-one mapping before touching any data. Do not proceed past this step without explicit confirmation.
2. **Write migration script** — Wipe `schema_intent_perspectives` rows and re-insert only the confirmed 1:1 rows. Add a `UNIQUE(perspective_id)` constraint via `ALTER TABLE` or DDL replacement.
3. **Update DDL** — Update `schema_sqlite.sql` to reflect the new `UNIQUE(perspective_id)` constraint.
4. **Update graph_sync** — Change the `perspectives` list property on `elevates`/`bound_to` edges to a single scalar `perspective` string (since 1:1 is now enforced). Add a validation check that warns in the sync report if any perspective maps to more than one intent.
5. **Run live sync** — Apply the migration to `manufacturing.db`, run `graph_sync.py` live, verify edges carry the correct single `perspective` value.
6. **Update tests** — Add a test in `test_perspective_deprecation.py` (or a new file) that asserts `UNIQUE(perspective_id)` is present in the schema and that no perspective has more than one intent in the live DB.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql`
- `hf-space-inventory-sqlgen/app_schema/manufacturing.db`
- `hf-space-inventory-sqlgen/graph_sync.py`
- `hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py`
- `hf-space-inventory-sqlgen/solder_engine.py`
