# MRP Set-Semantics Criteria — 7 Inventory-Planning Concepts

**Status:** SME review draft (Task #237 — definition only)
**Scope:** This document DEFINES the correct set semantics for the seven MRP /
inventory-planning concepts. It changes no code, no manifest, no graph, no
snippets. Authoring and hardening the snippets to match these criteria is the
downstream task (#238).
**Dialect:** SQLite (`manufacturing.db`) — the synthetic ground-truth target.
**Reviewer sign-off:** see the table at the end.

---

## 1. Why this document exists

**All seven concepts are currently `APPROVED` in `reviewer_manifest.json`** (anchors
`AVAILABLETOPROMISE`, `ALLOCATEDQUANTITY`, `SAFETYSTOCK`, `LEADTIMEDEMAND`,
`MINIMUMSTOCKQUANTITY`, `MAXIMUMSTOCKQUANTITY`, `ECONOMICORDERQUANTITY`) — so the
SolderEngine serves all of them today. The problem is not availability; it is that
their **set logic is semantically weak**:

- ATP and AllocatedQuantity aggregate *every* `customer_order_line` row with no
  order-state filter, ATP ignores firm incoming supply, and neither is
  time-phased.
- SafetyStock and LeadTimeDemand carry the same unfiltered-demand defect plus an
  unstable, self-referential planning window (per-part `MAX−MIN(need_by_date)`).
- MaximumStockQuantity and EconomicOrderQuantity average `po_line.quantity` with
  no PO-state filter (Cancelled POs pollute the lot size).

The correct semantics already exist in the codebase — `mrp_engine.py` nets the
right sets over the right horizon. This document lifts those rules into an
SME-reviewable definition so #238 can run a **corrective re-authoring / re-approval
cycle** against a single, agreed standard rather than re-deriving it per concept.

> **Naming note:** the manifest stores concept anchors in UPPERCASE (e.g.
> `AVAILABLETOPROMISE`); this document uses the title-case concept-node names
> (e.g. `AvailableToPromise`). They refer to the same concept.

---

## 2. Canonical foundations every concept must anchor to

These are **not** re-invented per concept. They are the shared, already-proven
conventions from `hf-space-inventory-sqlgen/mrp_engine.py`.

### 2.1 Order / supply state vocabularies (verified against the data)

| Set role | Table.column | Members that qualify | Members excluded |
|---|---|---|---|
| **Live demand** | `customer_order.status` | `Open` | `Closed`, `Shipped`, `Cancelled` |
| **Scheduled receipt (make)** | `work_order.status` | `unreleased`, `firmed`, `released` | `closed` |
| **Scheduled receipt (buy)** | `purchase_order.status` | `Open`, `Partial` | `Closed`, `Received`, `Cancelled` |

`customer_order_line` has **no** status column, so demand-state filtering
**requires** a join `customer_order_line → customer_order` on `order_id`.
Likewise `po_line` has no status; PO-state filtering requires the join
`po_line → purchase_order` on `po_id`.

### 2.2 Time-phasing anchor (data-derived, never wall-clock)

- `AS_OF = MAX(work_order.close_date)` (stable across re-runs), fallback
  `2026-06-12`.
- `PLAN_START = first day of the AS_OF month`.
- Horizon = 6 monthly buckets (M0..M5). Anything before `PLAN_START` folds into
  **Past Due**.
- Any concept whose value depends on *when* demand or supply lands MUST use this
  horizon, not `MIN/MAX(need_by_date)` per part and not `DATE('now')`.

### 2.3 Fail-closed rule

A concept must NOT silently plan against zero. Missing lead time, missing
planning columns, or an unknown part must raise / return an explicit error
(mirroring `compute_mrp_grid`). Because all seven concepts are already approved
and served, #238 must decide whether to **de-approve first** (pull them from the
manifest until re-authored) or **re-author in place** — but either way the
corrected snippets must guarantee these fail-closed inputs before staying
approved.

---

## 3. Modeling-surface recommendation (SQL vs Arango edges)

**All seven concepts should express their set membership and time-phasing in the
SQL snippet, not in the ArangoDB graph.**

Rationale: the semantic graph's job is *routing* — mapping a concept to its
anchor column and perspective (the existing `resolves_to` edges). It cannot
express row-level predicates like "only `Open` orders whose `need_by_date` falls
in bucket M2" or "on-hand plus firm receipts minus committed demand". Those are
**set-arithmetic and state predicates** that belong in the approved SQL, exactly
where `mrp_engine.py` already puts them. The graph stays a navigation layer; the
snippet stays the authoritative definition. This preserves the Solder Pattern
(SME-approved SQL is the source of truth) and keeps `graph_metadata.json`
byte-stable.

Where a concept is a define-once scalar (Min/Max/EOQ), the M4
`computation_template` + `resolves_to` variable-binding pattern is the natural
home *if* it is later promoted to a metric; but that is a #238 authoring choice,
not required by these criteria.

---

## 4. Per-concept criteria

Each concept states: (a) the correct set definition, (b) the defect in the
current snippet, (c) verified columns, (d) time-phasing need, (e) modeling
surface.

### 4.1 AllocatedQuantity

- **Correct set:** the sum of `customer_order_line.order_qty` for a part, over
  **only the lines whose parent order is `Open`** (committed but not yet
  shipped/closed/cancelled). This is the demand already spoken for against
  on-hand stock.
- **Set expression:** `SUM(col.order_qty)` from `customer_order_line col`
  `JOIN customer_order o ON o.order_id = col.order_id`
  `WHERE o.status = 'Open'`, grouped by `part_id`.
- **Current defect:** the approved snippet sums `order_qty` over **all**
  `customer_order_line` rows with no join to `customer_order`, so Cancelled,
  Shipped, and Closed orders are counted as "allocated". The header even claims
  "open customer-order demand" — the SQL does not implement it. `open_order_count`
  is likewise overstated.
- **Verified columns:** `customer_order_line.order_qty`, `.order_id`, `.part_id`,
  `.need_by_date`; `customer_order.status`, `.order_id`; `part.active`.
- **Time-phasing:** optional for the headline number (total open commitment), but
  the **by-bucket** breakdown must use the §2.2 horizon on `need_by_date`.
- **Surface:** pure SQL. No graph change.

### 4.2 AvailableToPromise (ATP)

- **Correct set:** uncommitted supply available to promise =
  `on_hand_qty` **plus** scheduled receipts (non-closed WOs + Open/Partial POs)
  **minus** committed `Open`-order demand — evaluated **time-phased** so ATP in
  each bucket reflects supply and demand up to that bucket. The simplest
  agreed baseline: cumulative `PAB`-style running balance from
  `compute_mrp_grid` (Projected Available Balance is the time-phased ATP).
- **Set expression (headline, non-phased baseline):**
  `on_hand_qty + Σ scheduled_receipts − AllocatedQuantity(Open)`. The phased form
  reuses the netting already in `mrp_engine.compute_mrp_grid`.
- **Current defect:** approved snippet computes `on_hand_qty − SUM(order_qty over
  all lines)`. Three errors: (1) demand set unfiltered (see 4.1); (2) **ignores
  all incoming supply** — firm WOs and open POs that will replenish stock are
  invisible, so ATP is understated for any part with inbound receipts; (3) not
  time-phased — a single scalar cannot answer "available to promise *by when*".
- **Verified columns:** `part.on_hand_qty`, `.active`; demand as in 4.1;
  `work_order.status`, `.required_date`, `.quantity`, `.part_id`;
  `purchase_order.status`, `.required_date`, `po_line.quantity`, `.part_id`.
- **Time-phasing:** **required.** ATP is meaningless without the §2.2 horizon.
- **Surface:** pure SQL, reusing the netting logic already proven in
  `mrp_engine.py`. No graph change.

### 4.3 LeadTimeDemand

- **Correct set:** expected demand over the replenishment lead-time window =
  average daily demand × `lead_time_days`, where **average daily demand is
  derived from `Open`-order demand across the canonical §2.2 horizon** (a fixed,
  shared denominator), not a per-part span of order dates.
- **Current defect:** derives `avg_daily_demand = SUM(order_qty) /
  (MAX(need_by_date) − MIN(need_by_date) + 1)` over **all** order lines. Two
  errors: (1) no `Open` filter (see 4.1); (2) the denominator is a
  **self-referential, unstable window** — a part with one order line gets a
  1-day horizon and an explosively high daily rate; a part with widely spaced
  orders gets a diluted rate. The window must be the fixed planning horizon.
- **Verified columns:** `part.lead_time_days`, `.reorder_point`, `.on_hand_qty`;
  demand as in 4.1.
- **Time-phasing:** the demand rate MUST be computed over the §2.2 horizon.
- **Surface:** pure SQL. No graph change.

### 4.4 SafetyStock

- **Correct set:** buffer inventory absorbing demand/lead-time variability.
  Agreed proxy: `SafetyStock ≈ reorder_point − LeadTimeDemand`, using the
  **corrected** LeadTimeDemand from 4.3.
- **Current defect:** inherits the LeadTimeDemand window/state defects verbatim
  (identical subquery). The proxy formula is acceptable *once its LeadTimeDemand
  input is corrected*.
- **Verified columns:** `part.reorder_point`, `.lead_time_days`, `.on_hand_qty`;
  demand as in 4.1.
- **Time-phasing:** inherited from LeadTimeDemand (§2.2 horizon).
- **Surface:** pure SQL. No graph change.

### 4.5 MinimumStockQuantity

- **Correct set:** in a min/max policy the minimum is the replenishment floor.
  Agreed proxy: `minimum_stock_qty = reorder_point`. This is a **policy proxy**,
  explicitly documented as such (no dedicated min column exists in this ERP).
- **Current defect:** none in the arithmetic — it correctly uses
  `reorder_point`. The only requirement is that the snippet header state plainly
  that this is a documented proxy, and that it carry no false time-phasing.
- **Verified columns:** `part.reorder_point`, `.on_hand_qty`, `.lead_time_days`,
  `.active`.
- **Time-phasing:** none (static policy level).
- **Surface:** pure SQL. Candidate for M4 `computation_template` promotion in
  #238 (optional).

### 4.6 MaximumStockQuantity

- **Correct set:** the replenish-up-to ceiling. Agreed proxy:
  `reorder_point + average replenishment lot`, where the average lot is
  `AVG(po_line.quantity)` **restricted to real POs** — i.e. joined to
  `purchase_order` and excluding `Cancelled` (and arguably restricted to
  `Open`/`Partial`/`Received`/`Closed` settled orders).
- **Current defect:** averages `po_line.quantity` over **all** PO lines with no
  join to `purchase_order`, so Cancelled POs inflate/deflate the lot size.
- **Verified columns:** `part.reorder_point`, `.active`; `po_line.quantity`,
  `.part_id`, `.po_id`; `purchase_order.status`, `.po_id`.
- **Time-phasing:** none (static policy level).
- **Surface:** pure SQL. No graph change.

### 4.7 EconomicOrderQuantity (EOQ)

- **Correct set:** the classic EOQ needs annual demand (D), order cost (S), and
  holding cost (H); **none of D/S/H exist as parameters in this schema**. Agreed
  proxy: the historically settled lot size = `AVG(po_line.quantity)` **restricted
  to real POs** (join `purchase_order`, exclude `Cancelled`), falling back to
  `reorder_point` when a part has no qualifying PO history.
- **Current defect:** averages `po_line.quantity` over **all** PO lines with no
  status filter (same defect as 4.6). The fallback-to-ROP and confidence bands
  are sound.
- **Verified columns:** `part.unit_cost`, `.reorder_point`, `.active`;
  `po_line.quantity`, `.part_id`, `.po_id`; `purchase_order.status`, `.po_id`.
- **Time-phasing:** none (empirical proxy over PO history).
- **Surface:** pure SQL. The header MUST state this is a proxy, not textbook EOQ.

---

## 5. Summary table

| Concept | Time-phased? | State filter needed | Primary defect today | Surface |
|---|---|---|---|---|
| AllocatedQuantity | by-bucket only | `customer_order.status='Open'` | no order-state filter | SQL |
| AvailableToPromise | **yes** | Open demand + non-closed WO + Open/Partial PO | ignores supply, no state filter, not phased | SQL |
| LeadTimeDemand | **yes** (rate) | Open demand | unstable per-part window, no state filter | SQL |
| SafetyStock | inherited | Open demand | inherits LeadTimeDemand defects | SQL |
| MinimumStockQuantity | no | none | acceptable; label as proxy | SQL |
| MaximumStockQuantity | no | exclude Cancelled POs | no PO-state filter | SQL |
| EconomicOrderQuantity | no | exclude Cancelled POs | no PO-state filter; label as proxy | SQL |

---

## 6. What #238 should do (out of scope here)

1. Decide the manifest strategy: de-approve the seven currently-approved snippets
   until corrected, or re-author them in place — but do not leave semantically
   weak SQL approved and served.
2. Re-author all seven snippets to the §2 foundations (state filters, canonical
   horizon, real supply for ATP), guaranteeing the fail-closed inputs before any
   snippet stays/returns to `APPROVED`.
3. Reuse `mrp_engine.py` netting for the phased concepts rather than duplicating
   horizon logic.
4. Keep every definition in SQL; make no graph/`graph_metadata.json` change.

---

## 7. SME sign-off

| Concept | Definition approved? | Reviewer | Date | Notes |
|---|---|---|---|---|
| AllocatedQuantity | ☐ | | | |
| AvailableToPromise | ☐ | | | |
| LeadTimeDemand | ☐ | | | |
| SafetyStock | ☐ | | | |
| MinimumStockQuantity | ☐ | | | |
| MaximumStockQuantity | ☐ | | | |
| EconomicOrderQuantity | ☐ | | | |
