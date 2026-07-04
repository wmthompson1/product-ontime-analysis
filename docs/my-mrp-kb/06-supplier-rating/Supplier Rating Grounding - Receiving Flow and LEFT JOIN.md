# Supplier Rating — Receiving-Flow Grounding & the LEFT JOIN Rule

**Status:** architectural rule (knowledge-loop note for "My MRP")
**Applies to:** `hf-space-inventory-sqlgen/migrations/backfill_supplier_rating_and_wo_actuals.py`

## The rule

Supplier `performance_rating` **must be derived strictly from the material
receiving flow** — never random, never LLM-generated. A supplier's score is its
actual track record in the data:

- **On-time delivery (OTD):** `receiving.receipt_date <= purchase_order.required_date`.
  Rows with no `required_date` are ignored (averaged out), matching the governed
  on-time definition.
- **Quality:** `(Passed + Waived) / (Passed + Waived + Failed)` over graded
  receipts; `Pending` is excluded; neutral `0.75` if nothing is graded yet.
- **Rating:** `clamp(5 * (0.55*OTD + 0.45*quality), 1, 5)`.

## Why the join is LEFT, not INNER

The rating query walks `suppliers → receiving → purchase_order` with a **LEFT
JOIN**. This is a deliberate decision, captured here because it lives only in the
migration's SQL:

- An **INNER** join would silently **drop** any supplier with zero receipts, so
  newly onboarded / no-history suppliers would vanish from the dashboard.
- With a **LEFT** join they still appear and are assigned a **neutral `3.0`**
  ("no track record") rather than being penalized with a low score.

So LEFT-ness here encodes a governance choice — *absence of receipts is not the
same as poor performance.*

## How SPARQL now governs this

The supplier→receiving join and its LEFT-JOIN optionality have been **promoted out
of the migration's hand-coded SQL and into the governed Ontop/SPARQL POC**
(`poc/ontop-ontology-poc/`), so the rule no longer lives only in one migration
script:

- The ontology now models a `:Supplier` class plus `:supplierName` and
  `:performanceRating`, and an object property `:hasDelivery` (Supplier → Delivery).
- **Optionality is governed by the mapping design, not by a query choice.**
  `:Supplier` is minted from the **suppliers** table, so *every* supplier is
  published whether or not it has receipts. `:hasDelivery` is minted **separately**
  from the **receiving** table, so the link exists *only* when a real receipt does.
- A supplier with no receipts therefore stays a first-class node with **no
  `:hasDelivery` edge** — the safe, unlinked state — and its `:performanceRating`
  carries the neutral **3.0** default straight from the data. In SPARQL a consumer
  reads it with `OPTIONAL { ?supplier :hasDelivery ?delivery }`, which Ontop
  compiles to a SQL LEFT JOIN.
- `parity_check.py` proves this: SPARQL and SQL agree on the published and linked
  supplier sets, and an injected no-receipt supplier (into a throwaway snapshot
  only) stays published, stays unlinked, and keeps its 3.0 default.
- `rating_parity_check.py` goes further and republishes the **full** rating: it
  recomputes `clamp(5*(0.55*OTD + 0.45*quality), 1, 5)` per supplier entirely from
  graph triples — `AVG(:opsOnTimeScore)`, `AVG(:qualityScore)`,
  `COUNT(:hasDelivery)` — and proves it equals the stored `performance_rating` for
  every supplier (exit non-zero on any mismatch). `:qualityScore` is mapped from
  `receiving.inspection_status` (1.0 Passed/Waived, 0.0 Failed, no triple for
  Pending), so the same NULL-ignoring averaging that governs on-time also governs
  quality.
- The backfill migration is still **standalone SQLite** and never calls
  Ontop/SPARQL; the POC is a read-only *republishing* of the same governed rule, so
  the two now agree by construction.

> SQLite-backend caveat: Ontop compiles a *multi-triple* `OPTIONAL` whose triples
> span more than one table (and that shape + `GROUP BY`) into SQL the SQLite parser
> rejects, so the simple optionality showcase keeps a **single triple** inside
> `OPTIONAL`. For the rating aggregates `rating_parity_check.py` **lifts** that
> limit by capturing Ontop's generated SQL and re-transpiling the nested join group
> with SQLGlot. The optionality holds regardless, because it is enforced by the
> mapping (entity from the full population table, link from receipts), not by how
> the query is phrased.

## Traceability

- Migration docstring + inline `-- no receipts -> neutral 3.0` comment.
- Commit that introduced the backfill (architect-reviewed; the INNER→LEFT change
  was the review's recommendation).
- This note.
