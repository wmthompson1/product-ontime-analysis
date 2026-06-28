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
covers *both* showcases automatically (see **Drift guard** below), and the
JVM-dependent parity checks run in CI (see **Continuous integration** below).

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

It guards **every published showcase** in one run — both the on-time-delivery
files and the Showcase 5 operational-OEE files
(`mapping/operational_efficiency.obda` + `ontology/operational_efficiency.ttl`) —
so adding a governed metric automatically extends the guard to its new columns
and terms. It runs in `scripts/post-merge.sh`, so drift fails the build
automatically. To run it on its own:

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
2. runs `parity_check.py`, `rating_parity_check.py`, and `oee_parity_check.py`
   (SPARQL-vs-SolderEngine parity + the supplier optionality / rating proofs);
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

- The full schema — the showcases cover `purchase_order`, `receiving`, and (as of
  Showcase 5) `operation`/`work_order`. Two governed metrics now prove the layer
  scales beyond a single one; publishing the remaining ~33 tables is a later step.
- A materialized triplestore, or OWL reasoning beyond the lightweight profile
  Ontop uses for SQL rewriting. (A live, read-only SPARQL HTTP endpoint is now
  implemented — see **Showcase 4** above.)
