# Schema folder

This folder contains canonical schema artifacts separate from the Gradio UI.

Structure:

- `schema/tables/` - per-table JSON files containing DDL summary and `candidate_keys`.

How to generate metadata (local SQLite):

```bash
# Uses the local SQLite file by default. To target a different DB, set `DATABASE_URL`.
./.venv/bin/python scripts/generate_schema_metadata.py
```

The generator will inspect the database schema and write `schema/tables/<table>.json`.
Each JSON contains keys: `table`, `columns`, `primary_keys`, and `candidate_keys`.
