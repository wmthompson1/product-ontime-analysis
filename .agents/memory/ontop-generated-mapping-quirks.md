---
name: Ontop generated-mapping quirks
description: Gotchas when publishing new tables via generate_mapping.py manifests (FK aliasing, SQLite DATETIME literals, per-manifest checks)
---

Rules learned publishing the gl_* ledger tables via the generated-mapping pattern:

- **FK column name ≠ target key name**: entity object_properties emit the target class's `iri_template` verbatim, so when the child FK column differs from the target key (e.g. `gl_events.job_id -> work_order.wo_id`) the source must alias `fk_col AS target_key` or Ontop fails on an unresolvable placeholder. The generator now does this automatically.
  **Why:** iri templates are written in terms of the parent key; Ontop resolves `{name}` only against source SELECT columns.
- **SQLite DATETIME columns**: Ontop cannot map JDBC type DATETIME to an RDF datatype (`UnknownDatatypeException`, `inferDefaultDatatype` disabled). Any xsd:string literal on a non-TEXT column must carry an explicit `^^xsd:string` suffix; TEXT columns stay suffix-free (byte-identity with older showcases preserved).
- **mapping_generation_check.py is manifest-parametric**: run it once per showcase in post-merge with explicit `--manifest/--obda/--vocab/--ontology` args; the vocab-closure leg needs a hand runtime ontology declaring every generated term.
- **Namespace hygiene**: new OBDA showcases must NOT re-declare local names that exist in the ledger# ontology files (ledger_events_vocab_check flags any sibling .ttl referencing ledger# that redeclares a ledger term) — use a distinct namespace (jobcost#) and distinct names (CostedJob, costsJob), linking via skos:closeMatch only.
- **How to apply:** any new table published over SPARQL: manifest + generate + hand ontology + per-manifest generation check + one scalar COUNT/SUM smoke query per table against the same snapshot (see ledger_sparql_smoke.py).
