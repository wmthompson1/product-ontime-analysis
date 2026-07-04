# Data Masking Tab

## What & Why
Add a "Data Masking" tab to the HF Space Gradio UI that mirrors the existing
"📋 Field Descriptions" tab in form and function, so an SME can declare a
column-level masking policy (which columns are sensitive and how they should be
masked) the same way they author field descriptions today. This closes out the
user's Plan-001-2.

The app already references "masked/hashed physical tables" in the Query Palette,
but there is no surface to author or record *which* columns carry a masking
policy. This tab makes masking a first-class, SQLite-backed overlay — authored
per column, certified by an SME, and published into the DAB stand-in
(`dab_config.json`) — exactly like field descriptions.

Architectural constraints (must follow project conventions):
- **SQLite is the source of truth.** A new masking table holds the policies;
  nothing is inferred at runtime.
- **Create, don't rename.** Add a new table, new helpers, a new tab, and a new
  publish script. Do not modify or rename the existing field-description tables,
  helpers, tab, or sync script.
- **Lowercase canonical naming** for the new table and its columns.
- **Cost-conscious / demo-first.** Masking suggestions are a deterministic
  heuristic (no API spend); there is no AI call on this tab.
- The new table must be registered both in the schema seed file *and* in the
  app's startup "additive guard" table-creation block, because the app
  re-creates/re-seeds tables on every startup.

## Done looks like
- A new tab (e.g. "🔒 Data Masking") appears in the Gradio UI alongside Field
  Descriptions.
- The user picks a table, sees every column with its current masking strategy
  and whether the policy is certified.
- The user can pick a column, choose a masking strategy from a fixed list
  (none / hash / partial / redact), add a short rationale, and Save it — the
  policy persists in SQLite.
- A "Suggest Masking" button proposes a strategy for the selected column from a
  deterministic name/type heuristic (e.g. email, phone, ssn → masked), with no
  API cost; the user reviews and saves it.
- The user can mark a policy "certified," and a "Publish" action flows certified
  masking policies into `dab_config.json` (a `masking` attribute per field),
  reporting how many were published.
- The tab shows coverage: how many columns have a policy / are certified, per
  table and overall — matching the Field Descriptions coverage readout.
- The whole demo masking set can be (re)generated headlessly from one idempotent
  seed script.
- The post-merge test suite stays green, with new tests covering the masking
  table upsert/certify, coverage, and the publish-to-`dab_config.json` flow.

## Out of scope
- The graph export / ArangoDB layer and the `sql_graph_*` tables / parity gates —
  masking is an overlay, not part of the canonical graph, so no graph regen,
  Arango reload, or parity changes (same boundary as field descriptions).
- Actually enforcing masking during query execution or in the SQLMesh
  masked/hashed physical tables — this tab authors and publishes the *policy
  metadata* only; wiring it into the physical layer is separate, larger work.
- AI-generated masking suggestions — the strategy vocabulary is small and a
  deterministic heuristic is sufficient and cheaper.
- Any change to the existing Field Descriptions tab, its tables, helpers, or its
  `dab_config.json` description sync.

## Steps
1. **Masking policy table** — Add a new lowercase SQLite table keyed on the same
   four-part column identity used by the field-description tables
   (source_database, schema_name, table_name, column_name), storing the masking
   strategy (constrained to a fixed vocabulary), a rationale note, a certified
   flag, and an updated timestamp. Register it both in the schema seed file and
   in the app's startup additive-guard table block so fresh and existing
   databases both get it.
2. **Read/write helpers + overlay** — Add get/save helpers for a column's
   masking policy (validating the column exists in the structural schema before
   writing, and upserting idempotently), plus a coverage calculation. Surface the
   masking strategy and certified state on the unified schema so the tab's table
   can display them per column.
3. **Deterministic suggestion** — Add a no-cost heuristic that proposes a masking
   strategy for a column from its name and type (e.g. email / phone / ssn / name
   → masked, ids and dates → none), returning a strategy plus a short rationale
   for the user to review.
4. **Masking tab UI** — Build the new Gradio tab mirroring the Field Descriptions
   tab: entity dropdown with refresh, a per-column table showing strategy and
   certified state, an authoring panel (column picker, strategy dropdown,
   rationale box) with Suggest / Save / Certify / Publish controls, and per-table
   and overall coverage readouts that refresh after each action.
5. **Publish to DAB stand-in** — Add a new idempotent publish script (mirroring
   the field-definition sync) that writes certified masking policies into
   `dab_config.json` as a per-field masking attribute, supports a dry-run mode,
   and is safe to re-run; wire the tab's Publish button to it.
6. **Headless seed** — Add an idempotent seed script that populates a small demo
   set of masking policies for obviously sensitive columns, so the tab is
   populated without manual entry and the flow can be demoed offline.
7. **Tests + CI wiring** — Add tests covering the masking table upsert/certify
   idempotency, coverage, and the publish-into-`dab_config.json` flow, and wire
   them into the post-merge suite so they run with the rest of the gates.

## Relevant files
- `hf-space-inventory-sqlgen/app.py:147-210`
- `hf-space-inventory-sqlgen/app.py:416-477`
- `hf-space-inventory-sqlgen/app.py:480-640`
- `hf-space-inventory-sqlgen/app.py:5251-5326`
- `hf-space-inventory-sqlgen/app.py:5352-5602`
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql:626-671`
- `hf-space-inventory-sqlgen/field_description_pipeline.py`
- `hf-space-inventory-sqlgen/scripts/sync_db_to_dab_config.py`
- `hf-space-inventory-sqlgen/dab_config.json`
- `hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py`
- `hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py`
- `replit_integrations/seed_field_descriptions.py`
- `scripts/post-merge.sh:26-39`
