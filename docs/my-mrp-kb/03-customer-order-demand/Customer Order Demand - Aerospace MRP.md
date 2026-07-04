*Source: written for the local synthetic `manufacturing.db` (SQLite) ERP stand-in, framed against the attached Manufacturing Demand Guide and the real Infor VISUAL T-SQL tables (CUST_ORDER_LINE, DEMAND_SUPPLY_LINK, WORK_ORDER). The real ERP and the guide are reference benchmarks only; every runnable example targets SQLite. The companion grounding query is archived as `manufacturing_customerorderdemand_20260704_000002.sql` under `hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/`.*

# Customer Order Demand — Aerospace MRP

## Page 1. Purpose and scope

This guide explains manufacturing demand from the **Customer Order** point of view, the way a contract analyst, planner, or shop-floor lead would read it. Demand is not one number in one table. It is a small workflow: a customer places an order, the order has one or more lines (a part and a quantity), and those lines create pressure that the plant must satisfy from stock or from production.

The focus is practical. By the end you should be able to start at a customer commitment and trace it toward the manufacturing response: who ordered what, how much is still owed, whether stock can cover it, and where the risk sits.

This document is grounded in the local synthetic database `manufacturing.db`. That database is deliberately **thinner** than a real aerospace ERP. Where a real system (Infor VISUAL) would carry a demand-supply link table, ship-date fields, and per-line shipped quantities, the synthetic model carries only the essentials. Rather than hide those gaps, this guide names each one and maps it to the closest field we actually have (see Page 15 and the "Synthetic vs. real ERP" table). That way the story stays honest and every example below really runs.

---

## Page 2. What manufacturing demand means here

In this model, manufacturing demand means the **quantity** a customer has ordered for a **part**, plus the **status** of that order. The demand lives in two tables:

- `customer_order` — the order header: `order_id`, `customer_name`, `order_date`, `site_id`, and `status` (one of `Open`, `Shipped`, `Closed`, `Cancelled`).
- `customer_order_line` — the order detail: `order_line_id`, `order_id`, `line_no`, `part_id`, `order_qty`, and `unit_price`.

A line becomes operational demand when we ask whether stock can cover it. The synthetic database has 60 orders and 93 order lines, spanning 10 aerospace customers (Boeing, Lockheed Martin, Collins Aerospace, GE Aviation, Raytheon, and others) and 15 distinct parts.

A useful demand guide answers three questions: **what** does the customer want, **how much / when** was it ordered, and **what source** will satisfy it. The first two are answered directly by the two demand tables. The third — the supply source — is where the synthetic model is thinnest, and we will be explicit about that on Pages 7 and 8.

---

## Page 3. Core demand tables in this model

Three tables tell the whole demand story here.

- **`customer_order`** is the commitment. Its `status` field is the single most important demand signal we have, because the synthetic model does not track per-line fulfilment. An order that is `Open` is still owed; `Shipped`/`Closed` are largely satisfied; `Cancelled` is dead demand.
- **`customer_order_line`** is the detail. Each line ties one `part_id` to an `order_qty` and a `unit_price`. The extended **line value** is simply `order_qty * unit_price`.
- **`part`** is the availability anchor. The column `part.on_hand_qty` is the physical stock on the shelf, and `part.part_description` gives the human-readable name. This table is what turns a demand line into an availability question.

The join that stitches demand together is one key: `customer_order_line.order_id = customer_order.order_id`. Everything else (value, availability, running totals) is built on top of that single join. The grounding query file beside this document shows all three views in runnable form.

---

## Page 4. ATP and allocation

The most basic planning relationship is **Available to Promise (ATP)**. In words:

- **On hand** is the total physical stock for a part (`part.on_hand_qty`).
- **Allocated** is the portion already spoken for by confirmed demand.
- **ATP** is what is left to promise to new demand: `ATP = On hand − Allocated`.

In a real aerospace ERP, "allocated" is a stored, maintained number. In the synthetic model there is **no allocated column**, so we **derive** it: allocated equals the sum of `order_qty` on lines whose parent order is still `Open`. That is the honest stand-in — open orders are the demand that has not yet been satisfied, so they are the demand competing for free stock.

This matters because allocated stock is not free even though it physically sits on the shelf. In a make-to-order aerospace shop, allocation is how the system protects a customer commitment from being consumed by a later order. ATP is therefore the bridge between demand and feasibility: positive ATP means the open demand is coverable from stock today; negative ATP means the demand is pushing the plant toward new production, expedites, or a schedule conversation.

Query 2 in the grounding file computes exactly this derivation, part by part.

---

## Page 5. Customer order logic (the demand register)

The operational anchor here is the **demand register**: `customer_order` joined to `customer_order_line`, one row per line, enriched with line value. Query 1 in the grounding file builds it:

```sql
SELECT co.order_id, co.customer_name, co.order_date, co.status AS order_status,
       col.line_no, col.part_id, col.order_qty, col.unit_price,
       ROUND(col.order_qty * col.unit_price, 2) AS line_value
FROM customer_order co
JOIN customer_order_line col ON col.order_id = co.order_id
ORDER BY co.order_id, col.line_no;
```

The key idea is that order lines are not read in isolation. Once you have the register, you can group by status to see committed value, group by part to see demand concentration, or layer availability on top to see coverage. A real ERP report (the Infor VISUAL "Customer Order Master" procedure) does the same thing but adds desired/promised ship dates and work-order-derived status. Our synthetic register has the order date and the order-level status, and we are explicit that the finer date and fulfilment fields are not present (Pages 9–10).

This single register is simultaneously a **demand** view (what was ordered), a **value** view (the line dollars), and a **status** view (where the order sits in its lifecycle).

---

## Page 6. Open quantity and running totals

Demand is not just what was ordered; it is what **remains unfulfilled**. In a real ERP, open quantity = order quantity − shipped quantity, computed per line. The synthetic model has **no per-line shipped quantity**, so we approximate open demand at the **order-status** level: a line counts as open demand when its parent order's `status = 'Open'`.

On that basis, the open demand in the synthetic database is:

| Status | Orders | Lines | Total qty | Total value |
|---|---|---|---|---|
| Shipped | 19 | 42 | 169.0 | $645,522 |
| Closed | 18 | 32 | 126.0 | $478,212 |
| Open | 10 | 19 | 65.0 | $290,038 |

So roughly $290K of committed demand (10 orders, 19 lines) is still open.

The reference guide also stresses the **running total** of demand by part — cumulative pressure rather than line-by-line detail. A single line may look harmless, but several lines on the same part can quietly drain stock. Query 3 in the grounding file walks each part's lines in date order and accumulates `order_qty`, so you can see demand build up over time. This is the synthetic counterpart of the guide's "running total ... by part and date." Note one honest difference: Query 3 accumulates **all** lines (every status) as a total-demand-pressure view, whereas the guide's running total is specifically of *open* quantity. The open-only coverage question is handled separately by the ATP derivation in Query 2; here we order by `order_date` because there is no desired-ship-date column.

---

## Page 7. Demand → supply linkage

This is where the synthetic model is deliberately thinnest, and it is worth being blunt about it. In real Infor VISUAL, the table **`DEMAND_SUPPLY_LINK`** is the relational bridge between a demand line and the supply that satisfies it. It maps a customer order line to a supply record and then joins that supply to a work order, so a planner can see whether a given commitment is backed by a real manufacturing task.

The synthetic database **has no `DEMAND_SUPPLY_LINK` table**. There is no stored row that says "this customer line is satisfied by that work order." That means we cannot reproduce the real linkage join. Instead, the synthetic stand-in for "is this demand satisfiable?" is the **ATP derivation** of Page 4: compare the part's open demand against its on-hand stock. It answers the question at the **part** level (can stock cover the open demand for this part?) rather than the **line-to-work-order** level (which specific job covers this line?).

The honest reading: in this model, demand-to-supply linkage is a stock-coverage check, not a record-to-record bridge. The companion query file states this gap in its header comment so no one mistakes the ATP view for a true demand-supply link.

---

## Page 8. Work orders as the supply response

In a real ERP, work orders are the manufacturing answer to demand. Through `DEMAND_SUPPLY_LINK`, a customer line points to a `WORK_ORDER`, giving the planner a due date, a production status, and proof that the commitment has become a real job.

The synthetic database **does** have a `work_order` table (used by the sibling Shop Floor & Routing guide), but it has **no stored link from a customer order to a work order**. There is no foreign key from `customer_order_line` to `work_order`, and no bridge table between them. So in this model the work-order-as-supply-response relationship is **conceptual, not queryable** from the customer-order side.

What this means in practice: from the demand perspective we can see *that* a part has open demand and *whether* current stock covers it, but we cannot, in the synthetic data, point to the specific job that will replenish it. A real analysis would follow the demand-supply link into the work order to confirm the recovery path. Here, the closest we get is: positive ATP = coverable from stock now; tight or negative ATP = would require a supply response (a work order) that the synthetic model does not yet wire up. We flag this rather than fabricate a link.

---

## Page 9. Shipping and unit-of-measure quantities

The reference guide spends real effort on units of measure: shipped quantity vs. stock shipped quantity, order quantity vs. stock order quantity. The rule there is that a user-facing quantity may be in a conversion unit while stock quantities are in the stocking unit, and mixing them silently corrupts ATP and open-balance math.

The synthetic model is simpler and we should not pretend otherwise. The `part` table has a single `unit_of_measure` (defaulting to `EA`), and `customer_order_line.order_qty` is recorded directly in that unit. There is **no separate stock-UoM vs. user-UoM split**, and there is **no shipped-quantity column** on the line. So in this model:

- There is no unit conversion to get wrong — `order_qty` and `on_hand_qty` are already in the same unit.
- "Shipped" is captured only as the order-level `status = 'Shipped'`, not as a per-line shipped quantity.

The lesson from the real guide still transfers as a caution: when this synthetic model is eventually grounded against real Infor VISUAL data, unit-of-measure conversion becomes a live risk and the single-unit assumption here would have to be revisited.

---

## Page 10. Promise vs. desired ship date

Dates are central to real demand planning. The reference guide describes at least four distinct date concepts — desired ship date, promised ship date, work-order due date, and a WODS desired want date — and a global preference (`MRPByReleaseDate`) that decides whether MRP nets against the promised date or the desired date. Treating those dates as interchangeable is a classic way to get a demand analysis wrong even when the SQL is correct.

The synthetic model has **one date only**: `customer_order.order_date`, the date the order was placed. There is **no desired ship date, no promised ship date, and no release date**. That is a meaningful gap, because it means the synthetic model cannot express *timing* pressure — only *quantity* pressure and order status.

Where the real guide would sort open demand by desired (or promised) ship date to find the most urgent lines, our running-total query (Page 6) sorts by `order_date` as the only available proxy. Any timing-based urgency analysis is therefore out of reach in the synthetic data and would need new columns before it could be modeled. We note the gap rather than invent dates.

---

## Page 11. Status, variance, and risk

Even without ship dates, the synthetic model supports a useful risk read through **status** and **ATP**.

- **Status risk**: the 10 `Open` orders ($290K, 19 lines) are the live exposure — demand still owed. `Cancelled` orders (13 of them) are dead demand and should be excluded from any coverage math. `Shipped`/`Closed` are largely settled.
- **Coverage (ATP) risk**: Query 2 derives ATP for every part with open demand. In the current synthetic data, all 11 such parts have **positive ATP** — open demand is fully coverable from stock — so there are zero shortages right now. The tightest part is `P-10026` (Weldment — Thrust Reverser Link): 8.0 on hand against 5.0 open demand, leaving an ATP of just 3.0.

The real guide pushes "variance-based reading" — late lines, weak work-order matches, ATP vs. projected-on-hand disagreements. The synthetic model cannot compute date variance (no ship dates) or work-order variance (no link), so its risk model is narrower: **status exposure plus stock coverage**. That narrower model is still genuinely useful for spotting which parts are close to the line, and `P-10026` is exactly the kind of part a planner would watch.

---

## Page 12. How to read this model as a process map

The most useful mental model is a short process map, scoped to what the synthetic data actually supports:

1. **Customer order entry** — read the demand register (Query 1): customer, order, line, part, quantity, value.
2. **Allocation** — derive open demand per part (sum of `order_qty` on `Open` orders).
3. **Availability / ATP** — compare open demand against `part.on_hand_qty` (Query 2).
4. **Cumulative pressure** — walk the running total of demand by part over time (Query 3).
5. **Risk read** — combine status exposure with ATP coverage (Page 11).

Notice what is *not* in this map compared to the real ERP: there is no demand-supply-link step and no work-order-status step, because the synthetic model does not carry those records. Reading the model this way keeps the analysis grounded in queries that actually run, while making the missing supply-side steps obvious. That honesty is the point — the map shows both what we can see and where the synthetic data stops.

---

## Page 13. Practical review checklist

When reviewing a customer-order demand scenario in this synthetic model:

1. **Start with status.** Is the order `Open` (live demand), `Shipped`/`Closed` (settled), or `Cancelled` (ignore)? Status is the primary fulfilment signal here.
2. **Read the line.** What `part_id`, what `order_qty`, what `unit_price`? Compute line value (`order_qty * unit_price`) to weigh the commitment.
3. **Check coverage.** For the part, derive open demand and compare it to `on_hand_qty`. Is ATP positive, tight, or negative?
4. **Look at cumulative pressure.** Run the running total for that part — is a series of lines quietly draining stock even though each line looks small?
5. **Name the gaps before deciding.** Remember there is no ship date, no demand-supply link, and no shipped quantity. If the question depends on timing or on a specific work order, the synthetic data cannot answer it — say so rather than guess.

That sequence tells you quickly whether the demand is simply *recorded* or genuinely *coverable* with the data on hand.

---

## Page 14. Common failure patterns

A few ways a demand read goes wrong in this model:

- **False confidence from ATP alone.** Positive ATP means stock currently covers open demand, but it says nothing about timing (no ship dates) or about whether a real work order exists (no link). Tight parts like `P-10026` (ATP 3.0) can flip to a shortage with one more order.
- **Counting cancelled demand.** `Cancelled` orders are dead. Including them in demand or coverage math overstates pressure. Always filter status.
- **Treating order-level status as line-level fulfilment.** Because status lives on the header, a multi-line order is `Open` or `Shipped` as a whole. Do not read it as if individual lines were partially shipped — the synthetic model has no per-line shipped quantity.
- **Assuming a supply link exists.** The biggest trap is reading the ATP coverage view as if it were a true demand-supply link to a work order. It is a part-level stock check, not a record-to-record bridge. The grounding query header says so on purpose.

Every one of these failures comes from forgetting where the synthetic model ends and the real ERP would begin.

---

## Page 15. Summary and synthetic-vs-real mapping

From the customer-order perspective, demand in this model is a clean, runnable chain: a customer commitment (`customer_order`) carries lines (`customer_order_line`) that create quantity pressure on parts, which we test against stock (`part.on_hand_qty`) to derive ATP and cumulative pressure. Status is the fulfilment signal; ATP is the coverage signal. Three queries (register, ATP, running total) make the whole story reproducible.

The synthetic model is intentionally thinner than real Infor VISUAL. The table below maps each real concept to the closest available SQLite field, so the gaps are explicit:

| Real ERP concept (Infor VISUAL) | Synthetic SQLite stand-in | Gap / note |
|---|---|---|
| `CUSTOMER_ORDER` header | `customer_order` | Present (order_id, customer, date, site, status). |
| `CUST_ORDER_LINE` detail | `customer_order_line` | Present (part, order_qty, unit_price). |
| Quantity on hand (`PART`) | `part.on_hand_qty` | Present; the availability anchor. |
| Allocated quantity | *derived* (Σ `order_qty` of `Open` lines) | No stored allocated column. |
| ATP | *derived* (`on_hand_qty − allocated`) | Computed in Query 2, not stored. |
| `DEMAND_SUPPLY_LINK` bridge | *none* | No demand→supply link table; coverage is part-level only. |
| `WORK_ORDER` as supply response | `work_order` exists, **no CO link** | Conceptual only; not queryable from the demand side. |
| Shipped quantity (per line) | *none* (`status='Shipped'` only) | No per-line shipped qty; status is order-level. |
| Desired ship date | *none* | Only `order_date` exists. |
| Promised ship date / `MRPByReleaseDate` | *none* | No ship-date or release-date logic. |
| Stock UoM vs. user UoM | single `part.unit_of_measure` | No conversion; order_qty taken as-is. |

Use this document as the framing reference, and the archived `manufacturing_customerorderdemand_20260704_000002.sql` as the runnable proof.

---

## Appendix. Key terms

- **ATP (Available to Promise):** stock not already committed to open demand; here derived as `on_hand_qty − open demand`.
- **Allocated:** stock reserved for confirmed demand; here derived from `Open` order lines (no stored column).
- **Demand register:** the `customer_order ⋈ customer_order_line` view, one row per line, with line value.
- **Demand-supply link:** the real-ERP bridge from a demand line to its supply record; **absent** in the synthetic model.
- **Open demand:** order lines whose parent order `status = 'Open'`; the live, unfulfilled commitment.
- **Line value:** `order_qty * unit_price`, the extended dollar value of an order line.
- **Running total:** cumulative `order_qty` for a part over time, showing demand pressure building up.
- **Status:** the order-level lifecycle flag — `Open`, `Shipped`, `Closed`, or `Cancelled`.
- **Work order:** the manufacturing job that would satisfy demand; present in the DB but not linked to customer orders here.
