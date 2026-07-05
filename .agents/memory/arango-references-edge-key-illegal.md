---
name: Live Arango references edges never load (illegal key)
description: Why the live `references` edge collection is always empty and how tests treat it
---
The `references_edge_key` format is `fk::CHILD.COL->PARENT.COL`. ArangoDB `_key` forbids `>`, so every live insert fails with `[ERR 1221] illegal document key`. The live `references` collection has therefore always been empty, and `test_solder_graph_catalog.test_references_edges_model_fk_topology` SKIPs on empty — pre-existing, not a regression.

**Why:** discovered while doing a targeted containment sync; a full `graph_sync.py` live run also can't fix it and additionally exceeds the 120s bash cap (run only targeted upserts + `prune_stale_containment` from a small inline script instead).

**How to apply:** don't chase empty `references` in live Arango as a sync bug; if the FK layer is ever needed live, the key format must drop `->` for legal chars (e.g. `..`), which is a deliberate migration, not a re-sync.
