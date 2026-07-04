# Add Plan-008 To Plans Folder

## What & Why
The live `hf-space-inventory-sqlgen/plans/` folder holds plan-011 and plan-012, each as a pair (a plan yaml + a `-tasks.yaml` work board), but **plan-008 is missing** — it exists only as older `attached_assets/` snapshots and as a standalone implementation-notes markdown. Recreate plan-008 in the live folder as a matching pair so the plan history is complete and the latest detail is captured in one place.

The content should be built from the attached `plan-008-implementation-notes` markdown (the `graph_metadata_demo.py` invocation/config and the full `replit_integrations/` module file inventory) layered on top of the existing plan-008 snapshot yamls. The plan should also record the context that plan-008's graph-metadata changes exist to support importing the polymorphic special-case table `USER_DEF_FIELDS` (which has unique graph-metadata structures), and that the broader graph-building POC planning was moved forward to plan-009.

This is a documentation/archival task only — it adds two yaml files and changes no executable code.

## Done looks like
- A new plan yaml exists at `hf-space-inventory-sqlgen/plans/plan-008-consumer-delivery-persistence.yaml`, following the exact key structure used by plan-011/012 (`plan_id`, `title`, `topic`, `created`, `status`, `assigned_to`, `objective`, `steps`).
  - `plan_id` and `title` preserve the snapshot values (`plan-008-consumer-delivery-persistence`; "Plan-008: Local Graph Metadata Parity Smoke-Test").
  - The objective/steps fold in the attached implementation notes: how `graph_metadata_demo.py` is invoked, the `MANUFACTURING_DB` env-var config, the read-only parity-smoke-test behavior, and the Supplier_Analysis semantic-triple benchmark.
- A new tasks work board exists at `hf-space-inventory-sqlgen/plans/plan-008-tasks.yaml`, following the structure used by plan-011-tasks/plan-012-tasks (`plan_id`, `status`, `tasks:` list with `task_id`, `title`, `status`, `assigned_to`, `wave`, `dependencies`, `artifact`, `notes`).
  - The task list carries over the waves from the plan-008 tasks snapshot (Wave 1 persistence/adapters, Wave 2 graph conversion, Wave 3 replit graph metadata integration, Wave 4 schema lock) with their recorded statuses (e.g., the Wave 3 demo/validation tasks marked completed).
  - The `notes` for the replit-integration tasks reflect the file inventory from the attached notes (`graph_metadata_queries.py`, `metadata_query_templates.py`, `graph_metadata_demo.py`, `export_graph_metadata.py`, `load_canonical_to_arango.py`, `seed_field_descriptions.py`, and the `graph_triples.tsv` / `graph_metadata.json` / `graph_metadata.v{N}.json` / canonical-example outputs).
- Both files are valid yaml and visually match the formatting conventions of the existing plan-011/012 pair.
- The plan captures the `USER_DEF_FIELDS` polymorphic special-case context and the note that POC planning moved to plan-009.

## Out of scope
- No changes to any executable code in `replit_integrations/` or to `graph_metadata_demo.py`.
- No changes to the plan-009 / plan-011 / plan-012 yaml files.
- Not implementing or modifying the `USER_DEF_FIELDS` import itself — only documenting it as context in the plan.
- Not running the parity smoke-test.
- No edits to the original `attached_assets/` snapshots (they are read-only source material).

## Steps
1. **Create the plan-008 plan yaml** — Write `hf-space-inventory-sqlgen/plans/plan-008-consumer-delivery-persistence.yaml` mirroring the plan-011/012 plan-file format. Carry over `plan_id`, `title`, `objective`, and `steps` from the plan-008 snapshot, and enrich the objective/steps with the invocation, `MANUFACTURING_DB` config, read-only constraint, and Supplier_Analysis semantic-triple benchmark from the attached implementation notes. Add `topic`, `created`, `status`, and `assigned_to` keys to match the live format.

2. **Create the plan-008 tasks work board** — Write `hf-space-inventory-sqlgen/plans/plan-008-tasks.yaml` mirroring the plan-011-tasks/plan-012-tasks format. Carry over the wave/task structure and statuses from the plan-008 tasks snapshot, and update each task's `notes` to reflect the `replit_integrations/` file inventory described in the attached notes.

3. **Record the USER_DEF_FIELDS / plan-009 context** — In the plan yaml's objective or a dedicated note, capture that plan-008's graph-metadata changes support importing the polymorphic `USER_DEF_FIELDS` special-case table (unique graph-metadata structures) and that the graph-building POC planning was advanced to plan-009.

4. **Verify parity with the existing pair** — Confirm both new files parse as valid yaml and use the same key names, ordering, and indentation conventions as the plan-011/012 pair.

## Relevant files
- `hf-space-inventory-sqlgen/plans/plan-011-fk-hierarchy-approval.yaml`
- `hf-space-inventory-sqlgen/plans/plan-011-tasks.yaml`
- `hf-space-inventory-sqlgen/plans/plan-012-dual-layer-delineation.yaml`
- `hf-space-inventory-sqlgen/plans/plan-012-tasks.yaml`
- `attached_assets/plan-008-implementation-notes_1781209677599.md`
- `attached_assets/plan_1780695754056.yaml`
- `attached_assets/tasks_1780695778650.yaml`
- `replit_integrations/graph_metadata_demo.py`
- `replit_integrations/metadata_query_templates.py`
- `replit_integrations/graph_metadata_queries.py`
- `replit_integrations/plan-8-wave-4-synthetic-erp-expansion.md`
