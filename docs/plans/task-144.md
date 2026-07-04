---
title: Plan-008-005: Harden CONTAINS column picker and FOREIGN_KEY self-loop guard
---
# Plan-008-005: CONTAINS Column Picker Hardening

## What & Why
Plan-008 Step 1 assigns the Replit sandbox to prototype the "table→column CONTAINS" layout so the private repo can implement matching DDL and AQL. The Define Relationship form already switches the Target panel to a column list when edge type is CONTAINS, but three gaps remain before the prototype accurately represents the private repo's physical schema mapping model:

1. **`useColumnsByTable` dep-array bug** — the hook's `useEffect` dependency array references `edgeType`, which is not in scope. This is a silent runtime defect (TypeScript error); the effect re-runs incorrectly on first render only. Fix: replace with `[tableName, active]`.

2. **Source-change reset race** — when the user picks a different source table while CONTAINS is active, `selectedTarget` holds the old column's `qualified_name` until the new column list finishes loading. The identity preview and commit payload briefly carry a stale cross-table column key. Fix: clear `selectedTarget` immediately when `sourceShort` changes while in CONTAINS mode.

3. **FOREIGN_KEY self-loop guard** — the structural form has no guard preventing a user from selecting the same table as both source and target with a FOREIGN_KEY predicate (a table cannot have a FK to itself). Fix: disable the "Add to Graph" button and show an inline warning when predicate is FOREIGN_KEY and source table === target table.

4. **Identity preview labeling for CONTAINS** — the structural edge key strip renders `CONTAINS:SRC→TGT` but TGT in column mode is a qualified_name like `production_orders.order_id`, which makes the `targetShort` split-on-space logic display the full dotted string. Update the CONTAINS identity preview to label the target as a column key and add a sub-label showing the private repo's `prefix::TABLE.COLUMN` key format so reviewers can verify naming alignment with task-008-001.

## Done looks like
- Selecting a new source table while CONTAINS is active immediately clears the target selection and shows "Loading columns…" with no stale qualified_name in the identity preview.
- Attempting to commit a FOREIGN_KEY edge where source === target shows an inline amber warning below the predicate definition box and the "Add to Graph" button is disabled.
- The structural identity preview for CONTAINS edges shows the column's `TABLE.COLUMN` qualified_name in the `edge_key` chip and a secondary chip labeled `col_key` showing the `prefix::TABLE.COLUMN` notation as a reference for the private repo adapter.
- `useColumnsByTable` dep array is `[tableName, active]`; no TypeScript errors in the hook file.

## Out of scope
- Any changes to the FastAPI backend or `hf-space-inventory-sqlgen/app.py`.
- Implementing the `prefix::` naming transform in the frontend (that lives in the private repo's `graph_naming_adapters.py`); the UI shows it as a read-only reference label only.
- CONTAINS commit-endpoint validation (backend already receives `qualified_name`; no server-side changes needed for this prototype).
- Any private repo DDL, AQL, or serialization work (tasks 008-001 through 008-004).

## Steps
1. **Fix `useColumnsByTable` dep array** — Replace the erroneous `[tableName, edgeType]` dep array with `[tableName, active]` so the effect re-runs correctly when either `active` or `tableName` changes.

2. **Source-change reset for CONTAINS mode** — Add a `useEffect` in `DefineRelationship` that watches `sourceShort` and clears `selectedTarget` to `""` whenever `isContains` is true, so the stale qualified_name never enters the commit payload or identity preview.

3. **FOREIGN_KEY self-loop guard** — Derive a boolean `isSelfLoop = selectedPredicate === "FOREIGN_KEY" && sourceShort === targetShort`. Render a small amber inline warning inside the "Define Relationship (Edge)" panel when `isSelfLoop` is true, and pass `disabled={isCommitting || isSelfLoop}` to the "Add to Graph" button.

4. **CONTAINS identity preview update** — In the structural identity strip, when `isContains` is true, replace the plain `TGT` token with the full `selectedTarget` (column qualified_name) and add a second read-only chip labeled `col_key` that renders the value prefixed with `nodes::` (representative of the private repo convention from task-008-001) so the format is visible to reviewers without being enforced by the frontend.

## Relevant files
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/DefineRelationship.tsx`
- `artifacts/mockup-sandbox/src/components/mockups/graph-relationship/useColumnsByTable.ts`