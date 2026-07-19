# Semantic Queries for the Ledger (NLQ Layer)

## What & Why
Make the ledger askable in natural language through the existing Solder Pattern pipeline: SME-approved ground-truth queries for inventory balances, job cost summaries, and event traces — routed deterministically, never LLM-generated SQL.

## Done looks like
- 4–6 governed queries authored in SQLite dialect: inventory balance per bucket (raw materials / WIP / finished goods), job cost summary (by job and cost element), event trace for a job, material issued over a period, finished goods produced over a period — temporal filters use the approved `(:param IS NULL OR col op :param)` guard idiom.
- Each query fully registered: snippet (with the v2 join-aware structural fingerprint stamped at registration), manifest entry, fingerprint backfill, and graph re-freeze with SCHEMA_VERSION bump so the binds_table gate passes.
- Queries wired into perspective/intent rows and `schema_intent_queries` so Selector v1.0 and the Query Palette see them (mid-file inserts must bump displaced query_index rows first); dispatcher routes questions like "Show WIP for job 42" and "what material was issued in July" to the right query.
- Temporal-parameter contract check and all `post-merge.sh` gates pass.

## Out of scope
- SPARQL-side NLQ (SQL path only; SPARQL exposure already handled in the bindings task).
- Flow diagrams (documentation task).

## Steps
1. **Author & validate queries** — governed SQL over the ledger tables, manually validated against the bootstrap DB.
2. **Full registration** — snippet + manifest + fingerprint + intent/query/perspective rows per the established new-view checklist.
3. **Routing verification** — re-freeze, then confirm palette visibility and dispatcher routing for at least three example questions; gates green.

## Relevant files
- `hf-space-inventory-sqlgen/solder_engine.py`
- `scripts/post-merge.sh`
