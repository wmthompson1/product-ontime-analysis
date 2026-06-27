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

## Toolchain
Java module `java-graalvm22.3` (JDK 19). Ontop CLI + sqlite-jdbc are downloaded
into `tools/` and **gitignored** (versions + SHA-256 pinned in the setup script).
The setup/run entry points are Python and live in `replit_integrations/`
(`ontop_poc_setup.py`, `ontop_poc_run_demo.py`) so they can be shared alongside
the other integration tools; both resolve the POC dir relative to the repo root.
Run `python3 replit_integrations/ontop_poc_run_demo.py` (or, after setup,
`python3 poc/ontop-ontology-poc/parity_check.py`). Nothing is wired into the
Flask/HF Space app, Gradio, ArangoDB, or SolderEngine.
