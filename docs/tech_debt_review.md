## Tech Debt Review — Schema & Metadata

Summary
- `schema_edges` — relationship metadata table (7 rows present). Contains `from_table`, `to_table`, `join_column`, and other descriptive fields, but no enforced foreign key constraints. Relationships are advisory and were used by the graph persistence code.
- `schema_nodes` — table metadata. The local SQLite database currently has no rows in `schema_nodes`, so relationship edges are orphaned and UIs that rely on node metadata show missing table names.
- `manufacturing_acronyms` — holds acronym definitions and context. Appears empty in the local faux DB; acronym mappings are therefore synthesized from edge/context metadata (less reliable).

Why this is a problem
- Lack of primary keys and unique constraints prevents safe FK enforcement and reliable referencing.
- Faux data (synthetic) meant some candidate keys could not be detected automatically, causing heuristics to miss natural keys.
- Missing `schema_nodes` entries means relationship metadata in `schema_edges` cannot be resolved to table-level metadata, degrading UX and hint generation.

Immediate remediation (safe, low-risk)
1. Populate `schema_nodes` with canonical table metadata (insert basic rows for each table). This fixes lookup failures immediately and is reversible.
2. Add `name` attributes to persisted Arango vertex documents (already added via script). This fixes visualization without changing DB schema.
3. Enhance the generator (`scripts/generate_schema_metadata.py`) to compute per-column `null_fraction` and `uniqueness_score` to better recommend `candidate_keys`.

Medium-term remediation (moderate risk; requires migrations)
1. Promote `edge_id` and `acronym_id` to explicit PRIMARY KEYs (create new table, copy data, swap tables) for `schema_edges` and `manufacturing_acronyms`.
2. Add UNIQUE constraint on `schema_nodes.table_name` so it can be referenced from `schema_edges` safely.
3. Add FK constraints on `schema_edges.from_table` and `schema_edges.to_table` referencing `schema_nodes.table_name` (after step above).

Long-term recommendations
- Normalize `manufacturing_acronyms`: enforce unique `acronym` (upper-cased), deduplicate definitions, and categorize.
- Add CI validation that checks for dangling `schema_edges` (edges referencing nonexistent `schema_nodes`) and that candidate keys are still valid (uniqueness + low nulls).
- Improve persistence pipeline so GraphML → Arango uses `table`/`_key` and `name` attributes (already implemented in part) and reflects candidate_keys in node documents.

Quick validation & repair commands
- Generate metadata (already available):
```bash
./.venv/bin/python scripts/generate_schema_metadata.py
```
- Auto-populate missing `schema_nodes` from `schema/tables/*.json` (example pattern):
```python
import json, glob
import sqlite3
conn = sqlite3.connect('data/manufacturing_analytics.sqlite3')
cur = conn.cursor()
for f in glob.glob('schema/tables/*.json'):
    j = json.load(open(f))
    cur.execute("INSERT OR IGNORE INTO schema_nodes(table_name, table_type, description) VALUES (?, ?, ?)", (j['table'], 'table', 'auto-populated'))
conn.commit()
```

Priority plan (next 3 tasks)
1. Add uniqueness/null heuristics to the metadata generator and re-run (low effort).
2. Provide an `auto-populate-schema-nodes` script to seed `schema_nodes` from `schema/tables/*.json` (low risk).
3. Draft migration scripts to make `schema_nodes.table_name` unique and promote `edge_id`/`acronym_id` to PKs (review before run).

References
- `scripts/generate_schema_metadata.py` — metadata generator (produces `schema/tables/*.json`).
- `app/database_hints_loader.py` — loader that now supports SQLite and extracts nodes/edges/acronyms for hints.
- `000index.md` — Arango reminder and notes about accessing Arango from devcontainer.

If you want, I can implement items 1–2 in the priority plan now (generator heuristics + auto-populate script) and run them against the local DB.
tech debt review  
docs/tech\_debt\_review

FKs  
replit prompt  
*we had table relationships in the updated contextual hints demo. Could you review in 2-3 pages and recommend which files to highlight in the repo for Copilot? I need this for tech debt review.*

Here's your **Tech Debt Review Summary** for Copilot:

---

Files to Highlight for Tech Debt Review  
Priority 1: Core Schema Metadata

| File | Purpose | Tech Debt Issue |
| ----- | ----- | ----- |
| app/database\_hints\_loader.py | Loads FK relationships from schema\_edges | Uses psycopg2 (PostgreSQL) but HF Space uses SQLite |
| app/contextual\_hints.py | Hint engine with hardcoded acronyms | 7 acronyms hardcoded \- should migrate to manufacturing\_acronyms table |

Priority 2: Schema DDL

| File | Purpose | Tech Debt Issue |
| ----- | ----- | ----- |
| schema/schema\_sqlite.sql | SQLite schema (20 tables) | 4 tables missing from PostgreSQL migration |
| schema/schema.sql | Original PostgreSQL (24 tables) | Source of truth |

Priority 3: Database Tables Needing Work

| Table | Current State | Needed |
| ----- | ----- | ----- |
| schema\_edges | 7 relationships | More FKs for 20 tables |
| schema\_nodes | Empty | Table descriptions |
| manufacturing\_acronyms | Empty | Populate with NCM, OTD, OEE, etc. |

---

Current FK Relationships (7 total)

equipment → product (part\_id)

product → supplier (supplier\_id)

equipment → production\_line (line\_id)

equipment → maintenance\_log (equipment\_id)

production\_line → quality\_control (line\_id)

product → quality\_control (product\_id)

equipment → quality\_control (equipment\_id)

---

Action Items

1. **Add candidate keys** \- Document PKs beyond id columns  
2. **Expand FK coverage** \- More relationships for 20 tables  
3. **Populate schema\_nodes** \- Add table descriptions  
4. **Migrate acronyms** \- Move hardcoded to database  
5. **Unify database layer** \- SQLite support for hints loader

Want me to continue with any specific item, or shall I clear context now?

^^\*\*  
