# MRP & Inventory — Knowledge Base and Revised Proposal

> **Status:** DRAFT v1 — a reference document (no code or schema changes).
> **Purpose:** Formalize manufacturing resource planning (MRP) and inventory
> concepts so an SME can read this and know *exactly what to build* in the
> semantic graph.
> **Two hard rules (read first):**
> 1. **Column-anchored** — a graph **concept must point to a real ERP column**
>    an SME can put their finger on.
> 2. **Operationally recognizable** — a concept must be a thing an SME
>    *recognizes from doing the work* (the words used on the job), **not an
>    abstract category**. If a materials manager wouldn't say it on the floor,
>    it isn't a concept.
>
> If something is only a formula, it is a **derived metric** and it does **not**
> become a graph concept — it lives in SME-approved SQL. SQL is never
> machine-generated (Solder Pattern).

> **⚠ Open decision — measures vs. categories.** The existing `elevates` edge
> elevates only **bounded categorical discriminators** (status / type / class /
> location) — explicitly *not* continuous measures or IDs (curation rule in
> `seed_elevations.py`). Most MRP terms here (reorder point, lead time, on-hand,
> EOQ) are **numbers, not categories**, so they do **not** fit today's `elevates`
> as-is. **Recommended resolution (§8):** admit *canonical named measures*
> (`concept_type = metric`) into `elevates`; pure formulas still stay in SQL.

This document does two things:
1. **Revises the proposed topology** so it fits the graph we already froze at
   `SCHEMA_VERSION = 14`.
2. Starts the **inventory concept knowledge base** — concrete, column-anchored
   concept cards an SME can author today.

---

## 1. What already exists today (v14 — facts, not proposals)

The graph already has three kinds of nodes and three kinds of edges. Nothing
below needs to be invented:

| Node type | Count | Example |
|---|---|---|
| `table` | 23 | `part`, `purchase_order`, `work_order` |
| `column` | 223 | `part:reorder_point`, `part:on_hand_qty` |
| `concept` | 33 | `QuantityBasisEngineering`, `StockMovementDirection` |

| Edge type | Count | Meaning |
|---|---|---|
| `has_column` | 223 | table → its columns (structural) |
| `references` | 39 | column → column foreign key (structural) |
| `elevates` | 17 | **column → concept** (semantic) — *this is the important one* |

**Edges already carry meaning.** Each edge has an `edge_type` and an
`edge_family`. (The `predicate: none` you saw is a *node* field, not the edge's
meaning.)

**The `elevates` edge is already the "column maps to concept" triple.** A real
one in the graph today:

```
part:on_hand_qty  --elevates { perspective: "Inventory_Transactions", weight: 1 }-->  OnHandQuantity (concept)
```
(shape, verified live: `customer_order_line:order_qty --elevates {perspective:"Engineering"}--> QuantityBasisEngineering`)

So the perspective **already lives on the edge**, not on the concept. That is on
purpose: the *same* concept can be elevated from several perspectives.

---

## 2. Your proposal, revised

Your proposed topology:

```
[Column/MIN_STOCK_QTY] --[MAPS_TO {perspective:"Inventory"}]--> [Concept/SafetyStock]
```

Revised to fit v14 (three small changes, same spirit):

```
part.reorder_point --[elevates {perspective:"Inventory_Transactions", weight:1}]--> ReorderPoint
```

| Your wording | Revised | Why |
|---|---|---|
| `MAPS_TO` | **`elevates`** (keep `MAPS_TO` as a plain-English alias) | `elevates` already exists and means exactly this. A second predicate would duplicate everything (exporter, DDL, parity, tests, live load). |
| `perspective: "Inventory"` | **`perspective: "Inventory_Transactions"`** for now | That is the perspective's real name today. Renaming it to `Inventory` is a good idea but is a **future schema step** (see §5), not a doc edit. |
| `Concept/SafetyStock` | `ReorderPoint` (real column) — keep `SafetyStock` for when a safety-stock column exists | `part.reorder_point` is a real column an SME can point to. There is no `safety_stock` / `MIN_STOCK_QTY` column in this schema yet (it exists in the private repo). |
| "concepts are subsets of perspectives" | concepts get a **`category`** (and stay reusable) | See §3 — this keeps a concept usable from more than one perspective. |

---

## 3. "Concepts as subsets of perspectives" — the careful version

The intent is good: group concepts so people can find them ("show me all the
Inventory concepts"). But we should **not** stamp a single perspective onto a
concept node, because a concept like `LeadTime` is used by *Inventory*,
*Procurement*, and *Manufacturing* at once.

Revised model:
- The **routing perspective stays on the `elevates` edge** (unchanged).
- Each **concept gets a `category`** (e.g. `Inventory`, `Procurement`,
  `Quality`) — a label for grouping and filtering only. This is the planned
  **M3 concept metadata** step (category / definition / synonyms), and it does
  **not** break the rule that a concept is reusable.

So "subset of a perspective" becomes "tagged with a category." Same browsing
benefit, no loss of reuse.

> **Important:** a `category` is only a *label on a concrete concept*. The
> category itself is never a concept. Concepts stay operationally recognizable
> (rule 2); categories are just how we file them.

---

## 4. The inventory concept knowledge base (buildable now)

Every concept below passes **both** hard rules: it is anchored to a **real,
verified column** *and* it is a term an SME would recognize on the job. An SME
can author each one as a single `elevates` triple.

**SME litmus test for any new concept:**
1. Can you point to the exact column it comes from? *(no → it's a derived metric, not a concept)*
2. Would you use this exact word describing your actual work? *(no → rename it to the word you do use, or drop it)*

> **⚠ Provisional.** The measure-based cards below (`OnHandQuantity`,
> `ReorderPoint`, `LeadTime`, `ReceivedQuantity`, `OrderedQuantity`, …) are
> column-anchored and recognizable, but they map to **numeric measure** columns,
> which today's categorical-only `elevates` rule excludes. They become buildable
> only after the "measures vs. categories" decision (§8 — **now recommended:
> admit canonical named measures**, so these become buildable). `StandardQuantity`
> / `ActualQuantity` are the exception: they already exist as the *categorical
> lens* concepts `QuantityBasisEngineering` / `QuantityBasisManufacturing`.

### Concept card template (what an SME fills in)
- **Concept name** — concrete noun (`OnHandQuantity`, not `Quantity`)
- **Everyday meaning** — one plain sentence
- **Category** — Inventory / Procurement / etc.
- **Perspective(s)** — which perspective the elevation is authored under
- **Source column(s)** — `table.column` that *already exists*
- **The triple** — `table.column --elevates {perspective}--> Concept`
- **SME notes / questions**

### Buildable inventory concepts

| Concept | Everyday meaning | Source column (real) | Perspective |
|---|---|---|---|
| `OnHandQuantity` | How much we physically have right now | `part.on_hand_qty` | Inventory_Transactions |
| `ReorderPoint` | Stock level that triggers a new order | `part.reorder_point` | Inventory_Transactions |
| `LeadTime` | Days from ordering to receiving | `part.lead_time_days`, `purchase_order.lead_time_days` | Inventory_Transactions / Payables |
| `ReceivedQuantity` | How much actually arrived | `receiving.quantity_received` | Inventory_Transactions |
| `OrderedQuantity` | How much we asked for | `receiving.quantity_ordered`, `po_line.quantity` | Inventory_Transactions / Payables |
| `StandardQuantity` | As-designed per-unit quantity (engineering) | `requirement.std_qty` | Engineering |
| `ActualQuantity` | As-built consumed quantity (shop floor) | `requirement.actual_qty` | Manufacturing |

Example the SME authors:
```
part.on_hand_qty   --elevates {perspective:"Inventory_Transactions"}--> OnHandQuantity
part.reorder_point --elevates {perspective:"Inventory_Transactions"}--> ReorderPoint
part.lead_time_days--elevates {perspective:"Inventory_Transactions"}--> LeadTime
```

These join the inventory concepts the graph **already** has:
`StockMovementDirection`, `WarehouseLocation`, `PartSourcingClass`,
`WorkOrderLifecycleState`, `PurchaseOrderLifecycleState`,
`ReceivingInspectionState`.

---

## 5. Derived metrics — vocabulary only, **not** graph concepts

These are real MRP ideas, but they are **calculations over columns**, not a
single column. By our hard rule they are **not** concepts; they belong in
SME-approved SQL snippets. They are listed here so everyone shares the words.

| Term | Plain meaning | Typical formula (confirm policy with SME) |
|---|---|---|
| Safety Stock | Buffer to cover demand swings during lead time | enough to cover demand variability over `lead_time_days` |
| Reorder Point (calc) | When to reorder | `(avg daily demand × lead_time_days) + safety stock` |
| Economic Order Qty (EOQ) | Cheapest order size | `sqrt( (2 × annual demand × order cost) / holding cost )` |
| Available-to-Promise | What we can still promise | `on_hand_qty − allocated` (+ scheduled receipts) — **needs an allocation source** |
| Gross / Net Requirement | Total vs net-of-stock demand | `net = gross − on_hand − scheduled receipts + safety stock` |
| ABC Class | Rank items by value | classify by cumulative value (A ≈ top 80%) |

> If the business later wants any of these to be a *first-class* concept, the
> right move is usually to **add a real column** that stores it (so an SME can
> point to it), then elevate that column — not to elevate an abstraction.

---

## 6. What is doc-only vs. a future schema change

| Item | Status |
|---|---|
| This knowledge base / concept cards | **Doc only** — safe now |
| Authoring `elevates` triples for the §4 concepts | SME data entry (no schema change) |
| `category` / definition / synonyms on concepts | **M3** — a future schema-version bump |
| Rename `Inventory_Transactions` → `Inventory` | **Future (v15)** — touches seeds, generated JSON, stable keys, live load; do as one approved migration |
| New `MAPS_TO` predicate | **Not recommended** — reuse `elevates` |

---

## 7. Open questions for the SME
1. Is `part.reorder_point` the agreed trigger level, or should reorder point be
   *calculated* (and only safety stock stored)?
2. Do we have (or need) a stored **safety stock** column? (Private repo has
   `MIN_STOCK_QTY`.)
3. Where does **allocated / reserved** quantity live? Without it,
   Available-to-Promise stays a derived metric we cannot anchor.
4. Should `LeadTime` be one concept used by several perspectives, or separate
   per perspective? (Recommendation: one concept, many perspectives.)
5. Confirm the unit of measure rules before comparing quantities across tables.
6. A few **existing** concept names lean abstract (e.g. `QuantityBasisEngineering`,
   `RequirementBasisManufacturing`). Do they pass rule 2 (operationally
   recognizable), or should a future version rename them to shop-floor language?

---

## 8. Decision & M3 build plan (measures join the graph)

### 8.1 Decision — recommended (pending your OK)
**Extend the `elevates` curation rule** from "bounded categorical discriminator
only" to:

> A column may elevate to a concept if it is **either** a bounded categorical
> discriminator (status / type / class / location) **or** a *canonical named
> measure* (a real, stored business quantity like reorder point or lead time)
> with `concept_type = 'metric'`.

- **Why this, not a new edge:** `elevates` already means "column → business
  concept," `concept_type = 'metric'` already exists, and the existing
  `QuantityBasisEngineering` / `…Manufacturing` metric concepts already elevate
  from a quantity column. A second predicate would duplicate the exporter, DDL,
  parity gates, tests, and live load for no semantic gain.
- **Formulas stay out.** EOQ, available-to-promise, and safety-stock math remain
  **derived metrics** in SME-approved SQL (§5). Only *stored* measures elevate.
- **Safety Stock is excluded** — no safety-stock column exists here, so it fails
  rule 1 (column-anchored). It stays in the §5 glossary until a real column is
  onboarded.

### 8.2 First MRP concept batch (the M3 payload)
Each concept carries a plain-English definition + synonyms (the new M3 fields)
and a single `elevates` triple. Perspectives use the real names
(`Inventory_Transactions`, `Manufacturing`).

| Concept | Type | Domain | Source column | Perspective | Synonyms |
|---|---|---|---|---|---|
| `ReorderPoint` | metric | inventory | `part.reorder_point` | Inventory_Transactions | ROP, reorder level, replenishment trigger |
| `PartLeadTime` | metric | inventory | `part.lead_time_days` | Inventory_Transactions | lead time, planning lead time, days to replenish |
| `OnHandQuantity` | metric | inventory | `part.on_hand_qty` | Inventory_Transactions | on hand, stock on hand, available stock |
| `RequiredMaterialQuantity` *(optional 4th)* | metric | manufacturing | `requirement.std_qty` | Manufacturing *(or Engineering?)* | required qty, standard requirement, planned material need |

> **Two choices for you:** (a) ship the **3 clean `part.*` inventory measures**,
> or **add the 4th** (`RequiredMaterialQuantity`)? (b) if added, `std_qty` is the
> *as-designed standard* quantity — perspective **Manufacturing** or
> **Engineering**? (It may also overlap with the existing
> `QuantityBasisEngineering`.)

Example triple authored in `seed_elevations.py`:
```
("Inventory_Transactions", "ReorderPoint", "part", "reorder_point", 3,
 "Stock level that triggers replenishment")
```

### 8.3 Build sequence (one v15 bump)
1. **Docs** — record this decision here + in the spec's M3 section / decision log.
2. **DDL (additive guards)** — add `synonyms`, `tags` (TEXT, canonical JSON
   array) to `schema_concepts`; add `concept_type`, `domain`, `synonyms`, `tags`
   to `sql_graph_nodes`. Mirror M2's `PRAGMA table_info` + `ALTER TABLE ADD
   COLUMN` guard pattern.
3. **Exporter** — `SCHEMA_VERSION = 15`, milestone `concept_metadata_mrp_seed`;
   `_fetch_concept_nodes` surfaces type/domain/synonyms/tags; parity checkers
   normalize the JSON arrays deterministically (`[]` default, sorted, no
   null↔empty drift).
4. **Seed** — update the `seed_elevations.py` curation rule + add the batch above
   (concepts with synonyms/tags + their metric elevations).
5. **Freeze + gate** — regenerate, freeze `graph_metadata.v15.json`, run
   `scripts/post-merge.sh` (both parity pairs), add tests (metadata surfacing,
   stable JSON serialization, safety-stock exclusion).
6. **Live load** — dry-run then live-load the canonical graph.

**Counts will change** (expected for a content milestone): with all 4 concepts,
concepts 33 → 37 and `elevates` 17 → 21, so totals go 279 → **283** nodes /
**283** edges (36 / 20 / **282** with just the 3 core). The new counts are
recorded in the v15 snapshot + spec.
