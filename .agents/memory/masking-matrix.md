---
name: Masking matrix (column-masking DAG)
description: How the masking_matrix feature relates to schema, salt, and the CSV↔SQLite sync; what NOT to assume.
---

- The masking matrix (root CSV `certificate_for_receiving/masking_matrix.csv` ↔ SQLite `masking_matrix` table) is SEPARATE from `column_masking_policies` (the SME strategy tab). Both coexist by design; never collapse one into the other.
- Its rows name columns (e.g. vendor.id, part.pref_vendor, user_def_fields) from the PRIVATE SQL Server schema (the synthetic twin's source), NOT this public SQLite twin — those tables/columns do not exist in `manufacturing.db`.
  **Why:** public/private repo duality. **How to apply:** do NOT try to resolve the `length` (schema width) in `hash_sha256(col,length)` against local `manufacturing.db`; `length` is a caller-supplied parameter resolved against the real schema at masking-apply time.
- Masking salt lives only in the env/secret flow under `GEMIN_SALT` (overridable via `MASK_SALT_ENV`), confirmed by the user. Never stored in CSV/DB/code. `hash_sha256` raises rather than masking unsalted; output = uppercase SHA-256(value+salt) truncated to `length` (the schema width); None/"" pass through.
- CSV→SQLite sync is upsert-only, keyed on `dag_no` (runs on every app boot via the lazy `get_db_engine`→`init_sqlite_db` path, wrapped so a missing/bad CSV never blocks boot).
  **Why:** simplicity + idempotent startup. **How to apply:** deleting a row from the CSV does NOT delete it from SQLite, and `replit_integrations/seed_masking_matrix.py --export` will resurrect a deleted row from the table back into the CSV. To truly remove a row, delete from SQLite first, then `--export`.
