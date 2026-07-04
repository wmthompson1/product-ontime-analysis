# Ontop Ontology Interoperability POC

A small, **read-only proof of concept** showing that the governed SQL semantic
layer (the "Solder Pattern": natural language → SME-approved SQL) can *also* be
published as a **standards-based, interoperable knowledge graph** — without
moving or copying any data.

It uses **[Ontop](https://ontop-vkg.org)**, an open-source *virtual* OBDA
engine. Ontop maps the existing SQLite database to a small **OWL** ontology and
answers standard **SPARQL** queries by rewriting them into SQL on the fly. There
is no triplestore and no data duplication — the SQL we already trust stays the
single source of truth; Ontop is a *publishing* layer on top of it.

> **Not part of the running app.** Nothing here is wired into the Flask/HF Space
> app, the Gradio UI, ArangoDB, or SolderEngine. It writes nothing. It only
> *reads* the manufacturing database (via a read-only snapshot).

---

## What this proves

### Showcase 1 — shared on-time delivery definition

The **shared on-time delivery definition** that the SQL semantic
layer surfaces under three perspectives (Operations, Supplier, Finance).

1. **Standard vocabulary** — an OWL ontology (`ontology/on_time_delivery.ttl`)
   with classes (`Delivery`, `PurchaseOrder`), a relationship
   (`fulfillsPurchaseOrder`), dates, and the on-time score.
2. **A hierarchy** — the three perspectives are modelled as
   `rdfs:subPropertyOf` a single shared parent property `:onTimeScore`. Because
   all three bind to the *same* SQL definition, they carry identical values —
   the "define once, surface under many perspectives" property of the semantic
   layer, restated in OWL. Sub-property entailment means a query on the parent
   transparently rolls up all three perspectives.
3. **Standard query language** — SPARQL queries (`queries/*.rq`) that another
   enterprise/aerospace system could issue against the virtual graph.
4. **Parity with the governed layer** — the on-time rate answered through SPARQL
   **matches** the number SolderEngine produces from its assembled SQL, to
   floating-point tolerance:

   ```
   SolderEngine assembled SQL      : 0.5615384615384615
   SPARQL (Operations subproperty) : 0.561538461538462   (146 of 260 deliveries)
   SPARQL (shared parent property) : 0.561538461538462
   RESULT: PARITY CONFIRMED
   ```

The on-time definition restated by the mapping is exactly the semantic layer's
computation template:

```
AVG(CASE WHEN {receipt_date} IS NOT NULL AND {receipt_date} <= {required_date} THEN 1.0
         WHEN {receipt_date} IS NOT NULL AND {receipt_date} >  {required_date} THEN 0.0
         ELSE NULL END)
```
with `receipt_date → receiving.receipt_date` and
`required_date → purchase_order.required_date`, joined on
`receiving.po_id = purchase_order.po_id`. Ontop computes the per-delivery score
in SQL; SPARQL averages it. Deliveries with no required date produce no score
triple, exactly as SQL `AVG` ignores `NULL`.

### Showcase 2 — the supplier→receiving join, with governed LEFT-JOIN optionality

The supplier→receiving relationship — and the fact that it is *optional* — is
promoted out of hand-coded migration SQL (`suppliers LEFT JOIN receiving`) and
into the governed vocabulary itself:

- `:Supplier` is minted from the **suppliers** table, so **every** supplier is
  published as an entity whether or not it has any receipts.
- `:hasDelivery` (Supplier → Delivery) is minted **separately** from the
  **receiving** table, so the link exists **only** when a real receipt does.
- A supplier with no receipts therefore stays a first-class node with **no**
  `:hasDelivery` edge — the *safe, unlinked state*. Its `:performanceRating`
  carries the deterministic **My MRP** neutral default (`3.0` for a no-receipt
  supplier), so the safe value lives in the data, not in an ad-hoc query.

In SPARQL, a consumer wraps the link in `OPTIONAL {}` (which Ontop compiles to a
SQL **LEFT JOIN**), and unlinked suppliers are preserved:

```sparql
SELECT ?supplier ?name ?rating ?delivery WHERE {
  ?supplier :supplierName ?name ; :performanceRating ?rating .
  OPTIONAL { ?supplier :hasDelivery ?delivery . }
}
```

`parity_check.py` proves this end-to-end: the published supplier population and
the linked subset match the SQL counts, and after injecting a no-receipt
supplier **into the throwaway snapshot only** (never the live DB) it is still
published, stays unlinked, and keeps its `3.0` default:

```
Suppliers published   (SPARQL / SQL): 26 / 26
Suppliers w/ delivery (SPARQL / SQL): 26 / 26
Injected a no-receipt supplier into the throwaway snapshot:
  published in SPARQL              : True
  unlinked (no :hasDelivery edge)  : True
  safe default rating == 3.0       : True
  population 26 → 27, linked 26 → 26 (unchanged)
RESULT: OPTIONALITY GOVERNED
```

> **SQLite backend note.** Ontop treats SQLite as a limited dialect. The simple
> showcase queries above keep a single triple inside `OPTIONAL` because Ontop
> serializes a *multi-triple* `OPTIONAL` whose triples span more than one table
> (a nested LEFT JOIN) — and that shape combined with `GROUP BY` — as SQL the
> SQLite parser rejects (`near "ON"` / `near "UNION"`). A single-triple
> `OPTIONAL` (or a multi-triple one whose triples resolve to the same table)
> yields a clean LEFT JOIN. The optionality is governed by the *mapping design*
> (entity from the full population table, link from receipts), so it holds
> regardless of how a consumer phrases the query.
>
> This was a query-ergonomics limit, **not** a correctness one — and **Showcase
> 3 below now lifts it**: it captures the SQL Ontop generates and re-transpiles
> the nested join group with SQLGlot, so the multi-triple `OPTIONAL` + `GROUP BY`
> aggregates run on SQLite too.

### Showcase 3 — the full supplier rating, recomputed through the graph

Showcase 2 governs *optionality* (a no-receipt supplier keeps its neutral
default). Showcase 3 goes further: it recomputes the **entire deterministic My
MRP rating** for every supplier **purely from triples the virtual graph
publishes**, and proves the result equals the migration's stored
`suppliers.performance_rating` — supplier by supplier.

The rating is `clamp(5 * (0.55*OTD + 0.45*quality), 1, 5)` rounded to 2dp, where:

- **OTD** = `AVG(:opsOnTimeScore)` per supplier,
- **quality** = `AVG(:qualityScore)` per supplier (neutral `0.75` when a supplier
  has receipts but none are graded), and
- **recs** = `COUNT(:hasDelivery)` per supplier (a supplier with no receipts at
  all gets the neutral `3.0`, never a penalty).

`:qualityScore` is a new datatype property mapped from
`receiving.inspection_status` (`1.0` for Passed/Waived, `0.0` for Failed, no
triple for Pending — mirroring the on-time `NULL` pattern). `rating_parity_check.py`
reads these three aggregates through SPARQL, combines them with the exact My MRP
formula, and compares to the stored value:

```
  supplier       OTD  quality  recs   graph  stored  ok
  ----------------------------------------------------------------
  S-001        1.000    0.786    16    4.52    4.52  ok
  S-002        0.500    0.600    16    2.73    2.73  ok
  ...
  S-026        1.000    0.750     4    4.44    4.44  ok
  ----------------------------------------------------------------
  suppliers checked: 26   mismatches: 0
RESULT: RATING PARITY CONFIRMED + SQLite OPTIONAL/GROUP BY LIFTED
```

#### Lifting the SQLite OPTIONAL + GROUP BY limit (SQLGlot)

The OTD aggregate is a multi-triple `OPTIONAL` (`:hasDelivery` from `receiving`,
`:opsOnTimeScore` from `receiving JOIN purchase_order`) combined with `GROUP BY` +
`AVG`. Ontop serializes that as a **nested LEFT JOIN with stacked `ON` clauses**
that the SQLite parser rejects (`near "ON"`). `rating_parity_check.py` lifts the
limit instead of avoiding it:

1. Run Ontop with `ONTOP_LOG_LEVEL=DEBUG` and scrape the **native SQL** it logs.
2. Show SQLite rejects that SQL raw.
3. Re-transpile it with **SQLGlot** (`sql_lift.lift_join_groups` wraps any join
   whose left side carries its own nested joins in a parenthesized subquery), and
   run the lifted SQL successfully on the same snapshot.

```
  Query: supplier_otd_avg.rq
  Raw Ontop SQL rejected by SQLite : YES (near "ON": syntax error)
  Nested join group(s) parenthesized by SQLGlot : 1
  Lifted SQL ran on the snapshot   : YES (26 rows)
```

The lift is needed exactly when an `OPTIONAL`'s triples span **more than one
table**. The quality aggregate is also a multi-triple `OPTIONAL` + `GROUP BY`, but
both of its triples resolve to the same `receiving` table, so Ontop already emits
SQLite-compatible SQL and the same pipeline is a safe no-op there — a useful check
that the lift only kicks in when it must.

### Showcase 4 — a live, read-only SPARQL HTTP endpoint

Showcases 1–3 query the virtual graph through the Ontop CLI. Showcase 4 stands
the **same** ontology + mapping up as a **live SPARQL endpoint over HTTP**, so an
outside system (another aerospace/enterprise service, a BI tool, a notebook) can
ask the governed questions over the wire — still with no triplestore and no data
copy. It stays **read-only**: the server is pointed at a read-only snapshot of
the live database, never the live file (a guard refuses to start otherwise). It
is a local, manually-run POC tool (not a workflow, not auto-started) — see
**Read-only & safety** for the network-exposure note.

Start it from the repository root:

```bash
python3 poc/ontop-ontology-poc/sparql_endpoint.py            # serves on :8090
python3 poc/ontop-ontology-poc/sparql_endpoint.py --port 9999
```

Then query it over HTTP. The on-time delivery rate (the same number Showcase 1
proves), returned as CSV:

```bash
curl -s "http://127.0.0.1:8090/sparql" \
  --data-urlencode "query=PREFIX : <http://example.org/manufacturing/ontime#> SELECT (AVG(?s) AS ?onTimeRate) (COUNT(?s) AS ?deliveries) WHERE { ?d :opsOnTimeScore ?s }" \
  -H "Accept: text/csv"
# onTimeRate,deliveries
# 5.61538461538462E-1,260
```

Every supplier with its OPTIONAL (LEFT-JOIN) deliveries (Showcase 2's governed
optionality, over HTTP) — here sending a saved query file:

```bash
curl -s "http://127.0.0.1:8090/sparql" \
  --data-urlencode "query@poc/ontop-ontology-poc/queries/suppliers_optional_deliveries.rq" \
  -H "Accept: text/csv"
```

Press Ctrl-C to stop; the JVM is torn down cleanly (no orphaned process).

**Automated HTTP smoke test.** `endpoint_smoke_test.py` proves the endpoint
end-to-end: it boots the server on a free port over the snapshot, POSTs the
on-time-rate SPARQL query over HTTP, asserts the result equals the governed
number SolderEngine assembles from the *same* snapshot (to `1e-9`), confirms the
supplier OPTIONAL query returns rows, and tears the server down in a `finally`
block — exiting non-zero on any failure or if a process were left behind:

```bash
python3 poc/ontop-ontology-poc/endpoint_smoke_test.py
```

```
  Governed on-time rate (SolderEngine): 0.5615384615384615
  On-time rate over HTTP (SPARQL)     : 0.561538461538462
  Rates match (tol 1e-09)            : True
  Supplier OPTIONAL rows over HTTP    : 260 (True)
  RESULT: ENDPOINT SERVES THE GOVERNED NUMBER OVER HTTP
  Endpoint shut down cleanly (no orphan process).
```

Like the parity checks (Java + a JVM boot), it is **standalone** — not wired
into `scripts/post-merge.sh`, but it (with the parity checks) now runs in the
dedicated **Ontop interoperability CI** workflow (see **Continuous integration**
below).

### Showcase 5 — a second governed metric (operational OEE)

Showcases 1–4 all tell one story (on-time delivery + the supplier rating it
feeds) over two tables, `purchase_order` and `receiving`. Showcase 5 proves the
interoperability layer **scales beyond that single metric**: it publishes a
*second* governed metric the semantic layer already defines —
**`OEEOperational`** (run-hours efficiency) — over a **different table**
(`operation`) and a **different computation shape** (a ratio of two `SUM`s rather
than an averaged per-row score).

It has its own small vocabulary (`ontology/operational_efficiency.ttl`) and
mapping (`mapping/operational_efficiency.obda`), entirely separate from the
on-time files:

- `:Operation` (from the `operation` table) and `:WorkOrder` (from `work_order`),
  linked by `:partOfWorkOrder`.
- `:actualRunHours` → `operation.act_run_hrs` and `:plannedRunHours` →
  `operation.run_hrs` — the two variables the metric's computation template binds.

The metric restated by the mapping is exactly the semantic layer's computation
template for `OEEOperational`:

```
SUM({act_run_hrs}) / NULLIF(SUM({run_hrs}), 0)
```

The template is **pure aggregation** (no per-row transform), so — mirroring how
Showcase 1 puts `AVG` in SPARQL — the mapping exposes the per-operation hours and
the consumer's SPARQL aggregation assembles the ratio:

```sparql
PREFIX : <http://example.org/manufacturing/oee#>
SELECT ((SUM(?act) / SUM(?run)) AS ?oee) (COUNT(?op) AS ?operations)
WHERE {
  ?op :actualRunHours ?act ; :plannedRunHours ?run .
}
```

`oee_parity_check.py` proves the number answered through SPARQL equals the one
SolderEngine assembles from the same metric's template, on the same read-only
snapshot (exits non-zero on drift):

```
SolderEngine assembled SQL : 0.30159062056605185
SPARQL  (virtual graph)    : 0.301590620566052
RESULT: PARITY CONFIRMED
```

```bash
python3 poc/ontop-ontology-poc/oee_parity_check.py
```

Like the other parity checks (Java + a JVM boot), it is **standalone** — not
wired into `scripts/post-merge.sh`. The offline **drift guard**, however, now
covers *all the published showcases* automatically (see **Drift guard** below),
and the JVM-dependent parity checks run in CI (see **Continuous integration** below).

---

### Showcase 6 — a governed metric with NO SolderEngine template (customer-order demand)

The metric showcases so far (1 and 5) ground their parity against **SolderEngine**,
because each metric has a semantic-layer computation template the engine assembles
(Showcases 2–4 ride on that same governed SQL semantic layer — supplier
optionality, the full rating recompute, and the live endpoint). Showcase 6 proves
the interoperability layer **also covers governed numbers that live as SME-approved
docs + a runnable SQL grounding query only** — with no computation template — by
publishing the **customer-order demand** layer over the virtual graph and proving
it agrees with that **governed SQL directly** (the grounding query in
`hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/manufacturing_customerorderdemand_20260704_000002.sql`). The SQL stays the single
source of truth; Ontop is only a standards-based publishing layer over it.

It has its own small vocabulary (`ontology/customer_order_demand.ttl`) and mapping
(`mapping/customer_order_demand.obda`), entirely separate from the other showcases:

- `:CustomerOrder` (from `customer_order`, carrying `:orderStatus`), `:OrderLine`
  (from `customer_order_line`, carrying `:lineQty` / `:unitPrice`), and `:Part`
  (from `part`, carrying `:onHandQty`).
- The links are minted **on the child** (order line) row — `:forOrder`
  (line → order) and `:forPart` (line → part) — and given a **range only, no
  `rdfs:domain`**: a domain on a link property makes Ontop infer the subject class
  from two sources and emit invalid UNION/LEFT-JOIN SQL on SQLite.

The two demand numbers restate the grounding query and, like the OEE showcase, are
**pure aggregation** — the mapping exposes the per-row facts and the consumer's
SPARQL aggregation assembles the totals. Both are **scalar** (no `GROUP BY`, no
`OPTIONAL`), the shapes that serialize cleanly on Ontop + SQLite:

```sparql
PREFIX : <http://example.org/manufacturing/customerdemand#>
SELECT (SUM(?qty * ?price) AS ?openValue) (COUNT(?line) AS ?lines)
WHERE {
  ?line :forOrder ?order ; :lineQty ?qty ; :unitPrice ?price .
  ?order :orderStatus "Open" .
}
```

ATP for the tightest-ATP part (`P-10026` in the doc's ATP table) is split into two
scalar queries — its on-hand (`part_on_hand.rq`) and its summed open demand
(`part_open_qty.rq`) — and the check computes `ATP = on_hand - open demand` in
Python, dodging the `GROUP BY` needed to return a non-aggregated value beside a sum.

`customer_order_demand_parity_check.py` proves the numbers answered through SPARQL
equal the governed SQL aggregates on the same read-only snapshot (exits non-zero on
drift):

```
Open demand value  (SQL / SPARQL): 290038.31 / 290038.31
Open demand qty    (SQL / SPARQL): 65.0 / 65.0
P-10026 ATP        (SQL / SPARQL): 3.0 / 3.0
RESULT: PARITY CONFIRMED
```

```bash
python3 poc/ontop-ontology-poc/customer_order_demand_parity_check.py
```

Like the other parity checks it is **standalone** (Java + a JVM boot), not wired
into `scripts/post-merge.sh`; the offline drift guard covers its columns and terms
automatically, and it runs in CI (see below).

---

### Showcase 7 — rough-cut capacity load (a second no-template governed layer)

Showcase 6 proved the interoperability layer covers a governed number that lives
as SME-approved docs + a SQL grounding query only. Showcase 7 repeats that proof
on a **different question over a different table**: rough-cut **capacity planning**
— how many standard shop-floor hours are scheduled on each in-house work center.
Like the demand layer it has **no SolderEngine computation template**, so parity
is grounded against the governed SQL directly (the grounding query in
`hf-space-inventory-sqlgen/app_schema/ground_truth/sql_snippets/_archived/manufacturing_capacityplanning_20260704_000001.sql`).

It reads the **same `operation` table as the OEE showcase (Showcase 5)** but is
minted in its **own namespace with its own files** — a different metric (planning
LOAD = setup + run hours) under a different governance:

- `:Operation` (from `operation`, carrying `:setupHours` / `:runHours`) and
  `:WorkCenter` (from `shop_resource`, carrying `:resourceType` / `:workCenterName`).
- The link `:onWorkCenter` (operation → work center) is minted on the operation
  row and given a **range only, no `rdfs:domain`** (the same Ontop+SQLite rule as
  the demand links).
- **The governance lives in the mapping source SQL.** The in-house-only filter
  (`service_id IS NULL` and a machine/labor work center) and the scheduled-only
  filter (`sched_start_date IS NOT NULL`) are restated inside the `.obda` source
  query, so only governed, in-house, scheduled load is ever published as a triple
  — a consumer never has to remember the `WHERE`.

The two capacity numbers are **pure aggregation** (like OEE) and **scalar** (no
`GROUP BY`, no `OPTIONAL`): total in-house load = `SUM(:setupHours + :runHours)`
over every published operation, and the busiest work center's load = the same sum
filtered to one `:onWorkCenter`. The work-center IRI is minted with a path
template, so it must be written as a full IRI in angle brackets in the query (a
`/` is illegal in a SPARQL prefixed name):

```sparql
PREFIX : <http://example.org/manufacturing/capacity#>
SELECT (SUM(?setup + ?run) AS ?wcLoad) (COUNT(?op) AS ?operations)
WHERE {
  ?op :onWorkCenter <http://example.org/manufacturing/capacity#workcenter/LB-003> ;
      :setupHours ?setup ; :runHours ?run .
}
```

`capacity_planning_parity_check.py` proves the numbers answered through SPARQL
equal the governed SQL aggregates on the same read-only snapshot (exits non-zero
on drift):

```
Total in-house load   (SQL / SPARQL): 834.25 / 834.25
LB-003 total load      (SQL / SPARQL): 190.0 / 190.0
RESULT: PARITY CONFIRMED
```

```bash
python3 poc/ontop-ontology-poc/capacity_planning_parity_check.py
```

Like the other parity checks it is **standalone** (Java + a JVM boot), not wired
into `scripts/post-merge.sh`; the offline drift guard covers its columns and terms
automatically, and it runs in CI (see below).

---

### Showcase 8 — shop-floor work & routing (a third no-template governed layer)

Showcases 6 and 7 each proved the interoperability layer covers a governed number
that lives as SME-approved docs + a SQL grounding query only. Showcase 8 repeats
that proof on the **execution side of the shop floor**: how routed work moves
across the floor — a **work order** and the ordered **operations** (routing steps)
that build it. Like the demand and capacity layers it has **no SolderEngine
computation template**, so parity is grounded against the governed SQL directly
(the grounding query in `docs/my-mrp-kb/04-shop-floor-routing/Shop_Floor_Routing.sqlite.sql`).

The grounding query is a **strict two-table join** of `work_order` and `operation`
on `wo_id`. The showcase publishes exactly that — **no third table**. A
human-readable work-station name lives in prose only (in `shop_resource`) and is
never joined, matching the grounding SQL. It is minted in its **own namespace with
its own files**, separate from the OEE (Showcase 5) and capacity (Showcase 7)
layers that read the same `operation` table:

- `:WorkOrder` (from `work_order`) and `:Operation` (from `operation`, carrying
  `:sequenceNumber` / `:operationStatus` / `:runHours` / `:setupHours`).
- The link `:partOfWorkOrder` (operation → work order) is minted on the operation
  row and given a **range only, no `rdfs:domain`** (the same Ontop+SQLite rule as
  the demand / capacity links). The operation mapping's source SQL is the same
  two-table join the grounding uses, so the published operation set is exactly the
  governed joined set.

The two routing numbers are **pure aggregation** and **scalar** (no `GROUP BY`, no
`OPTIONAL`): total routing run hours = `SUM(:runHours)` over every published
operation, and the routing-step count for one specific work order = `COUNT` of the
operations pinned to that work order. The work-order IRI is minted with a path
template, so it must be written as a full IRI in angle brackets in the query (a
`/` is illegal in a SPARQL prefixed name):

```sparql
PREFIX : <http://example.org/manufacturing/routing#>
SELECT (COUNT(?op) AS ?steps)
WHERE {
  ?op :partOfWorkOrder <http://example.org/manufacturing/routing#workorder/WO-240003> .
}
```

`shop_floor_routing_parity_check.py` proves the numbers answered through SPARQL
equal the governed SQL aggregates on the same read-only snapshot (exits non-zero
on drift):

```
Total routing run hours (SQL / SPARQL): 669.55 / 669.55
WO-240003 step count    (SQL / SPARQL): 6 / 6
RESULT: PARITY CONFIRMED
```

```bash
python3 poc/ontop-ontology-poc/shop_floor_routing_parity_check.py
```

Like the other parity checks it is **standalone** (Java + a JVM boot), not wired
into `scripts/post-merge.sh`; the offline drift guard covers its columns and terms
automatically, and it runs in CI (see below).

---

### Showcase 9 — inventory transactions (a fourth no-template governed layer)

Showcases 6, 7, and 8 each proved the interoperability layer covers a governed
number that lives as SME-approved docs + a SQL grounding query only. Showcase 9
repeats that proof on the **inventory ledger**: the movement register that drives
Quantity on Hand — a stream of **inventory transactions**, each an `In` or `Out`
of some `quantity` for a `part` at a `site`. Like the demand, capacity, and
routing layers it has **no SolderEngine computation template**, so parity is
grounded against the governed SQL directly (the grounding query in
`docs/my-mrp-kb/05-inventory-transactions/Inventory_-_Transactions_AI_Review.sqlite.sql`).

Per the Terminology Guide the signed effect on Quantity on Hand is `+qty` for an
`In` (`type='I'`) and `−qty` for an `Out` (`type='O'`), so net movement =
`SUM(In qty) − SUM(Out qty)`. It is minted in its **own namespace with its own
files**:

- `:InventoryTransaction` (from `inventory_transaction`, carrying
  `:transactionType` / `:transactionQty` / `:siteId`) and `:Part` (from `part`).
- The link `:forPart` (transaction → part) is minted on the transaction row and
  given a **range only, no `rdfs:domain`** (the same Ontop+SQLite rule as the
  demand / capacity / routing links).

Rather than express the signed `CASE` inside a single SPARQL `SUM` (a shape Ontop
serializes to SQL that SQLite rejects), each direction is a **separate scalar
`SUM`** and the two are subtracted in Python — so every query stays scalar (no
`GROUP BY`, no `OPTIONAL`, no `CASE` in `SUM`). The per-part net uses the
fully-reconciled case the grounding query walks (`P-10011` @ `SITE-1`, where
ledger net = on-hand = trace = 62 → `'Y'`); the part IRI is minted with a path
template, so it is written as a full IRI in angle brackets in the query (a `/` is
illegal in a SPARQL prefixed name):

```sparql
PREFIX : <http://example.org/manufacturing/inventory#>
SELECT (SUM(?qty) AS ?inQty)
WHERE {
  ?txn :forPart         <http://example.org/manufacturing/inventory#part/P-10011> ;
       :siteId          "SITE-1" ;
       :transactionType "I" ;
       :transactionQty  ?qty .
}
```

`inventory_transactions_parity_check.py` proves the numbers answered through
SPARQL equal the governed SQL aggregates on the same read-only snapshot (exits
non-zero on drift):

```
Net movement, all txns  (SQL / SPARQL): 2104.33 / 2104.33
  In qty  (SQL / SPARQL): 5516.5 / 5516.5  [332 / 332 txns]
  Out qty (SQL / SPARQL): 3412.17 / 3412.17  [307 / 307 txns]
P-10011 @ SITE-1 net    (SQL / SPARQL): 62.0 / 62.0
RESULT: PARITY CONFIRMED
```

```bash
python3 poc/ontop-ontology-poc/inventory_transactions_parity_check.py
```

Like the other parity checks it is **standalone** (Java + a JVM boot), not wired
into `scripts/post-merge.sh`; the offline drift guard covers its columns and terms
automatically, and it runs in CI (see below).

---

## Artifacts

| Path | What it is |
|---|---|
| `ontology/on_time_delivery.ttl` | The OWL ontology (vocabulary + one hierarchy + the Supplier dimension). |
| `mapping/on_time_delivery.obda` | The Ontop OBDA mapping (SQL ↔ ontology terms), incl. `map-supplier` / `map-supplier-delivery`. |
| `mapping/on_time_delivery.properties` | JDBC connection for **manual** runs. |
| `queries/on_time_rate_ops.rq` | On-time rate via the Operations sub-property (the parity number). |
| `queries/on_time_rate_parent.rq` | On-time rate via the shared parent (hierarchy roll-up). |
| `queries/sample_deliveries.rq` | A few per-delivery rows, to show real triples. |
| `queries/suppliers_optional_deliveries.rq` | Every supplier with its OPTIONAL (LEFT-JOIN) deliveries — the governed-optionality showcase. |
| `queries/supplier_otd_avg.rq` | Per-supplier AVG on-time score (multi-triple OPTIONAL + GROUP BY — the shape that needs the lift). |
| `queries/supplier_quality_avg.rq` | Per-supplier AVG quality acceptance rate (multi-triple OPTIONAL + GROUP BY). |
| `queries/supplier_delivery_count.rq` | Per-supplier receipt count (drives the no-history neutral default). |
| `ontology/operational_efficiency.ttl` | The OWL ontology for Showcase 5 (the `OEEOperational` metric over the `operation` table). |
| `mapping/operational_efficiency.obda` | The Ontop OBDA mapping for Showcase 5 (per-operation run hours ↔ ontology terms). |
| `mapping/operational_efficiency.properties` | JDBC connection for **manual** OEE runs. |
| `queries/oee_operational.rq` | Operational OEE = `SUM(actual run hours) / SUM(planned run hours)` (the Showcase 5 parity number). |
| `oee_parity_check.py` | Runs the OEE SPARQL query + SolderEngine on the same snapshot and proves they return the same number (Showcase 5). |
| `ontology/customer_order_demand.ttl` | The OWL ontology for Showcase 6 (the customer-order demand layer: `:CustomerOrder` / `:OrderLine` / `:Part`). |
| `mapping/customer_order_demand.obda` | The Ontop OBDA mapping for Showcase 6 (per-row demand facts ↔ ontology terms; links minted on the order line). |
| `mapping/customer_order_demand.properties` | JDBC connection for **manual** customer-order-demand runs. |
| `queries/open_demand_value.rq` | Open demand value = `SUM(order_qty * unit_price)` over open-order lines (a Showcase 6 parity number). |
| `queries/open_demand_qty.rq` | Open demand quantity = `SUM(order_qty)` over open-order lines (a Showcase 6 parity number). |
| `queries/part_on_hand.rq` | On-hand stock for the tightest-ATP part (`P-10026`) — the availability input to ATP. |
| `queries/part_open_qty.rq` | Summed open demand for `P-10026`; the check computes `ATP = on_hand - this` (the Showcase 6 ATP parity number). |
| `customer_order_demand_parity_check.py` | Runs the demand SPARQL queries + the governed SQL grounding aggregates on the same snapshot and proves they match (Showcase 6 — no SolderEngine template exists for the demand layer). |
| `ontology/capacity_planning.ttl` | The OWL ontology for Showcase 7 (the capacity-planning load layer: `:Operation` / `:WorkCenter`). |
| `mapping/capacity_planning.obda` | The Ontop OBDA mapping for Showcase 7 (per-operation setup/run hours ↔ ontology terms; the in-house + scheduled governance baked into the source SQL). |
| `mapping/capacity_planning.properties` | JDBC connection for **manual** capacity-planning runs. |
| `queries/capacity_total_load.rq` | Total in-house standard load = `SUM(setup_hrs + run_hrs)` over every published operation (a Showcase 7 parity number). |
| `queries/work_center_load.rq` | Total load on the busiest work center (`LB-003`), pinned by `:onWorkCenter` to its IRI (a Showcase 7 parity number). |
| `capacity_planning_parity_check.py` | Runs the capacity SPARQL queries + the governed SQL grounding aggregates on the same snapshot and proves they match (Showcase 7 — no SolderEngine template exists for the capacity layer). |
| `ontology/shop_floor_routing.ttl` | The OWL ontology for Showcase 8 (the shop-floor routing layer: `:WorkOrder` / `:Operation`). |
| `mapping/shop_floor_routing.obda` | The Ontop OBDA mapping for Showcase 8 (per-operation routing facts ↔ ontology terms; the strict two-table `work_order`+`operation` join in the source SQL; the link minted on the operation). |
| `mapping/shop_floor_routing.properties` | JDBC connection for **manual** shop-floor-routing runs. |
| `queries/routing_total_run_hours.rq` | Total routing-step run hours across work orders = `SUM(run_hrs)` over every published operation (a Showcase 8 parity number). |
| `queries/work_order_step_count.rq` | Routing-step count for one work order (`WO-240003`), pinned by `:partOfWorkOrder` to its IRI (a Showcase 8 parity number). |
| `shop_floor_routing_parity_check.py` | Runs the routing SPARQL queries + the governed SQL grounding aggregates on the same snapshot and proves they match (Showcase 8 — no SolderEngine template exists for the routing layer). |
| `ontology/inventory_transactions.ttl` | The OWL ontology for Showcase 9 (the inventory-transactions ledger layer: `:InventoryTransaction` / `:Part`). |
| `mapping/inventory_transactions.obda` | The Ontop OBDA mapping for Showcase 9 (per-row ledger facts ↔ ontology terms; the type/quantity/site movement register in the source SQL; the link minted on the transaction). |
| `mapping/inventory_transactions.properties` | JDBC connection for **manual** inventory-transactions runs. |
| `queries/inv_total_in_qty.rq` | Total inbound movement quantity = `SUM(quantity)` over `type='I'` transactions, with the In txn count (one half of the net-movement math — Showcase 9). |
| `queries/inv_total_out_qty.rq` | Total outbound movement quantity = `SUM(quantity)` over `type='O'` transactions, with the Out txn count (the other half — Showcase 9). |
| `queries/inv_part_in_qty.rq` | Inbound movement quantity for `P-10011` at `SITE-1`, pinned by `:forPart` + `:siteId` (the fully-reconciled per-part case — Showcase 9). |
| `queries/inv_part_out_qty.rq` | Outbound movement quantity for `P-10011` at `SITE-1`; the check computes the per-part net `= In − Out` (a Showcase 9 parity number). |
| `inventory_transactions_parity_check.py` | Runs the inventory-transactions SPARQL queries + the governed SQL grounding aggregates on the same snapshot and proves the net movement, directional quantities, transaction counts, and per-part net match (Showcase 9 — no SolderEngine template exists for the inventory-transactions layer). |
| `parity_check.py` | Runs SPARQL + SolderEngine on the same snapshot: on-time-rate parity **and** the supplier LEFT-JOIN optionality proof. |
| `rating_parity_check.py` | Recomputes the full My MRP rating from graph triples and proves it equals the stored `performance_rating` per supplier; also captures + SQLGlot-lifts Ontop's SQLite-incompatible aggregate SQL. |
| `sql_lift.py` | Pure helpers: scrape Ontop's native SQL from its DEBUG log and re-transpile the nested join group with SQLGlot so SQLite accepts it. |
| `mapping_drift_check.py` | Offline drift guard: proves the mapping's columns and the ontology vocabulary stay aligned with the governed `graph_metadata.json` (file vs file, no DB/network). |
| `generate_mapping.py` | Deterministic offline generator: derives the `.obda` mapping + the mechanically-derivable vocabulary terms from `graph_metadata.json` + the publishing manifest; fails loud on any missing column/FK/binding. Writes both files in place. |
| `mapping/on_time_delivery_manifest.json` | The small committed publishing manifest: stable decisions only (term names, namespace, quality-rule literals, casts/filters, mapping ids + order). No volatile schema facts — those are resolved from `graph_metadata.json`. |
| `mapping_generation_check.py` | Offline equivalence gate: proves the generated `.obda` is byte-identical to the committed mapping, the committed generated vocabulary is fresh, and every generated term is declared in the runtime ontology (file vs file, no DB/network). |
| `sparql_endpoint.py` | Stands the ontology + mapping up as a live, **read-only** SPARQL HTTP endpoint over a snapshot; also the reusable start / ready / stop lifecycle helpers used by the smoke test. |
| `endpoint_smoke_test.py` | Boots the endpoint on a free port, POSTs the on-time-rate SPARQL over HTTP, asserts it equals the governed number, and tears it down cleanly (no orphan); exits non-zero on failure. |
| `../../replit_integrations/ontop_poc_run_demo.py` | One command: set up the toolchain (if needed) and run the parity check. |
| `../../replit_integrations/ontop_poc_setup.py` | Downloads the pinned Ontop CLI + SQLite JDBC driver into `tools/`. |

`tools/` (downloaded binaries) and `results/` (run output) are gitignored.

---

## How to run

From the repository root:

```bash
python3 replit_integrations/ontop_poc_run_demo.py
```

That will (idempotently) download the toolchain on first run, then print the
parity table above. To re-run just the check after setup:

```bash
python3 poc/ontop-ontology-poc/parity_check.py
```

To run the full supplier-rating proof + the SQLGlot lift (Showcase 3) after the
toolchain is set up:

```bash
python3 poc/ontop-ontology-poc/rating_parity_check.py
```

It exits non-zero if any supplier's graph-recomputed rating differs from the
stored value, or if the previously-failing aggregate SQL was not actually lifted.

To run the customer-order demand proof (Showcase 6 — SPARQL vs the governed SQL
grounding query) after the toolchain is set up:

```bash
python3 poc/ontop-ontology-poc/customer_order_demand_parity_check.py
```

It exits non-zero if the open demand value/quantity or the `P-10026` ATP answered
through the virtual graph differs from the governed SQL on the same snapshot.

To run the capacity-planning proof (Showcase 7 — SPARQL vs the governed SQL
grounding query) after the toolchain is set up:

```bash
python3 poc/ontop-ontology-poc/capacity_planning_parity_check.py
```

It exits non-zero if the total in-house load or the busiest work center's load
answered through the virtual graph differs from the governed SQL on the same
snapshot.

To run the shop-floor routing proof (Showcase 8 — SPARQL vs the governed SQL
grounding query) after the toolchain is set up:

```bash
python3 poc/ontop-ontology-poc/shop_floor_routing_parity_check.py
```

It exits non-zero if the total routing run hours or the `WO-240003` step count
answered through the virtual graph differs from the governed SQL on the same
snapshot.

To run the inventory-transactions proof (Showcase 9 — SPARQL vs the governed SQL
grounding query) after the toolchain is set up:

```bash
python3 poc/ontop-ontology-poc/inventory_transactions_parity_check.py
```

It exits non-zero if the net movement, directional (In/Out) quantities,
transaction counts, or the `P-10011` @ `SITE-1` per-part net answered through the
virtual graph differs from the governed SQL on the same snapshot.

### Serve a live SPARQL endpoint (read-only)

Start the endpoint and query it over HTTP (full details + curl examples in
**Showcase 4** above):

```bash
python3 poc/ontop-ontology-poc/sparql_endpoint.py        # http://127.0.0.1:8090/sparql
```

Prove it end-to-end (boots, queries over HTTP, asserts the governed number,
tears down — exits non-zero on failure):

```bash
python3 poc/ontop-ontology-poc/endpoint_smoke_test.py
```

### Run a SPARQL query manually

After `python3 replit_integrations/ontop_poc_setup.py`, from the **repository root** (so the relative DB path in
`mapping/on_time_delivery.properties` resolves):

```bash
poc/ontop-ontology-poc/tools/ontop-cli-5.5.0/ontop query \
  -m poc/ontop-ontology-poc/mapping/on_time_delivery.obda \
  -t poc/ontop-ontology-poc/ontology/on_time_delivery.ttl \
  -p poc/ontop-ontology-poc/mapping/on_time_delivery.properties \
  -q poc/ontop-ontology-poc/queries/on_time_rate_ops.rq
```

> That properties file opens the database read-only (`open_mode=1`), and Ontop
> only issues SELECTs. For the strongest guarantee, the automated
> `parity_check.py` does **not** use it at all — it takes a read-only backup
> snapshot of the live WAL-mode database and points Ontop at the snapshot.

---

## Dependency footprint

All free / open-source:

| Dependency | Version | Source | Footprint |
|---|---|---|---|
| Java runtime | GraalVM CE (JDK 19) | Replit module `java-graalvm22.3` | runtime only |
| Ontop CLI | 5.5.0 | GitHub release (gitignored under `tools/`) | ~45 MB zip |
| SQLite JDBC driver | 3.49.1.0 (org.xerial) | Maven Central (gitignored under `tools/`) | ~14 MB jar |

Nothing is added to the app's Python requirements. The Ontop binaries are not
committed; `replit_integrations/ontop_poc_setup.py` re-fetches the pinned versions.

---

## Read-only & safety

- The live database (`hf-space-inventory-sqlgen/app_schema/manufacturing.db`) is
  WAL-mode and gitignored. The demo opens it **read-only** and takes a backup
  snapshot; Ontop and SolderEngine both run against that snapshot, so they
  provably see identical data and the live file is never written.
- The live SPARQL endpoint (`sparql_endpoint.py`, Showcase 4) is pointed only at
  that read-only snapshot — a guard refuses to start if its JDBC properties
  reference the live database. Note: Ontop's `endpoint` has no bind-host option,
  so it listens on all interfaces inside the container. It is a local,
  manually-run POC tool (not a workflow, not auto-started) — reach it at
  `http://127.0.0.1:<port>/sparql`, stop it when done, and don't forward its port
  publicly. (Replit may auto-add a port mapping the first time it runs; remove
  that mapping from the Ports pane if you don't want the port exposed.)
- No ArangoDB writes. No changes to the app, Gradio tabs, or SolderEngine.

---

## Drift guard

Because the mapping and ontology are hand-authored, a rename or drop in the
governed schema could silently break them. `mapping_drift_check.py` guards
against that — completely offline (file vs file, no database or network), like
the project's other coverage gates. It proves:

- every base table/column the mapping's source SQL reads (resolved through
  aliases, CASE expressions, and joins with SQLGlot) exists as a column node in
  the committed `replit_integrations/graph_metadata.json`;
- every ontology term the mapping targets is declared in the ontology; and
- every declared class / property is backed by at least one mapping — the shared
  parent `:onTimeScore` counts as backed via its mapped sub-properties, so it is
  not falsely flagged.

It guards **every published showcase** in one run — the on-time-delivery files,
the Showcase 5 operational-OEE files (`mapping/operational_efficiency.obda` +
`ontology/operational_efficiency.ttl`), the Showcase 6 customer-order demand
files (`mapping/customer_order_demand.obda` +
`ontology/customer_order_demand.ttl`), the Showcase 7 capacity-planning files
(`mapping/capacity_planning.obda` + `ontology/capacity_planning.ttl`), the
Showcase 8 shop-floor routing files (`mapping/shop_floor_routing.obda` +
`ontology/shop_floor_routing.ttl`), and the Showcase 9 inventory-transactions
files (`mapping/inventory_transactions.obda` +
`ontology/inventory_transactions.ttl`) — so adding
a governed metric automatically extends the guard to its new columns and terms. It runs in
`scripts/post-merge.sh`, so drift fails the build automatically. To run it on its
own:

```bash
python3 poc/ontop-ontology-poc/mapping_drift_check.py
```

To narrow it to a single showcase, pass `--mapping`/`--ontology` explicitly.

---

## Continuous integration

The offline drift/generation guards run in `scripts/post-merge.sh`, but the
JVM-dependent checks (they need Java + the downloaded Ontop toolchain, so they
are deliberately *not* in `post-merge.sh`) are covered by their own GitHub
Actions workflow: **`.github/workflows/ontop-interop-ci.yml`**.

It runs on changes under `poc/ontop-ontology-poc/**` (plus the toolchain setup
scripts) and on a nightly schedule, consistent with the project's other
smoke/drift workflows. Each run:

1. provisions Java + the **pinned** Ontop CLI (via
   `replit_integrations/ontop_poc_setup.py`, checksum-verified);
2. runs `parity_check.py`, `rating_parity_check.py`, `oee_parity_check.py`,
   `customer_order_demand_parity_check.py`, `capacity_planning_parity_check.py`,
   `shop_floor_routing_parity_check.py`, and
   `inventory_transactions_parity_check.py`
   (SPARQL-vs-SolderEngine parity + the supplier optionality / rating proofs, plus
   the customer-order demand, capacity-planning, shop-floor routing, and
   inventory-transactions SPARQL-vs-governed-SQL proofs);
3. runs `endpoint_smoke_test.py` end-to-end — booting the live read-only SPARQL
   HTTP endpoint, answering the governed number over the wire, and confirming a
   clean teardown (no orphan process).

Any mismatch, lift regression, or orphaned process fails the run. On failure it
posts a Slack Block Kit alert — reusing the same `GRAPH_SYNC_ALERT_WEBHOOK`
secret as the sync/drift workflows, and skipped silently when that secret is not
configured. The checks compare the virtual graph against the governed SQL layer
over the **same read-only snapshot**, so the governed database
(`hf-space-inventory-sqlgen/app_schema/manufacturing.db`) must be present in the
checkout; the workflow fails with a clear message if it is missing.

---

## Generated mapping

The drift guard *detects* when the hand-authored mapping falls out of sync with
the schema. `generate_mapping.py` goes one step further and **derives** the
mapping from the governed source of truth, so for this showcase the `.obda` is
no longer hand-maintained — it is regenerated:

```bash
python3 poc/ontop-ontology-poc/generate_mapping.py
```

This reads two inputs and writes two files in place:

- **Inputs** — `mapping/on_time_delivery_manifest.json` (the small committed
  *publishing* manifest: term names, namespace, the quality-rule literals,
  casts/filters, the optionality pattern, and the mapping ids + order) plus the
  governed `replit_integrations/graph_metadata.json` (the *schema* source of
  truth). Every volatile fact — column existence and type, the
  `receiving.po_id → purchase_order.po_id` foreign key, each metric's
  `computation_template` and its `variable_name → table.column` bindings — is
  **resolved from the graph and never hard-coded**. If anything is missing the
  generator fails loudly (non-zero exit) instead of emitting a broken mapping —
  that is the whole anti-desync point.
- **Outputs** — `mapping/on_time_delivery.obda` (the OBDA mapping, emitted
  byte-identical to the committed showcase) and
  `ontology/on_time_delivery.generated.vocab.ttl` (the mechanically-derivable
  vocabulary terms: the classes, datatype/object properties, and the metric
  score properties). The runtime `ontology/on_time_delivery.ttl` — its
  `rdfs:subPropertyOf` hierarchy, labels, and human prose — stays
  **hand-authored governance** and is deliberately *not* generated.

`mapping_generation_check.py` proves the switch to generation is **provably
lossless**, completely offline (file vs file, no DB / network / JVM): the
rendered `.obda` is byte-identical to the committed mapping (byte identity ⇒ the
same SPARQL answers), the committed generated vocabulary is fresh, and every
generated term is declared in the runtime ontology. It runs in
`scripts/post-merge.sh` alongside the drift guard. To run it on its own:

```bash
python3 poc/ontop-ontology-poc/mapping_generation_check.py
```

---

## Out of scope (sensible later steps)

- The full schema — the showcases cover `purchase_order`, `receiving`,
  `operation`/`work_order`, `shop_resource`, and (as of Showcase 9)
  `inventory_transaction`/`part`. Multiple governed layers now prove the pattern
  scales beyond a single metric; publishing the remaining tables is a later step.
- A materialized triplestore, or OWL reasoning beyond the lightweight profile
  Ontop uses for SQL rewriting. (A live, read-only SPARQL HTTP endpoint is now
  implemented — see **Showcase 4** above.)
