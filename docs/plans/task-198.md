---
title: Full supplier-rating parity (SQLGlot OPTIONAL/aggregate lift)
---
# Full Supplier-Rating Parity

## What & Why
Today the POC proves parity only for the on-time *sub-part* of the supplier
story. The full deterministic "My MRP" rating —
`clamp(5 * (0.55*OTD + 0.45*quality), 1, 5)`, where quality =
(Passed+Waived)/(Passed+Waived+Failed) over graded receipts with a neutral 0.75,
and a no-receipt supplier gets a neutral 3.0 — still lives only in the backfill
migration. Republish the whole rating through the virtual graph and prove the
SPARQL-computed rating matches the migration's stored `performance_rating` for
every supplier.

Computing a per-supplier rating needs aggregation (GROUP BY) combined with the
optional supplier→receiving link (LEFT JOIN) in one query — exactly the
`OPTIONAL` + `GROUP BY` shape Ontop serializes into SQL that SQLite rejects. So
this task also revisits the previously-tabled idea: capture Ontop's generated
SQL and re-transpile the SQLite-incompatible constructs with SQLGlot (already in
the stack) into SQLite-valid SQL, lifting the single-triple-`OPTIONAL` /
`OPTIONAL`+aggregate limit. The full-rating query is the driving example that
proves the lift works.

## Done looks like
- The ontology/mapping expose the rating's building blocks (each receipt's
  on-time outcome and its inspection grade, each supplier's stored rating) so the
  full rating is derivable through the graph, not just read back from the stored
  column.
- A query that previously failed on SQLite (a multi-triple `OPTIONAL`, and an
  `OPTIONAL` + `GROUP BY` aggregate) now runs to completion through the
  SQLGlot-rewritten SQL path.
- The per-supplier rating computed via the graph equals the migration's stored
  `performance_rating` for every supplier, to rounding tolerance — including
  no-receipt suppliers landing on the neutral 3.0.
- The parity proof runs read-only against a snapshot and exits non-zero on any
  mismatch.
- README documents the lifted limit and that the full rating (not just on-time)
  is now proven at parity; the supplier-rating grounding note and memory are
  updated to match.

## Out of scope
- Changing the backfill migration or the live rating values (read-only
  republishing only).
- Lifting every conceivable SQLite limitation — only the constructs the
  full-rating query needs.
- Wiring any of this into the Flask/HF Space app, Gradio, ArangoDB, or
  SolderEngine.

## Steps
1. **Model the rating inputs** — Extend the ontology + mapping so each receipt
   carries its on-time outcome and its inspection grade, and each supplier
   carries its stored rating, keeping the governed single-source mapping shape
   (entity from the full population table, link from the fact table).
2. **Capture Ontop's SQL** — Drive Ontop so the SQL it generates for the richer
   query can be captured rather than executed directly.
3. **Transpile with SQLGlot** — Rewrite the SQLite-incompatible constructs
   (nested LEFT JOIN from multi-triple OPTIONAL, OPTIONAL+GROUP BY) into
   SQLite-valid SQL and run that against the snapshot. If clean interception
   proves infeasible, fall back to aggregating Ontop's SQLite-safe per-receipt
   triples and record the blocker — the rating parity proof must still be
   delivered either way.
4. **Prove full-rating parity** — Compute the rating through the graph path and
   assert it equals the migration's stored `performance_rating` per supplier (and
   the no-receipt neutral default), to tolerance, read-only against a snapshot.
5. **Docs + memory** — Update the README, the supplier-rating grounding note, and
   memory to reflect the lifted limit and the full-rating parity proof.

## Relevant files
- `poc/ontop-ontology-poc/mapping/on_time_delivery.obda`
- `poc/ontop-ontology-poc/ontology/on_time_delivery.ttl`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/queries/suppliers_optional_deliveries.rq`
- `poc/ontop-ontology-poc/README.md:104-116,199-210`
- `hf-space-inventory-sqlgen/migrations/backfill_supplier_rating_and_wo_actuals.py:60-115`
- `docs/my-mrp-kb/Supplier Rating Grounding - Receiving Flow and LEFT JOIN.md`
- `.agents/memory/ontop-interoperability-poc.md`