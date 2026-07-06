# Three-Way Match — Tenth Ontop Ontology Showcase (2026-07-06)

The ontology tabs are finalized — the three-way match is now the tenth showcase in the Ontop ontology POC, fully checked and passing.

**What I built:**
- **Ontology + mapping** (`three_way_match.ttl` / `.obda`): the three legs of the match — PO line (ordered), receipt line (received), invoice line (billed) — with the two links that tie them together, following the same rules as the other nine showcases.
- **SPARQL queries**: four scalar queries (counts + sums per leg), staying inside the shapes Ontop can translate cleanly for SQLite.
- **Parity check** (`three_way_match_parity_check.py`): runs the SPARQL through the virtual graph and the direct governed SQL on the same read-only snapshot, and proves they match.

**Results — everything matches:**
- Uninvoiced receivers: **1 / 1** (SQL / SPARQL) — the PO-000009 receipt from the docs
- Receipt lines: 29 / 29 (qty 2058), invoiced links: 28 / 28 (qty 1960)
- PO lines: 122 / 122 (qty 8106)
- Governed views cross-check: 8 POs fully received, 14 unreceived, zero overlap

**Code review caught one real bug**, which was fixed: an invoice line pointing at a receipt but with a blank quantity would have been counted as "invoiced" on the SQL side but "uninvoiced" on the graph side. The link was split from the quantity so both sides use the exact same definition, and a built-in regression test with that exact edge case was added — it now runs first every time the parity check runs.

Also wired in: the offline drift guard now covers the new domain (all 7 showcases pass), the CI workflow got a Showcase 10 step, and the POC README documents it with the live numbers.
