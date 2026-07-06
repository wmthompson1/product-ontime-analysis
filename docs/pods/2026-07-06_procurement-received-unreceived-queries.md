# Procurement queries: orders received vs. unreceived

*Saved from chat, 2026-07-06. Both queries run read-only against
`hf-space-inventory-sqlgen/app_schema/manufacturing.db` (SQLite).*

## 1. Orders received (every line fully received) — 8 POs

```sql
SELECT po.po_id, po.supplier_id, po.status,
       COUNT(pl.line_id)                    AS lines,
       ROUND(SUM(pl.quantity), 1)           AS qty_ordered,
       ROUND(SUM(COALESCE(r.qty_recv,0)),1) AS qty_received,
       MAX(r.last_receipt)                  AS last_receipt_date
FROM purchase_order po
JOIN po_line pl ON pl.po_id = po.po_id
LEFT JOIN (
    SELECT rl.po_line_id,
           SUM(rl.quantity_received) AS qty_recv,
           MAX(rc.receipt_date)      AS last_receipt
    FROM receiving_line rl
    JOIN receiving rc ON rc.receipt_id = rl.receipt_id
    GROUP BY rl.po_line_id
) r ON r.po_line_id = pl.line_id
WHERE po.status <> 'Cancelled'
GROUP BY po.po_id
HAVING MIN(CASE WHEN COALESCE(r.qty_recv,0) >= pl.quantity THEN 1 ELSE 0 END) = 1
ORDER BY last_receipt_date DESC;
```

Results: PO-000011, PO-STD-001, PO-SVC-001, PO-000005, PO-000012, PO-000015,
PO-000003, PO-000014 — all quantities received in full, most recent receipt
2026-01-04.

## 2. Orders unreceived or short — 14 POs

```sql
SELECT po.po_id, po.supplier_id, po.status, po.required_date,
       COUNT(pl.line_id)                                            AS lines,
       SUM(CASE WHEN COALESCE(r.qty_recv,0) <= 0 THEN 1 ELSE 0 END) AS lines_unreceived,
       SUM(CASE WHEN COALESCE(r.qty_recv,0) > 0
                 AND COALESCE(r.qty_recv,0) < pl.quantity THEN 1 ELSE 0 END) AS lines_short,
       ROUND(SUM(pl.quantity - COALESCE(r.qty_recv,0)), 1)          AS qty_outstanding
FROM purchase_order po
JOIN po_line pl ON pl.po_id = po.po_id
LEFT JOIN (
    SELECT po_line_id, SUM(quantity_received) AS qty_recv
    FROM receiving_line
    GROUP BY po_line_id
) r ON r.po_line_id = pl.line_id
WHERE po.status <> 'Cancelled'
GROUP BY po.po_id
HAVING SUM(CASE WHEN COALESCE(r.qty_recv,0) < pl.quantity THEN 1 ELSE 0 END) > 0
ORDER BY po.required_date;
```

Results highlights:
- **Past due**: PO-000010 (1 line never received, 100 outstanding) and
  PO-000001 (short-shipped 2 units) — the two engineered three-way-match
  exception cases, showing up exactly as designed.
- **Open, nothing received yet**: the three big MRP blanket POs (~5,700 units
  outstanding combined), plus PO-000013, PO-000002, PO-000007, the service
  POs, and the consignment PO.
- **Partially received**: PO-SVC-003 (8 of its service qty still open).

## Data quirk surfaced

**PO-000014 is fully received (90 of 90) but its header still says
"Partial"** — its status was never flipped to Closed. Pre-existing wart, not
touched by the recent migrations (they deliberately never change PO status).
Left in place as a realistic ERP artifact unless repaired later.

## Promoted to ground truth (same day)

Both queries were registered as governed views in the Ground Truth SQL layer:
`payables_ordersreceived_20260706_000001` and
`payables_ordersunreceived_20260706_000002` (perspective **Payables**,
category **delivery_performance**, concept anchors ORDERSRECEIVED /
ORDERSUNRECEIVED). One refinement over the chat version was made during
review: `qty_outstanding` is clamped per line at zero
(`SUM(MAX(ordered - received, 0))`) so an over-received line can never
offset another line's shortage. Gated by
`tests/test_procurement_views.py` in `scripts/post-merge.sh`.

## Design notes

- Coverage is computed line-by-line: a PO counts as "received" only when
  every `po_line` has receipt coverage `>=` its ordered quantity, via
  `receiving_line.po_line_id` (strict line linkage from the three-way match
  chain).
- Cancelled POs are excluded from both views.
- "Unreceived or short" splits lines into `lines_unreceived` (nothing
  received) vs. `lines_short` (partial coverage) and totals
  `qty_outstanding`.
