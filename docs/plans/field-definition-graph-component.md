# Field definitions in the graph (field_component)

## What & Why
Begin loading **field definitions** into the canonical graph and make a single field
able to carry more than one definition. A field's definition is modeled as the
existing semantic `elevates` edge on its column (perspective + concept + weight); the
SME-meaningful text lives in the already-built `dab_field_definitions` /
`api_field_descriptions` layer (Field Description Pipeline, merged). Today the
multi-meaning case (one column elevated under several perspectives/concepts) is only
implicit. This task makes it explicit and addressable: add a `component_index` column
in SQLite that numbers each definition of a field (1, 2, 3…), and carry that number
into the graph as a `field_component` attribute on the `elevates` edge that increments
when a field has more than one definition.

## Done looks like
- `schema_concept_fields` (the field→definition mapping, source of truth) has a new
  `component_index` column; a field with one definition is `1`, and additional
  definitions of the same field are `2`, `3`, … — set idempotently.
- Field definitions are actually loaded: an idempotent seeder populates real field
  definitions, including at least one field that carries more than one definition, so
  the `field_component` behavior is exercised with live data (not just a fixture).
- Every `elevates` edge in the exported graph carries a `field_component` number
  sourced from `component_index`. A field with N definitions produces N `elevates`
  edges with `field_component` 1..N.
- The exported `graph_metadata.json`, the `sql_graph_edges` table, and the live
  ArangoDB graph all agree on the new attribute — both parity gates (SQL-vs-file and
  SQL-vs-AQL) stay green.
- A new frozen `graph_metadata.v{N}.json` snapshot is written and the live graph is
  re-synced so it reflects `field_component`.
- The post-merge suite stays green, with new coverage for the multi-definition case.

## Out of scope
- Changing the 6-slot composite key grammar. `field_component` is an edge **attribute**
  only — the existing uid slot already disambiguates multiple edges, so the key scheme
  is untouched.
- Re-working the Field Description Pipeline / DAB tab UI (already built). This task may
  *populate* definitions but does not redesign that authoring surface.
- Introducing any new edge **type** or predicate (still only `elevates`; no SUPPRESSES).
- LLM-generated content — definitions are SME/seeded, consistent with the Solder Pattern.

## Steps
1. **Add `component_index` in SQLite.** Add the column to `schema_concept_fields`
   (default 1) and mirror the DDL in both places the app re-creates tables (the schema
   seed file and the app's startup additive-guard block) so fresh and existing DBs both
   get it. Decide deterministic numbering: per `(table_name, field_name)`, the primary
   meaning is 1 and each further definition increments. Keep it idempotent.
2. **Load field definitions.** Extend the existing idempotent elevation/field seeders so
   fields carry real definitions, including at least one field with more than one
   definition (a natural multi-meaning column from the established Perspective Bridge
   pattern). Reuse the name-based `INSERT OR IGNORE` manifest style so re-running is a
   no-op.
3. **Carry `field_component` through the exporter.** Read `component_index` in the
   semantic-elevation fetch, emit it as `field_component` on each built `elevates` edge
   (and give merged SME-authored edges a sensible default), then materialize and
   reconstruct it on round-trip. Add the new `field_component` column to `sql_graph_edges`
   across **all** parity touch-points: the 3 DDL copies (schema seed, app startup guard,
   the sql_graph tables migration), the materialize INSERT, and the edge reconstructor.
4. **Re-freeze and re-sync.** Bump `SCHEMA_VERSION`, re-run the exporter to materialize
   the tables and write the new `graph_metadata.v{N}.json` snapshot, and re-run the
   Arango loader so the live graph carries `field_component`.
5. **Parity + tests.** Keep both parity gates green (SQL-vs-file and SQL-vs-AQL) and
   update the canonical-example fixture. Add tests proving: `component_index` round-trips
   through export→materialize→reconstruct, and a field with multiple definitions yields
   multiple `elevates` edges with distinct, incrementing `field_component` values.

## Architectural constraints
- **SQLite is the source of truth**; the `sql_graph_*` tables exist to mirror and prove
  the graph. `component_index` is authored in SQLite and flows outward — never inferred
  at runtime.
- **Mirror every edge-shape change or parity breaks.** A new edge field must be added to
  the table DDL (3 places), the materialize INSERT, and the `_edge_dict_from_row`
  reconstructor in lockstep, or the SQL-vs-file / SQL-vs-AQL gates fail.
- **Additive, not a key change.** `field_component` is a plain edge attribute; do not
  touch the 6-slot key, the uid allocator, or the node-guard rules. Semantic edges keep
  their invariant that perspective is never the reserved token `system`.
- **Re-export is a deliberate, frozen-once step** — bump the version and freeze a new
  `vN` snapshot rather than mutating an existing one; accept the Arango re-sync cost.

## Relevant files
- `hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql:379-389,790-804`
- `hf-space-inventory-sqlgen/app.py:184-193`
- `hf-space-inventory-sqlgen/migrations/add_sql_graph_tables.py`
- `replit_integrations/export_graph_metadata.py:78-80,545-583,583-630,662-722,833-875,913-940`
- `replit_integrations/seed_elevations.py`
- `replit_integrations/seed_field_descriptions.py`
- `replit_integrations/load_canonical_to_arango.py`
- `replit_integrations/sql_graph_parity_check.py`
- `replit_integrations/sql_aql_parity_check.py`
- `replit_integrations/graph_metadata_canonical_example.json`
- `hf-space-inventory-sqlgen/tests/test_sql_graph_tables.py`
- `hf-space-inventory-sqlgen/tests/test_sql_aql_parity.py`
- `scripts/post-merge.sh`
