---
name: Pruning two-endpoint edges in graph_sync
description: Why FK/references edges are pruned once over all stale tables, not inside the per-table loop.
---

# Pruning edges that have two table endpoints

`prune_stale_containment` in `hf-space-inventory-sqlgen/graph_sync.py` loops per
stale table to remove that table's column vertices and `contains` edges (those are
genuinely one-table-each). FK `references` edges are different: one edge has TWO
table endpoints (child `table_name` and parent `references_table`), and a single
edge can connect two stale tables in the same prune run.

**Rule:** prune/count any edge type that can span two stale tables ONCE over the
full set of stale names (`FILTER e.table_name IN @names OR e.references_table IN
@names`), not inside the per-table loop.

**Why:** in the LIVE branch a per-table loop is self-correcting (the first pass
REMOVEs the edge, so the second table's pass finds nothing) — but the DRY-RUN
branch only counts (no REMOVE), so the same edge is counted twice (once as child,
once as parent), inflating the reported `references_pruned`. A code reviewer
caught exactly this.

**How to apply:** when adding another two-endpoint edge collection to the prune
path, mirror the references handling — accumulate `result["stale_table_names"]`
during the per-table loop, then do a single `IN @names` query (REMOVE for live,
RETURN 1 for dry-run) after the loop. Don't put two-endpoint edges in the
per-table loop.
