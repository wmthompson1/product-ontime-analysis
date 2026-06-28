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
| `parity_check.py` | Runs SPARQL + SolderEngine on the same snapshot: on-time-rate parity **and** the supplier LEFT-JOIN optionality proof. |
| `rating_parity_check.py` | Recomputes the full My MRP rating from graph triples and proves it equals the stored `performance_rating` per supplier; also captures + SQLGlot-lifts Ontop's SQLite-incompatible aggregate SQL. |
| `sql_lift.py` | Pure helpers: scrape Ontop's native SQL from its DEBUG log and re-transpile the nested join group with SQLGlot so SQLite accepts it. |
| `mapping_drift_check.py` | Offline drift guard: proves the mapping's columns and the ontology vocabulary stay aligned with the governed `graph_metadata.json` (file vs file, no DB/network). |
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

It runs in `scripts/post-merge.sh`, so drift fails the build automatically. To
run it on its own:

```bash
python3 poc/ontop-ontology-poc/mapping_drift_check.py
```

---

## Out of scope (sensible later steps)

- Auto-*generating* the OBDA mapping from the `sql_graph_*` tables /
  `graph_metadata.json` — here the single showcase mapping is hand-authored.
  (Drift of the hand-authored mapping against the schema is now caught
  automatically; see **Drift guard** above. This bullet is about generation,
  not detection.)
- The full schema — only `purchase_order` and `receiving` for this showcase.
- A live SPARQL HTTP endpoint, a materialized triplestore, or OWL reasoning
  beyond the lightweight profile Ontop uses for SQL rewriting.
