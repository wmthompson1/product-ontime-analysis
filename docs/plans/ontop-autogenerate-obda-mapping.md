# Auto-generate the OBDA mapping

## What & Why
Today the Ontop virtual-graph mapping and ontology are hand-authored, so a rename
or drop in the governed schema can silently desync them (only caught after the
fact by the drift guard). Generate the OBDA mapping (and the ontology vocabulary
it targets) directly from the governed source of truth — `graph_metadata.json` /
the `sql_graph_*` tables — so the published knowledge graph is derived, not
maintained by hand. This is the first "sensible later step" the POC README calls
out.

## Done looks like
- A single command regenerates the OBDA mapping (and ontology vocabulary terms)
  for the existing showcase from the governed schema metadata, deterministically.
- The generated mapping produces the **same** SPARQL answers as today: the
  existing parity checks still pass against the generated artifacts (on-time rate
  matches SolderEngine; supplier optionality preserved).
- A parity/diff check proves the generated mapping is equivalent to the committed
  hand-authored mapping for the showcase (so the switch is provably lossless).
- Regeneration is offline (file → file, no DB/network needed beyond reading the
  committed metadata) and fits the project's existing gate style.
- README documents how to regenerate and updates the "Out of scope" bullet.

## Out of scope
- Expanding which tables are covered (kept to the current showcase here — that is
  a separate task).
- Auto-generating OWL hierarchies/perspectives beyond what the showcase already
  declares; only the mechanically-derivable vocabulary is generated.
- Wiring generation into the running app.

## Steps
1. **Generator** — Add a script that reads the governed schema metadata and emits
   the OBDA mapping + the column/class/property vocabulary for the showcase, with
   deterministic ordering.
2. **Equivalence check** — Add a check that proves the generated mapping is
   equivalent to the committed hand-authored mapping (and that the existing parity
   checks pass when pointed at the generated artifacts).
3. **Docs** — Document the regeneration command and move mapping generation out of
   the README's "Out of scope" list.

## Relevant files
- `poc/ontop-ontology-poc/mapping/on_time_delivery.obda`
- `poc/ontop-ontology-poc/ontology/on_time_delivery.ttl`
- `poc/ontop-ontology-poc/mapping_drift_check.py`
- `replit_integrations/graph_metadata.json`
- `replit_integrations/generate_sql_graph_dump.py`
- `poc/ontop-ontology-poc/parity_check.py`
- `poc/ontop-ontology-poc/README.md:384-395`
