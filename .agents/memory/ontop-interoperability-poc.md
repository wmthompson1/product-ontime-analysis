---
name: Ontop interoperability POC
description: How the SQL semantic layer is republished as a standards-based virtual OWL/SPARQL graph, and the read-only WAL-snapshot pattern used to prove parity.
---

# Ontop interoperability POC

A read-only proof of concept lives at `poc/ontop-ontology-poc/`. It shows the
governed SQL semantic layer (Solder Pattern) can ALSO be published as a
standards-based, interoperable knowledge graph using **Ontop** (virtual OBDA:
maps SQLite → OWL, answers SPARQL by rewriting to SQL, no data movement, no
triplestore).

## Positioning decision
Ontop is the **publishing / interoperability** layer, NOT an authoring or
governance layer. SQL stays the single source of truth; the OWL ontology +
`.obda` mapping are a standards-based restatement of an *existing* SME-approved
computation template. We chose Ontop over Stardog because virtual OBDA mirrors
the Solder Pattern shape and is free.
**Why:** the user's value is interoperability (a vocabulary + SPARQL another
aerospace/enterprise system can consume) on top of SQL we already trust — not a
new copy of the data.

## "Define once, many perspectives" → OWL hierarchy
The three perspectives (Ops/Supplier/Finance) of one shared on-time definition
are modelled as `rdfs:subPropertyOf` a single parent property `:onTimeScore`.
All three bind to the SAME mapping SQL, so they carry identical values; querying
the parent rolls them up via sub-property entailment and yields the same number.
This is the standards-based restatement of the semantic layer's
define-once-identical-SQL property.

## Read-only parity pattern (reusable)
To compare two engines against the live WAL-mode, gitignored DB without ever
writing to it: open the live DB read-only, take a `sqlite3` backup snapshot, and
point BOTH engines at the snapshot. This guarantees identical data AND honors
strict read-only. The per-row score mapping returns NULL when there is no
required date, so Ontop emits no triple — matching SQL `AVG` ignoring NULL.
**How to apply:** any "does graph/alt-engine X agree with SolderEngine" check
should snapshot first, not query the live WAL file twice.

## Governed LEFT-JOIN optionality via mapping shape (not query phrasing)
To promote an *optional* relationship (e.g. supplier→receiving) into the ontology
so absence is a safe state: mint the entity class from the FULL population table
and mint the link property SEPARATELY from the child/fact table. Then an entity
with no children is still published but simply has no link edge — a SPARQL
`OPTIONAL { }` (compiled by Ontop to a SQL LEFT JOIN) preserves it, and its safe
default value (here the My-MRP neutral 3.0 rating) rides along straight from the
data. Optionality is then enforced by the *mapping design*, not by whether a
consumer remembers to write OPTIONAL.
**Why:** keeps "absence of receipts ≠ poor performance" governed in the
vocabulary, matching the migration's deterministic rule, instead of living only
in hand-coded migration SQL.
**Gotchas (Ontop + SQLite specifically):**
- Do NOT give the link property an `rdfs:domain` or an inverse — that makes Ontop
  infer the subject class from two sources and emit invalid UNION/LEFT-JOIN SQL
  ("near UNION"). Give the property a `range` only.
- Keep a SINGLE triple inside `OPTIONAL`. A multi-triple `OPTIONAL` (nested LEFT
  JOIN) and `OPTIONAL` + `GROUP BY`/`AVG` both serialize to SQL SQLite rejects
  ("near ON" / "near UNION").
- No `#` comments inside `.obda` `[[ ]]` target/source blocks (parser rejects).
- To prove optionality empirically, inject a synthetic no-child row into the
  THROWAWAY snapshot only (never the live DB) and assert it stays published +
  unlinked + carries its default; compare exact SPARQL-IRI-tail vs SQL id SETS,
  not just counts.
- The multi-triple-OPTIONAL + GROUP BY limit is ergonomics, NOT correctness, and
  is now **LIFTED** (`rating_parity_check.py` + `sql_lift.py`): run Ontop with
  `ONTOP_LOG_LEVEL=DEBUG`, scrape the LAST "Resulting native query" SQL from the
  log, and re-transpile with SQLGlot — wrap any join whose `this` carries nested
  joins in a Subquery so the stacked-`ON` nested LEFT JOIN parses on SQLite. KEY
  nuance: the lift is needed ONLY when the OPTIONAL's triples span >1 physical
  table (OTD = receiving + purchase_order). A multi-triple OPTIONAL whose triples
  resolve to the SAME table (quality = both from receiving) and a single-triple
  OPTIONAL are already SQLite-compatible, so the same pipeline is a safe no-op.

## Full My MRP rating republished through the graph
`rating_parity_check.py` recomputes the ENTIRE deterministic rating
(`clamp(5*(0.55*OTD + 0.45*quality),1,5)`, 2dp) per supplier purely from graph
aggregates — `AVG(:opsOnTimeScore)`, `AVG(:qualityScore)`, `COUNT(:hasDelivery)`
— and proves it equals the stored `suppliers.performance_rating`.
**How to apply:** mirror the backfill migration's constants EXACTLY (W_OTD .55 /
W_QUALITY .45 / neutral-quality .75 when there are graded-receipts-but-none /
no-receipts rating 3.0); the quality input is a single-table `:qualityScore`
mapped from `receiving.inspection_status` (1.0 Passed/Waived, 0.0 Failed, no
triple for Pending — same NULL pattern as on-time). Identify the supplier-id
column in the lifted aggregate by "values ⊆ known supplier ids" (robust to
Ontop's column aliasing), not by name/position.

## Live read-only SPARQL HTTP endpoint
The same ontology + `.obda` mapping can be served as a live SPARQL endpoint over
HTTP via Ontop's `endpoint` subcommand (`sparql_endpoint.py` launcher +
`endpoint_smoke_test.py`), still read-only over the snapshot. Non-obvious bits:
- **Readiness must be a real query, not a socket/port check.** The HTTP port
  accepts connections seconds before the mappings finish loading; poll by POSTing
  a trivial `SELECT ... LIMIT 1` to `/sparql` and wait for HTTP 200, else the
  first real query races and fails.
- **Snapshot-only guard before boot:** refuse to start if the runtime
  `.properties` JDBC url points at the live DB (only the snapshot is allowed) —
  the endpoint is long-lived, so a wrong path would expose the live WAL file.
- **Clean teardown:** the `ontop` shell launcher ends with `exec "$JAVA" …`, so
  the Popen PID *is* the JVM and SIGTERM reaches it; still start it with
  `start_new_session=True` and stop via `killpg` (SIGTERM→SIGKILL) so no orphan
  JVM survives. Verify "no orphan" with a self-match-proof pattern like
  `pgrep -af 'cli[.]Ontop'` (a plain `it.unibz.inf.ontop` pattern matches the
  checking shell's own argv and gives a false positive).
- **SPARQL CSV output is scientific notation** (e.g. `5.61538461538462E-1`);
  Python `float()` parses it fine — don't hand-roll a decimal parser.
- Query over HTTP with `POST /sparql`, form param `query`, `Accept: text/csv`.
- Like the parity checks (Java + JVM boot) it is **standalone**, NOT added to
  `scripts/post-merge.sh`.

## Publishing a governed layer that has NO SolderEngine template
A governed number can exist as SME-approved docs + a runnable SQL grounding query
only (no semantic-layer `computation_template`/concept) — e.g. the customer-order
demand layer (`docs/my-mrp-kb/Customer_Order_Demand.sqlite.sql`). Such a showcase
grounds parity against the **direct governed SQL** run on the same read-only
snapshot, NOT SolderEngine (there is no template to assemble). This is still
faithful to the Solder Pattern: the SQL stays the single source of truth and
Ontop is only the publishing layer. Do NOT invent a SolderEngine template just to
reuse the existing parity helper — that is scope creep into the semantic layer.
**How to apply:** import `parity_check as pc` for the snapshot/properties/CSV
helpers, run the `.rq` files through the Ontop CLI, run the doc's aggregates via
`sqlite3` on the SAME snapshot, assert equal. Register the new (label, obda, ttl)
in `mapping_drift_check.py` `DEFAULT_SHOWCASES` so the offline post-merge guard
covers it; keep the JVM parity check standalone (CI only, not post-merge.sh).
Also add a step for the new check to `.github/workflows/ontop-interop-ci.yml`
(the JVM checks run there, not in post-merge.sh).

### Parity nuance: SUM/COUNT showcases want COALESCE, not NULL-drop
The on-time/quality showcases deliberately emit NO triple for a NULL so SPARQL
matches SQL `AVG` (which ignores NULL). A SUM/COUNT showcase (e.g. capacity
LOAD = `SUM(setup_hrs + run_hrs)`) wants the OPPOSITE: use `COALESCE(col, 0)` in
**both** the `.obda` source SQL and the governed grounding SQL, so a NULL never
drops a row from the SPARQL inner join. Then the published population equals the
governed population and you can assert the operation **COUNT** alongside the SUM
— a count guard catches population drift that a coincidentally-matching sum would
hide. Assert both; don't just print them.
**Why:** SPARQL requires all triples in a basic graph pattern to bind, so a
missing `:runHours` triple silently shrinks both the SUM and the COUNT.

### CI workflow YAML caution
A heredoc body inside a `run: |` block (`PAYLOAD=$(python3 - <<'PYEOF' … PYEOF`)
must be indented to the block scalar's level; if it is dedented to column 0 the
literal block terminates early and the WHOLE workflow fails to parse (so every
step, not just the heredoc step, silently never runs). Indent the body + closing
`PYEOF` to match — YAML strips that common indent back off, so bash still receives
the same script. Always re-validate the file with a YAML parser after editing it.

## SPARQL gotcha: instance IRIs containing '/' need angle brackets
An instance IRI minted with a path template (e.g. `:part/{part_id}` →
`…#part/P-10026`) CANNOT be referenced in a SPARQL query as the prefixed name
`:part/P-10026` — `/` is illegal in a SPARQL PN_LOCAL, so RDF4J throws
`MalformedQueryException: Encountered " "/" "`. Write the FULL IRI in angle
brackets instead: `<http://example.org/manufacturing/customerdemand#part/P-10026>`.
(The `/` is fine inside `.obda` target templates — this only bites in `.rq` query
text.) Also: a non-aggregated value beside a `SUM` forces a `GROUP BY`; to keep
ATP-style answers scalar/SQLite-safe, split into two scalar queries (on-hand;
summed open qty) and subtract in Python. `xsd:double` datatype-property ranges
trigger a benign "not OWL 2 QL" WARN from Ontop but still answer correctly.

## Toolchain
Java module `java-graalvm22.3` (JDK 19). Ontop CLI + sqlite-jdbc are downloaded
into `tools/` and **gitignored** (versions + SHA-256 pinned in the setup script).
The setup/run entry points are Python and live in `replit_integrations/`
(`ontop_poc_setup.py`, `ontop_poc_run_demo.py`) so they can be shared alongside
the other integration tools; both resolve the POC dir relative to the repo root.
Run `python3 replit_integrations/ontop_poc_run_demo.py` (or, after setup,
`python3 poc/ontop-ontology-poc/parity_check.py` for Showcases 1–2, or
`python3 poc/ontop-ontology-poc/rating_parity_check.py` for Showcase 3 +
the SQLGlot lift). Nothing is wired into the Flask/HF Space app, Gradio,
ArangoDB, or SolderEngine.
