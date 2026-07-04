# Place Certificate Files

## What & Why
Populate the `certificate_for_receiving/` folder with two provided files:
1. The `generate_certificate.py` generator script. It reads the masking matrix, probes the Vendor/Part (and related) tables on the `sql-lab-2` Staging server, and writes a versioned receiving certificate JSON into the same folder. This gives the receiving side a repeatable way to emit trust-boundary certificates tied to the masking matrix DAG.
2. An already-certified receiving certificate (`receiving_certificate_RECV-2026-05-28-003.json`). Once a certificate passes receiving (reaches `status: certified` across the `pre_stage_to_receiving` trust boundary), the file is allowed to live on disk so the downstream sqlMesh receiving agent can consume it. This file is an existing record — place it as-is.

## Done looks like
- A file exists at `certificate_for_receiving/generate_certificate.py` containing the attached script.
- A file exists at `certificate_for_receiving/receiving_certificate_RECV-2026-05-28-003.json` with the exact content of the attached certificate (content unchanged — it is a historical certified record).
- The script's masking-matrix path resolves to the file's real location in this repo (`certificate_for_receiving/masking_matrix.csv`), so it can find the CSV when run.
- Running `python certificate_for_receiving/generate_certificate.py` loads the matrix, attempts the SQL Server probe, and writes a `receiving_certificate_RECV-*.json` file (probe will report `failed`/`pending` when `sql-lab-2` is unreachable from this environment — that is expected outside the corporate network).

## Out of scope
- Wiring the script into CI or any workflow.
- Adding automated tests.
- Refactoring the hardcoded `CONNECTION_STRING` to environment variables / config management (the script carries a TODO for this, but it is not part of this request).
- Running the script against the live SQL Server.
- Editing the content of the provided certified certificate JSON (it is a fixed record).

## Steps
1. **Place the script** — Create `certificate_for_receiving/generate_certificate.py` with the exact content of the attached script file (drop the `_<timestamp>` suffix from the attachment filename).
2. **Place the certified certificate** — Create `certificate_for_receiving/receiving_certificate_RECV-2026-05-28-003.json` with the exact content of the attached certificate file (drop the `_<timestamp>` suffix). Do not modify its contents.
3. **Reconcile the masking-matrix path** — The attached script points `MASKING_MATRIX_PATH` at the repo root, but in this repo the CSV lives at `certificate_for_receiving/masking_matrix.csv` (the canonical location used by `masking_matrix.py` and `seed_masking_matrix.py`). Update the path so the script reads the CSV from its real location, and adjust the certificate's `masking_matrix_ref.file` value to match. Make no other behavioral changes to the script.

## Relevant files
- `certificate_for_receiving/masking_matrix.csv`
- `hf-space-inventory-sqlgen/masking_matrix.py:48`
- `replit_integrations/seed_masking_matrix.py`
