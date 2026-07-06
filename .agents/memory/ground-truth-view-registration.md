---
name: Ground-truth view registration path
description: End-to-end steps to add a new governed SQL view; missing the graph re-freeze fails the fingerprint gate
---

Adding a governed ground-truth view is a four-step chain — stopping after the
manifest entry leaves the repo failing gates:

1. Snippet file in `app_schema/ground_truth/sql_snippets/` named
   `<perspective>_<concept>_<YYYYMMDD>_<seq>.sql` with a header comment.
2. APPROVED entry in `reviewer_manifest.json` (binding_key == filename stem).
3. `migrations/backfill_structural_fingerprints.py` stamps the structural
   fingerprint (never hand-write it).
4. Re-freeze the canonical graph: bump `SCHEMA_VERSION` + `MILESTONE_NAME` in
   `replit_integrations/export_graph_metadata.py` and run it — binding nodes
   and `binds_table` edges are materialized FROM the manifest at export time,
   and `test_structural_fingerprint`'s graph-wiring check counts
   binds_table edges against manifest fingerprints, so a new APPROVED entry
   without a re-export fails that gate.

**Why:** the graph-wiring test failed after steps 1–3 alone; the binding layer
lives only in the frozen graph_metadata, not anywhere boot-time.

**How to apply:** any new/changed APPROVED manifest entry whose base-table set
changes ⇒ re-export with a version bump, then rerun sql_graph_parity and
regenerate committed parity reports. `MRP_VIEW_BINDING_KEYS` in
view_ontology_extractor.py is a separate MRP-only whitelist — most views
(e.g. payables) deliberately stay out of it.

Note: an "orders unreceived/outstanding qty" KPI must clamp per line at zero
(`SUM(MAX(ordered - received, 0))`) — over-received lines must never offset
another line's shortage.
