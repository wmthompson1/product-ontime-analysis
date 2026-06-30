---
name: Live flat-graph parity race (shared cloud ArangoDB)
description: Why sql_aql_parity_check is non-deterministic pre-merge for a canonical version bump, and which gate is the real acceptance.
---

The certified live flat graph (`manufacturing_graph_node` / `manufacturing_graph_edge`)
lives on a SHARED cloud ArangoDB instance (`*.arangodb.cloud`). It is concurrently
mutated by processes OUTSIDE your isolated task environment — notably whatever loads
the still-unmerged `main` canonical. During a multi-minute `scripts/post-merge.sh`
run, the live node/edge count can flip between your new version and `main`'s version,
so `replit_integrations/sql_aql_parity_check.py` (the SQL-vs-AQL gate, run LAST) can
sample a clobbered wrong-version state and FAIL — even though running it interactively
right after `load_canonical_to_arango.py` passes cleanly.

**Why:** `app.py` does NOT boot-load the flat graph (`sync_graph` is endpoint-only),
so nothing in your env re-pins it; the only writer in-env is a manual
`load_canonical_to_arango.py`. An external shared-instance process reloads `main`'s
version on its own schedule, racing your load. A version-bump task therefore cannot
deterministically keep the live graph at its new version for a full ~4 min run.

**How to apply:** For a canonical/SCHEMA_VERSION bump, treat
`replit_integrations/sql_graph_parity_check.py` (SQLite `sql_graph_*` ↔ committed
`graph_metadata.json`) as the authoritative, deterministic acceptance — it is fully
under your control and offline. Verify the live-graph gate by loading the canonical
and running `sql_aql_parity_check.py --skip-on-missing` interactively; expect a clean
pass. Do NOT burn cycles re-running the whole post-merge hoping the shared graph stays
pinned. After any clobber, regenerate the committed parity report artifacts
(`sql_graph_parity_report.txt`, `sql_aql_parity_report.txt`, `*_graph_*` columnar CSVs
via `--report-file`/`--csv-dir`) while the live graph is at the correct version so the
committed artifacts reflect the passing state. The gate is `--skip-on-missing` by
design (unreachable = skip), confirming it is meant to tolerate environment variance;
`tests/test_sql_aql_parity.py` proves the parity LOGIC via an injected fake Arango.
