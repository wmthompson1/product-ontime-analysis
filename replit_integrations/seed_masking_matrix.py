"""Seed / sync the column-masking DAG matrix (root CSV ↔ SQLite ``masking_matrix``).

The matrix lives in two places that stay in sync:

  - the human-editable CSV at ``certificate_for_receiving/masking_matrix.csv``
  - the SQLite ``masking_matrix`` table

This script is the head-less entry point for keeping them in agreement (the app
also loads the CSV into SQLite on every startup):

  - default:   ensure the CSV exists (recreate it from the curated default if it
               was deleted), then load it into SQLite (idempotent upsert).
  - --export:  write the current SQLite table back out to the CSV (DAG order),
               so programmatic edits to the table are reflected in the CSV.

The matrix is distinct from ``column_masking_policies`` (the SME strategy tab) —
they live side by side. No LLM is involved.
"""
import argparse
import os
import sys

_HF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen",
)
if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)

DB_PATH = os.path.join(_HF_DIR, "app_schema", "manufacturing.db")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed / sync the masking matrix between the root CSV and SQLite.",
    )
    parser.add_argument(
        "--export", action="store_true",
        help="Write the current SQLite masking_matrix table back out to the CSV "
             "(instead of loading the CSV into SQLite).",
    )
    args = parser.parse_args(argv)

    from masking_matrix import (
        DEFAULT_CSV_PATH,
        export_matrix_to_csv,
        load_matrix_from_csv,
        write_default_csv,
    )

    if not os.path.exists(DB_PATH):
        raise SystemExit(f"ERROR: manufacturing.db not found at {DB_PATH}")

    if args.export:
        written = export_matrix_to_csv(db_path=DB_PATH, csv_path=DEFAULT_CSV_PATH)
        print(f"exported {written} matrix row(s) to {DEFAULT_CSV_PATH}")
        return 0

    if not os.path.exists(DEFAULT_CSV_PATH):
        created = write_default_csv(DEFAULT_CSV_PATH)
        print(f"created masking matrix CSV with {created} default row(s) at "
              f"{DEFAULT_CSV_PATH}")

    res = load_matrix_from_csv(csv_path=DEFAULT_CSV_PATH, db_path=DB_PATH)
    if not res.get("ok"):
        raise SystemExit(f"ERROR: failed to load matrix: {res.get('error')}")
    print(f"synced {res.get('loaded', 0)} matrix row(s) from CSV into SQLite "
          f"(idempotent).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
