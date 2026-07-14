# Setting the Grain for a Receivables Query at Invoice Level
## A Customer-Orders Perspective

*Saved from chat, 2026-07-14.*

---

## 1. Why grain comes first

"Grain" is the answer to one question: **what does one row in my result mean?**

Everything else in a query — the joins, the filters, the aggregates, even whether a total is trustworthy — flows from that answer. If you can't finish the sentence *"one row equals one ___"*, you don't have a query yet; you have a join accident waiting to happen.

For receivables from the customer-orders perspective, the candidate grains form a ladder:

| Level | One row equals… | Typical question |
|---|---|---|
| Customer | one customer | "Who owes us the most?" |
| Order | one customer order | "Which orders are unbilled?" |
| **Invoice** | **one AR invoice** | **"What is open, due, and aging?"** |
| Invoice line | one line on an invoice | "Which shipments were billed short?" |
| Application | one cash application event | "How was this payment applied?" |

This document sets the grain at **invoice level** and shows how the customer-order world above it and the line world below it must be handled so the invoice grain stays honest.

The reason invoice grain matters so much in receivables: the invoice is the **unit of collection**. Customers don't pay orders and they don't pay lines — they pay invoices. Due dates, aging buckets, dunning, and DSO all live at the invoice. Pick any other grain and you're aggregating or exploding your way back to it anyway.

---

## 2. The customer-orders side of the mirror

The schema already contains the demand-side spine:

```
customer_order          -- order_id, customer_name, order_date, site_id, status, completed_date
customer_order_line     -- order_line_id, order_id, line_no, part_id, site_id,
                        --   order_qty, unit_price, need_by_date, desired_release_date
```

And on the supplier side the identical problem is already solved:

```
payables       -- invoice_id, po_id, supplier_id, invoice_number, invoice_date,
               --   due_date, amount_dollars, status, payment_date
payable_line   -- payable_line_id, invoice_id, line_no, po_id, part_id, qty, amount,
               --   po_line_id, receipt_line_id
```

The receivables mirror is structurally the same shape with the arrows reversed:

| Payables (built) | Receivables (mirror) |
|---|---|
| purchase_order | customer_order |
| po_line | customer_order_line |
| receiving / receiving_line (goods **in**) | shipment / shipment_line (goods **out**) |
| payables (supplier invoice, header) | AR invoice (customer invoice, header) |
| payable_line → po_line_id, receipt_line_id | AR invoice line → order_line_id, shipment_line_id |
| three-way match: PO ↔ receipt ↔ voucher | three-way match: CO ↔ shipment ↔ invoice |

**Key design lesson carried over from the payables work:** the line table carries *two* provenance keys — one back to the commercial commitment (`order_line_id`, mirroring `po_line_id`) and one back to the physical event (`shipment_line_id`, mirroring `receipt_line_id`). That pair is what makes coverage and exception analysis possible later. An invoice line with a NULL shipment link is the AR twin of the "orphan voucher line," and it must be *visible*, not silently joined away.

---

## 3. Declaring the grain: one row = one AR invoice

The grain declaration for the governed view should be written down, in words, at the top of the SQL — the same way the governed snippets carry a Temporal Parameter Contract:

> **Grain:** one row per AR invoice (`invoice_id`).
> An invoice belongs to exactly one customer. It may bill lines from one or more customer orders. Amounts shown are invoice-header amounts; order and line detail is aggregated up, never fanned out.

Three consequences fall out of that sentence, and each one is a rule enforced in the SQL:

**Rule 1 — everything below the grain must be aggregated before it joins.**
Invoice lines, order lines, and shipment lines are all finer than the invoice. If you join them directly to the header and then `SUM(amount_dollars)`, every line multiplies the header amount. This is the classic **fan-out**, and it's the single most common way receivables totals go wrong.

**Rule 2 — everything above the grain must be single-valued or explicitly listed.**
Customer is safe: one invoice, one customer. Order is *not* safe: one invoice can bill several orders (and one order can be billed across several invoices — it's many-to-many through the lines). So "the order" is not a column at invoice grain; it's either a count, a concatenated list, or a deliberate explosion to a bridge grain (Section 6).

**Rule 3 — the grain key must actually be unique in the result.**
Not assumed — proven. A governed receivables view should be accompanied by a check that `COUNT(*) = COUNT(DISTINCT invoice_id)`.

---

## 4. Building the invoice-grain query safely

The safe pattern is the one the payables spine already uses: **pre-aggregate each finer-grained input in its own CTE to the invoice key, then join the aggregates one-to-one.**

Written in the synthetic dialect (SQLite, mirroring the `payables` shape onto a hypothetical `ar_invoice` / `ar_invoice_line`):

```sql
-- Grain: one row per AR invoice.
WITH line_rollup AS (
    -- collapse invoice lines to invoice grain BEFORE joining
    SELECT il.invoice_id,
           COUNT(*)                             AS line_count,
           SUM(il.amount)                       AS billed_amount,
           COUNT(DISTINCT il.order_id)          AS orders_billed,
           SUM(CASE WHEN il.shipment_line_id IS NULL
                    THEN 1 ELSE 0 END)          AS unshipped_lines
    FROM ar_invoice_line il
    GROUP BY il.invoice_id
),
order_context AS (
    -- order attributes, aggregated to invoice grain
    SELECT il.invoice_id,
           MIN(co.order_date)                   AS earliest_order_date,
           GROUP_CONCAT(DISTINCT co.order_id)   AS order_ids
    FROM ar_invoice_line il
    JOIN customer_order co ON co.order_id = il.order_id
    GROUP BY il.invoice_id
)
SELECT i.invoice_id,
       i.customer_name,
       i.invoice_date,
       i.due_date,
       i.amount_dollars                          AS invoice_amount,
       lr.billed_amount,
       lr.line_count,
       lr.orders_billed,
       lr.unshipped_lines,
       oc.order_ids,
       CASE WHEN i.status = 'Open'
             AND i.due_date < DATE('now') THEN 'Past Due'
            ELSE i.status END                    AS aging_status
FROM ar_invoice i
LEFT JOIN line_rollup   lr ON lr.invoice_id = i.invoice_id
LEFT JOIN order_context oc ON oc.invoice_id = i.invoice_id;
```

What makes this grain-safe:

1. **Every CTE ends at the invoice key.** Each `GROUP BY il.invoice_id` is a written promise that the CTE's output is one row per invoice, so the final joins are 1:1 (or 1:0-or-1 with `LEFT JOIN`).
2. **Header amount vs. rolled-up amount are separate columns.** `invoice_amount` comes from the header; `billed_amount` comes from summing lines. Keeping both visible turns a reconciliation problem into a visible column comparison — the AR twin of the payables header-vs-line drift check.
3. **`LEFT JOIN`, not `INNER`.** An invoice with no lines (a data-quality problem) still appears — with NULL rollups — instead of vanishing. Fail visible, not silent.
4. **The many-to-many with orders is contained.** Orders show up as a count and a list, never as extra rows.

---

## 5. What the customer-orders perspective adds

Seen from customer orders, the invoice-grain view is answering a different underlying question than the finance view. Finance asks "what money is open?" The order desk asks **"how far has each order traveled toward cash?"** The invoice grain serves both, but the customer-orders perspective adds these concerns:

**Billing coverage.** For each order line: `order_qty × unit_price` is the commitment; the sum of linked invoice-line amounts is what's been billed. At invoice grain you surface the symptom (`orders_billed`, `unshipped_lines`); the diagnosis lives one level down at a coverage grain — exactly the role the Three-Way Match Coverage spine plays on the payables side. The AR mirror is: **CO line ↔ shipment line ↔ invoice line**, with quantities `ordered / shipped / invoiced` per order line.

**Unbilled shipments.** Goods that shipped but have no invoice line yet — the mirror of the Uninvoiced Receipts view. Note this population is invisible at invoice grain *by construction*: there's no invoice row for it to hang on. That's not a flaw in the grain; it's a reminder that "receivables at invoice level" and "unbilled revenue" are **two different views with two different grains**, and forcing them into one query is how grain gets corrupted.

**Status semantics.** `customer_order.status` and the invoice's status are independent state machines. An order can be `Closed` with an open invoice (shipped, billed, unpaid), or `Open` with paid invoices (partial billing). Never derive one status from the other inside the invoice-grain view; expose both and let the exception views name the mismatches.

**Temporal anchoring.** Consistent with the MRP convention: aging should be computable against a passed `:as_of_date` parameter (NULL-defaulting to a data-derived anchor), not hard-wired wall-clock, so the view is deterministic and testable.

---

## 6. When you deliberately leave invoice grain

Sometimes the question genuinely needs order and invoice together per row. Then you move to the **bridge grain**: one row per (invoice, order) pair, or per (invoice line ↔ order line) link. The discipline is:

- **Name it.** "One row = one invoice-order pairing" is a legitimate grain — as long as nobody sums `invoice_amount` over it, because the header amount now repeats per order.
- **Mark repeated measures.** Any column repeated across the pairs (header amount, due date) is *descriptive* at this grain, not *additive*. If a total is needed, allocate it (e.g., proportional to each order's share of billed lines) — an explicit business rule, never an implicit join artifact.
- **Keep it a separate governed view.** Don't let a bridge-grain query masquerade as the invoice-level view. In this architecture that means: separate snippet, separate binding key, separate fingerprint.

---

## 7. Guardrails, in the house style

Applying the Solder-Pattern conventions to a future receivables spine:

1. **Grain contract in the header comment** — one sentence, next to the Temporal Parameter Contract.
2. **Fail-closed uniqueness check** — a migration/test asserting no duplicate `invoice_id` in the view output, mirroring the palette-vs-snippet parity gates.
3. **Reconciliation column, not silent trust** — header amount and line rollup side by side; an exceptions view names the drift.
4. **Orphans asserted visible** — invoice lines with no shipment link must exist in fixtures and be provably *excluded* from coverage math and *included* in an exception view (the pattern gated in `test_twm_spine_parity.py`).
5. **Sibling views derive from one spine** — coverage, unbilled shipments, and aging should all read from a single CO↔shipment↔invoice spine so their populations reconcile by construction, the way PRA and Uninvoiced Receipts now derive from the TWM spine.

---

## 8. Summary

- Grain is a declared contract: **one row = one AR invoice**, stated in words and enforced by a uniqueness check.
- Finer-grained detail (lines, shipments, order lines) is **aggregated in CTEs to the invoice key before joining** — never joined raw, or fan-out silently inflates money.
- Coarser or many-to-many context (customer orders) appears as **counts and lists**, never extra rows; when pairs are genuinely needed, that's a separately named bridge grain.
- The customer-orders perspective contributes coverage, unbilled-shipment, and status-mismatch questions — each of which belongs in its **own view at its own grain**, all fed by one spine, mirroring exactly what was built for payables.

The strongest takeaway: this problem has already been solved once. The payables TWM spine *is* a grain-setting exercise — the receivables version is the same architecture with the arrows pointing out the door instead of in.
