---
name: Live graph concept-node drift
description: Why post-merge sql_aql_parity fails independent of your changes, and which gate to trust.
---

`scripts/post-merge.sh` runs two graph-parity gates:
- **sql_graph_parity** — SQLite `sql_graph_*` tables vs `graph_metadata.json` (file-vs-file). This is the authoritative check for any snippet/graph change; when it says "296 nodes / 306 edges match" the canonical graph is intact.
- **sql_aql_parity** — SQLite tables vs the **live** ArangoDB graph.

The live ArangoDB graph carries ~103 extra `manufacturing_graph_node_concept_*` nodes (e.g. AllocatedQuantity, AvailableToPromise), so it reports ~399 nodes vs the canonical 296 and sql_aql_parity FAILS.

**Why:** live-graph drift — concept-as-node material was pushed into the live graph but the canonical SQLite/JSON export was not re-frozen to include them (edges still match at 306).

**How to apply:** When a task only edits ground-truth SQL snippet files (no graph_metadata.json / sql_graph_* change), a sql_aql_parity FAIL with the 399-vs-296 concept-node signature is pre-existing environment drift, NOT your regression. Trust sql_graph_parity; use this as a legitimate skip_validation_reason. Do not attempt to "fix" it by editing snippets.
