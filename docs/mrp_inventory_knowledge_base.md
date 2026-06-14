# MRP & Inventory — Knowledge Base and Revised Proposal

> **Status:** v15 — concept payload + MRP/inventory vocabulary seeded (in sync with
> the frozen `SCHEMA_VERSION = 15`). Earlier revisions of this file were a v14 draft
> proposal; §8 now records the decision **as built**.
> **Purpose:** Formalize manufacturing resource planning (MRP) and inventory
> concepts so an SME can read this and know *exactly what to build* in the
> semantic graph.
> **Two rules (read first):**
> 1. **Operationally recognizable** — a concept must be a thing an SME
>    *recognizes from doing the work* (the words used on the job), **not an
>    abstract category**. If a materials manager wouldn't say it on the floor,
>    it isn't a concept.
> 2. **Column-anchored only for an `elevates` edge** — a recognized term becomes a
>    graph **concept node** right away, *whether or not* a column exists yet. It
>    only gains an `elevates` edge once it points to a real ERP column an SME can
>    put their finger on. A recognized term with no column is an **orphan glossary
>    node** (see §8) — it is kept, not dropped.
>
> If something is only a formula, it is a **derived metric**: it may still hold a
> concept node as recognized vocabulary, but its math lives in SME-approved SQL — a
> concept node records that a term *exists*, not how it is *computed*. SQL is never
> machine-generated (Solder Pattern).

> **Resolved (§8) — measures vs. categories.** The `elevates` curation rule, which
> once admitted only **bounded categorical discriminators** (status / type / class /
> location), was extended at v15 to also admit *canonical named measures*
> (`concept_type = metric`, e.g. reorder point, lead time, on-hand). Pure formulas
> (EOQ, ATP, lead-time demand) still stay in SME-approved SQL — they keep a concept
> node as vocabulary but get no `elevates` edge.

This document does two things:
1. **Records the topology as built** at `SCHEMA_VERSION = 15` (§1, §8).
2. Maintains the **inventory concept knowledge base** — concrete concept cards an
   SME can author.

---

## 1. What already exists today (v15 — facts, not proposals)

The graph already has three kinds of nodes and three kinds of edges. Nothing
below needs to be invented:

| Node type | Count | Example |
|---|---|---|
| `table` | 23 | `part`, `purchase_order`, `work_order` |
| `column` | 223 | `part:reorder_point`, `part:on_hand_qty` |
| `concept` | 43 | `QuantityBasisEngineering`, `StockMovementDirection`, `ReorderPoint` |

| Edge type | Count | Meaning |
|---|---|---|
| `has_column` | 223 | table → its columns (structural) |
| `references` | 39 | column → column foreign key (structural) |
| `elevates` | 20 | **column → concept** (semantic) — *this is the important one* |

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

Revised to fit the graph as built (v15) — three small changes, same spirit:

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

## 8. M3 — concept metadata + MRP/inventory vocabulary (COMPLETE, v15)

### 8.1 Decision — concepts are perspective-agnostic glossary nodes
Two rules were settled and built for this milestone:

1. **The `elevates` curation rule is extended** from "bounded categorical
   discriminator only" to also admit a *canonical named measure* — a real, stored
   business quantity (reorder point, lead time, on-hand) with
   `concept_type = 'metric'`. `elevates` already means "column → business concept"
   and the existing `QuantityBasisEngineering` / `…Manufacturing` metric concepts
   already elevate from a quantity column, so a stored measure needs no new
   predicate. **Formulas stay out:** EOQ, available-to-promise, lead-time-demand,
   and safety-stock math remain *derived metrics* in SME-approved SQL (§5) — only a
   *stored* column elevates.

2. **The whole SME vocabulary is seeded as concept nodes — even terms with no
   column yet (user decision).** A concept node is the ontology's record that a term
   *exists and is recognized*; it does not require a source column. So all 10
   MRP/inventory terms become concept nodes now. The 3 that map to a real column
   also get an `elevates` edge; the other 7 are **orphan glossary nodes** —
   intentionally edgeless until their column is onboarded by ETL. This lets the
   ontology lead the warehouse instead of trailing it.

**Perspective is dual-namespace.** Perspective is stamped **only on the `elevates`
edge**, never on the concept node. `ReorderPoint` is one canonical,
perspective-agnostic thing; the *reading* of a column through a lens — that
`Inventory_Transactions` sees `part.reorder_point` as `ReorderPoint` — lives on the
edge. (This resolves the spec's Open Question 1: perspective = edge property, not a
node.)

### 8.2 The MRP/inventory vocabulary — all 10 seeded as concept nodes
The SME proposed 10 MRP terms. **All 10 are seeded as concept nodes**
(`concept_type = 'metric'`, `domain = 'operations'`, each carrying synonyms + tags).
Each was then run past **rule 1 (does a real column exist in *this* schema?)** using
the live `manufacturing.db` to decide whether it *also* gets an `elevates` edge.
Perspectives use the real name `Inventory_Transactions` (there is no `Inventory` /
`Procurement` / `Planning` perspective).

**Column-anchored — concept node + `elevates` edge (perspective `Inventory_Transactions`):**

| Concept | Source column | Synonyms | Tags |
|---|---|---|---|
| `ReorderPoint` | `part.reorder_point` | ROP, reorder level, order point | mrp, inventory, replenishment |
| `LeadTime` | `part.lead_time_days` | replenishment lead time, procurement lead time, supplier lead time | mrp, inventory, planning |
| `OnHandQuantity` | `part.on_hand_qty` | on hand, QOH, quantity on hand, stock on hand | mrp, inventory, stock |

**Orphan glossary nodes — concept node now, no `elevates` edge until a column is onboarded:**

| Concept | Why no edge yet | Synonyms | Tags |
|---|---|---|---|
| `SafetyStock` | No safety-stock column here (`MIN_STOCK_QTY` in private SQL Server) | buffer stock, safety inventory | mrp, inventory, buffer |
| `LeadTimeDemand` | Derived: demand rate × lead time — no stored column | demand during lead time, DLT | mrp, inventory, demand |
| `MinimumStockQuantity` | No `min_stock` column here | min stock, minimum level, min | mrp, inventory, min-max |
| `MaximumStockQuantity` | No `max_stock` column here | max stock, maximum level, max | mrp, inventory, min-max |
| `EconomicOrderQuantity` | Derived: balances ordering vs holding cost — no stored column | EOQ, economic order qty, optimal order quantity | mrp, inventory, ordering |
| `AvailableToPromise` | Derived: on-hand − allocated — no stored column (`allocated` absent) | ATP, available to promise quantity | mrp, inventory, availability |
| `AllocatedQuantity` | No `allocated` / `reserved` column here | allocated, reserved quantity, committed quantity | mrp, inventory, allocation |

> An orphan node becomes anchored the moment its column is onboarded: add the
> elevation triple, re-run the seed + exporter, and the edge appears with no node
> churn. The derived (formula) terms keep their concept node as recognized
> vocabulary — a concept node records that the term *exists*, not how it is
> *computed*; the math still lives in SME-approved SQL (§5).

Example elevation triple authored in `seed_elevations.py` (batch 6):
```
("Inventory_Transactions", "ReorderPoint", "part", "reorder_point", 3,
 "Stock level that triggers replenishment")
```

### 8.3 Build outcome (one v15 bump)
1. **DDL (additive guards)** — `synonyms`, `tags` (TEXT, canonical JSON array)
   added to `schema_concepts`; `concept_type`, `domain`, `synonyms`, `tags` added to
   `sql_graph_nodes`, mirroring M2's `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`
   boot-guard pattern.
2. **Exporter** — `SCHEMA_VERSION = 15`, milestone `concept_metadata_mrp_seed`;
   `_fetch_concept_nodes` surfaces type/domain/synonyms/tags; the JSON arrays
   serialize deterministically (`[]` default, no null↔empty drift).
3. **Seed** — `seed_elevations.py` carries the 10 MRP concept nodes (synonyms/tags)
   and the 3 metric elevations (batch 6).
4. **Freeze + gate** — regenerated, froze `graph_metadata.v15.json`, ran
   `scripts/post-merge.sh` (both parity pairs byte-identical: SQL↔file,
   SQL↔live-AQL); added concept-payload round-trip + JSON-stability tests.
5. **Live load** — dry-ran, then truncate-then-imported the canonical into live
   ArangoDB (289 / 282, all endpoints resolve); both apps boot unaffected.

**Counts (content milestone):** +10 concept nodes, +3 `elevates` edges → concepts
33 → **43**, `elevates` 17 → **20**, totals 279 → **289** nodes / **282** edges.
Recorded in the v15 snapshot + the spec Decision Log (rev 0.7).
