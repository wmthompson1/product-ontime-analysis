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

One showcase: the **shared on-time delivery definition** that the SQL semantic
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

---

## Artifacts

| Path | What it is |
|---|---|
| `ontology/on_time_delivery.ttl` | The OWL ontology (vocabulary + one hierarchy). |
| `mapping/on_time_delivery.obda` | The Ontop OBDA mapping (SQL ↔ ontology terms). |
| `mapping/on_time_delivery.properties` | JDBC connection for **manual** runs. |
| `queries/on_time_rate_ops.rq` | On-time rate via the Operations sub-property (the parity number). |
| `queries/on_time_rate_parent.rq` | On-time rate via the shared parent (hierarchy roll-up). |
| `queries/sample_deliveries.rq` | A few per-delivery rows, to show real triples. |
| `parity_check.py` | Runs SPARQL + SolderEngine on the same snapshot and compares. |
| `run_demo.sh` | One command: set up the toolchain (if needed) and run the parity check. |
| `setup.sh` | Downloads the pinned Ontop CLI + SQLite JDBC driver into `tools/`. |

`tools/` (downloaded binaries) and `results/` (run output) are gitignored.

---

## How to run

From this directory:

```bash
./run_demo.sh
```

That will (idempotently) download the toolchain on first run, then print the
parity table above. To re-run just the check after setup:

```bash
python3 parity_check.py
```

### Run a SPARQL query manually

After `./setup.sh`, from the **repository root** (so the relative DB path in
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
committed; `setup.sh` re-fetches the pinned versions.

---

## Read-only & safety

- The live database (`hf-space-inventory-sqlgen/app_schema/manufacturing.db`) is
  WAL-mode and gitignored. The demo opens it **read-only** and takes a backup
  snapshot; Ontop and SolderEngine both run against that snapshot, so they
  provably see identical data and the live file is never written.
- No ArangoDB writes. No changes to the app, Gradio tabs, or SolderEngine.

---

## Out of scope (sensible later steps)

- Auto-generating the OBDA mapping from the `sql_graph_*` tables /
  `graph_metadata.json` (to avoid drift) — here the single showcase mapping is
  hand-authored.
- The full schema — only `purchase_order` and `receiving` for this showcase.
- A live SPARQL HTTP endpoint, a materialized triplestore, or OWL reasoning
  beyond the lightweight profile Ontop uses for SQL rewriting.
