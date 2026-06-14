---
name: Parity report & columnar CSV artifacts
description: How/why the SQL parity checkers emit reports + columnar CSVs, the freshness-by-presence rule, and that they are committed (not gitignored).
---

# Parity report & columnar CSV artifacts

The two parity checkers can emit side artifacts (beyond their stdout + exit
code gate):

- `--report-file` → a human-readable `.txt` summary (header, count table,
  diffs, status line).
- `--csv-dir` → columnar, per-record CSVs (one row per node/edge, one column
  per field, rows sorted by `_key`):
  - SQL↔file check writes the **metadata** side (`graph_metadata_*.csv`).
  - SQL↔AQL check writes the **live graph** side (`arango_graph_*.csv`).
  A private-repo routing agent diffs metadata vs live-graph CSVs to confirm the
  metadata can be resynced to / already matches the ArangoDB graph.

## Freshness-by-presence rule (do not break)
The columnar CSVs are **cleared up front** at the start of each check (before
any skip/error early-return). So: **CSV present ⟺ a fresh, successful dump from
this run; CSV absent ⟺ the run skipped/errored** (e.g. ArangoDB unreachable, an
offline-tolerant SKIP that still exits 0).

**Why:** without clearing, a skipped AQL run would leave a *stale*
`arango_graph_*.csv` on disk, and a CSV-only consumer could mistake it for a
fresh confirmation. The `.txt` report says SKIP, but the CSV itself carries no
status marker — so presence is the only honest freshness signal.

**How to apply:** keep the up-front clear; never switch the CSVs to
"always write". If you add a new early-return branch, the up-front clear
already covers it (don't write CSVs on that branch).

## These artifacts are committed, not gitignored
Reversed the earlier "gitignore as runtime artifact" decision: the `.txt`
reports and the CSVs live tracked in `replit_integrations/` so the private repo
can compare them. Tradeoff: `post-merge.sh` rewrites them every run, so expect
churn in the working tree.
