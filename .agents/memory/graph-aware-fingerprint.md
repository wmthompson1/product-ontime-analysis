---
name: graph-aware structural fingerprint (v2)
description: Join-edge fingerprint enforcement — the write side and runtime must agree on the v2 extractor, or new snippets silently bypass join validation.
---

# Graph-aware structural fingerprint (v2)

The structural fingerprint validates a snippet against base tables **and** its
canonical join edges. Joins fold into the graph's `references` edge family via an
`origin` (`fk_declared` | `sql_observed`) + `join_type` column pair — NOT a new
edge_type. Canonical edge = endpoints sorted (table, col); INNER for FK-declared.

## The runtime only enforces joins for v2 (join-aware) bindings
`solder_engine.py` runs `validate_join_edges` **only when** the fingerprint's
`extractor == EXTRACTOR_ID_V2` (`join_aware`). Any binding still on the v1
extractor is silently exempt from join drift / graph-recognition enforcement.

**Why:** this is the trap that a code review caught. The runtime was correctly
wired and every existing manifest entry was backfilled to v2, but the *write*
side (`register_snippet.py`) still stamped v1 (`EXTRACTOR_ID`, base_tables only).
So every *newly registered* snippet would bypass join validation — defeating the
hard cutover.

**How to apply:** whenever you touch fingerprint enforcement, treat the write
path and the runtime path as one unit. `register_snippet.py` must emit
`join_edges` + `unresolved_joins` + `extractor=EXTRACTOR_ID_V2`
(`join_edges_from_sql` + `edge_to_dict`). Locked by
`tests/test_register_snippet_v2.py` (in post-merge gate).

## Adding a column to the references edge layer
Adding `origin`/`join_type` (or any new edge column) to the `sql_graph_edges`
export requires updating the `references` edge fixtures in
`tests/test_sql_graph_tables.py` `_sample_graph()` (they assert exact
round-trip/doc equality) or the round-trip test fails.

## Live-Arango parity is pre-existing red (out of scope)
`sql_aql_parity` fails independently: the live ArangoDB graph is on the legacy
`concept_`-prefixed key model and was never synced (documented in replit.md).
`--skip-on-missing` only skips when the graph is *unreachable*; here it is
reachable-but-stale, so it fails. The v22 `origin` field just adds more mismatch
atop an already-red check. All file-vs-SQLite parity + coverage gates are green.
