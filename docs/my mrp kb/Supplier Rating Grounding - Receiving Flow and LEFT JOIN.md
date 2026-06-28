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

## Why SPARQL did NOT define this

The Ontop/SPARQL POC (`poc/ontop-ontology-poc/`) is relevant context but is **not**
the source of this join:

- The semantic/SPARQL layer defines the **relationship** `receiving → purchase_order`
  as the object property `:fulfillsPurchaseOrder` (minted from the `receiving.po_id`
  foreign key). It defines *what relates to what*.
- It does **not** define *left-ness*. In SPARQL, inner-vs-outer is a **query-time**
  choice expressed with `OPTIONAL { }`, which Ontop compiles down to a SQL LEFT JOIN.
  The POC's own mapping SQL actually uses an INNER join.
- The POC ontology models only `Delivery` and `PurchaseOrder` — there is **no
  Supplier** class or supplier→receiving relationship in it.
- The backfill migration is **standalone SQLite** and never calls Ontop/SPARQL.

Therefore the supplier→receiving LEFT JOIN and the neutral-3.0 rule exist **only
in the migration's SQL**, which is why they are recorded here.

## Traceability

- Migration docstring + inline `-- no receipts -> neutral 3.0` comment.
- Commit that introduced the backfill (architect-reviewed; the INNER→LEFT change
  was the review's recommendation).
- This note.
