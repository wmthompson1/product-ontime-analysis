---
name: Live ArangoDB graph key/edge conventions
description: How the live manufacturing_graph keys tables/columns/edges — differs from the local arangodb_helpers prototype convention.
---

# Live graph vs local helper conventions

The **live** ArangoDB `manufacturing_graph` (the full production ERP graph,
~1,009 tables / ~12,586 columns, mostly `dbo.*` SQL Server) uses a DIFFERENT
key/edge convention than the local `arangodb_helpers` module.

Live format (names preserved verbatim — source case kept, schema prefix kept):
- table vertex `_key` = the **raw table_name**, no `table::` prefix
  - e.g. `dbo.INVENTORY_BALANCE`; `_id` = `tables/dbo.INVENTORY_BALANCE`
- column vertex `_key` = `column::{table_name}.{column_name}`
  - keeps the schema prefix in the table part, e.g. `column::dbo.INVENTORY_BALANCE.POSTING_DATE`
  - `_id` = `columns/column::{table_name}.{column_name}`
- contains edge lives in edge collection **`contains`** (verified live via
  `/_api/gharial`: edge def `contains` from `tables` to `columns`). An earlier
  note here said `manufacturing_graph_edges` — that collection does NOT exist;
  do not use it.
  - `_from`: `tables/{table_name}`, `_to`: `columns/column::{table_name}.{column_name}`
  - fields: `edge_type: "CONTAINS"`, `table_name`, `column_name` — **no `predicate` field**
  - live `_key` is a random hash (not deterministic)

**Live collection inventory** (db `manufacturing_graph`, queried on host `:8529`
— bare host serves the web UI as HTML, so always append `:8529` for the REST/API):
two node-modeling conventions coexist —
- structural trio: `tables`, `columns` (docs) + `contains` (edge tables→columns)
- unified `manufacturing_graph_node` (doc, hex `_xHH_` keys) with UPPERCASE
  node→node edges: `ELEVATES`, `CAN_MEAN`, `MAPS_TO_CONCEPT`, `FOREIGN_KEY`,
  `HAS_COLUMN`, `NEUTRAL`, `OPERATES_WITHIN`, `USES_DEFINITION`, `ATOMIC_FK`
- semantic docs `intents`, `concepts`, `bindings` + lowercase edges `bound_to`
  (intents→bindings), `elevates` (intents→concepts); bridges `Perspective_Intents`,
  `Perspective_Concepts`. Note duplication (uppercase `ELEVATES` vs lowercase
  `elevates`) — multiple generations; user plans to remove old/incorrect structures.

Local prototype (`arangodb_helpers/manufacturing_graph_version_0_0_1.py`):
- `table_key()` → `table::{NAME}` UPPERCASE; `column_key()` → `column::{TABLE}.{COL}` UPPERCASE
- edge collection `contains`
- This is the PROTOTYPE convention only; it does NOT match the live graph.

**Why:** the user confirmed (by sharing live `columns` dump + an edge doc) that
the export under `replit_integrations/export_graph_metadata.py` must mirror the
LIVE graph format, not the local helpers. Preserve source case — the live graph
has uppercase (`EMPLOYEE`), lowercase (`corrective_actions`), and mixed
(`Staging.WODS_Output`) names all kept verbatim.

**How to apply:** when emitting graph parity artifacts, build keys verbatim from
the catalog (no `.upper()`, no `table::` prefix on tables). Only two node types
exist (tables, columns); perspective/intent/concept/weight are semantic-layer
edge properties, never nodes. The local SQLite prototype DB is a tiny subset
(14 tables) and is even missing `EMPLOYEE` columns that the live graph has.
