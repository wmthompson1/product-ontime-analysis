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
- The single-triple-OPTIONAL limit is ergonomics, NOT correctness — the safe
  default already comes from the deterministic My MRP rule. A SQLGlot pass over
  Ontop's emitted SQL (currently Ontop talks to SQLite directly via sqlite-jdbc;
  we don't intercept the SQL) could lift it, but that is **tabled** by decision.

## Toolchain
Java module `java-graalvm22.3` (JDK 19). Ontop CLI + sqlite-jdbc are downloaded
into `tools/` and **gitignored** (versions + SHA-256 pinned in the setup script).
The setup/run entry points are Python and live in `replit_integrations/`
(`ontop_poc_setup.py`, `ontop_poc_run_demo.py`) so they can be shared alongside
the other integration tools; both resolve the POC dir relative to the repo root.
Run `python3 replit_integrations/ontop_poc_run_demo.py` (or, after setup,
`python3 poc/ontop-ontology-poc/parity_check.py`). Nothing is wired into the
Flask/HF Space app, Gradio, ArangoDB, or SolderEngine.
