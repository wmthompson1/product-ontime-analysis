# Pod: PRA view — derived-table join display & the line-19 INNER join

**Date:** 2026-07-08
**Context:** Partial-Receipt Accrual Exposure governed view
(`payables_partialreceiptaccrual_20260708_000004`); Join-relationships display
in the view ontology.

## The `rcv` / `inv` rows in the join table

Those aren't base tables — they're the two derived subqueries (receipt
coverage and voucher coverage), and the join display currently flattens
everything into one table, mixing the outer topology
(`po_line → purchase_order → suppliers`) with the joins *inside* each
subquery (`receiving_line → receiving`, `payable_line → payables`).

The fingerprint layer already knows the difference — it records the
base-to-base joins as validated edges and flags the derived-table joins as
unresolved — so having SQLGlot render the topology in sections (outer query
vs. each subquery scope) is very doable. **Tabled** for now; it's a display
change only, no logic involved.

## Line 19: INNER vs LEFT join

Normally yes, you'd LEFT JOIN receipt coverage so never-received lines still
appear. Here the INNER join is deliberate: the view's own condition requires
`qty_received > 0`, so a line with no receipts can never qualify — a LEFT
JOIN would produce NULL coverage rows that the very next predicate discards.

The asymmetry is meaningful:

- **Receipts are required** for exposure → INNER join.
- **Vouchers are optional** → LEFT join, since "never invoiced" is precisely
  the exposure we want to keep.

If this ever generalizes into a full receipt-status report (including
"nothing received yet" lines), that's when line 19 becomes a LEFT JOIN and
the `> 0` filter moves into a status column.
