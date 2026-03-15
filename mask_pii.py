"""mask_pii.py - PII Masking Engine (MCP skill: masking_engine_001)

Applies tiered, perspective-aware PII masking via BFS-ordered hierarchy.
Targets the SQLMesh DuckDB database (Utilities/SQLMesh/db.db), raw schema.

Usage:
    python mask_pii.py --salt <GEMIN_SALT> [--perspective manufacturing|finance]
                       [--db-path <path>] [--bfs-path <json_file>]

Environment variable alternative:
    GEMIN_SALT=<value> python mask_pii.py
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

import duckdb
from faker import Faker

# Level 2: PII identifier columns to hash deterministically
PII_HASH_COLS = ["EmailAddress", "LoginName", "TaxID", "Username",
                 "email", "login_name", "tax_id", "username"]

# Level 3: Free-text columns to replace with Faker personas
FAKER_NAME_COLS = ["name", "full_name", "contact_name", "operator_name",
                   "customer_name", "vendor_name"]
FAKER_ADDR_COLS = ["Address", "address", "ship_to_address", "bill_to_address",
                   "delivery_address"]

LOG_PATH         = "Utilities/SQLMesh/analysis/impact/output/masking_log.json"
DEFAULT_DB_PATH  = "Utilities/SQLMesh/db.db"
DEFAULT_BFS_PATH = "Utilities/SQLMesh/analysis/impact/output/foreign_key_hierarchy.json"
TARGET_SCHEMA    = "raw"

fake = Faker()


def _hash(val, salt: str, n: int = 10) -> str:
    """Deterministic n-char SHA-256 hash. Matches SQL HASHBYTES logic."""
    if val is None:
        return None
    digest = hashlib.sha256(f"{val}{salt}".encode("utf-8")).hexdigest().upper()
    return digest[:n]


def _col_info(con, schema: str, table: str) -> dict:
    """Return {col_name: max_length} via DuckDB information_schema."""
    rows = con.execute(
        "SELECT column_name, character_maximum_length "
        "FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ?",
        [schema, table],
    ).fetchall()
    return {r[0]: (r[1] or 10) for r in rows}


def _tables_in_schema(con, schema: str) -> set:
    """Return set of table names in the given schema."""
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
        [schema],
    ).fetchall()
    return {r[0] for r in rows}


def mask_pii(gemin_salt: str, perspective: str, db_path: str, bfs_path: str) -> dict:
    """Execute tiered masking; return result dict for skill contract output."""
    if not os.path.exists(bfs_path):
        print(f"X BFS hierarchy not found: {bfs_path}")
        sys.exit(1)

    # Pre-mask backup
    backup_path = db_path + ".premask.bak"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Pre-mask backup: {backup_path}")

    with open(bfs_path) as f:
        hierarchy = json.load(f)

    con = duckdb.connect(db_path)
    live_tables = _tables_in_schema(con, TARGET_SCHEMA)

    log_entries = []
    tables_processed = 0
    print(f"[RUN] Tiered Masking - perspective={perspective}, schema={TARGET_SCHEMA}")

    # Build ordered table list: BFS hierarchy first, then any remaining live tables
    bfs_names = []
    for entry in hierarchy:
        t = (entry.get("child") or entry.get("table") or "").lower()
        if t and t in live_tables and t not in bfs_names:
            bfs_names.append(t)
    remaining = [t for t in sorted(live_tables) if t not in bfs_names]
    ordered_tables = bfs_names + remaining

    for table in ordered_tables:
        col_info  = _col_info(con, TARGET_SCHEMA, table)
        col_names = list(col_info.keys())

        if not col_names:
            continue

        hash_targets = [c for c in PII_HASH_COLS if c in col_names]
        name_targets = [c for c in FAKER_NAME_COLS if c in col_names]
        addr_targets = [c for c in FAKER_ADDR_COLS if c in col_names]

        if not (hash_targets or name_targets or addr_targets):
            print(f"  -> {table}: no PII columns - skipped")
            continue

        rows = con.execute(f"SELECT * FROM {TARGET_SCHEMA}.{table}").fetchall()
        if not rows:
            print(f"  -> {table}: empty - skipped")
            continue

        desc_cols = [d[0] for d in con.description]
        anchor = "id" if "id" in desc_cols else desc_cols[0]
        rows_updated = 0

        for row in rows:
            row_dict = dict(zip(desc_cols, row))
            row_id   = row_dict[anchor]
            set_parts = []
            params    = []

            for col in hash_targets:
                n = col_info.get(col, 10)
                set_parts.append(f"{col} = ?")
                params.append(_hash(row_dict[col], gemin_salt, n))

            for col in name_targets:
                set_parts.append(f"{col} = ?")
                params.append(fake.name())

            for col in addr_targets:
                set_parts.append(f"{col} = ?")
                params.append(fake.address().replace("\n", ", "))

            if set_parts:
                params.append(row_id)
                con.execute(
                    f"UPDATE {TARGET_SCHEMA}.{table} SET {', '.join(set_parts)} WHERE {anchor} = ?",
                    params,
                )
                rows_updated += 1

        if rows_updated > 0:
            tables_processed += 1
            log_entries.append({
                "table": table, "schema": TARGET_SCHEMA,
                "rows_updated": rows_updated, "perspective": perspective,
                "pii_cols_masked": hash_targets + name_targets + addr_targets,
            })
        print(f"  [OK] {table}: {rows_updated} rows updated")

    con.close()

    result = {
        "status": "success",
        "perspective": perspective,
        "tables_processed": tables_processed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backup": backup_path,
        "log": log_entries,
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[OK] Masking log -> {LOG_PATH}")
    print(f"[OK] Tiered Masking Complete - {tables_processed} table(s) modified.")
    return result


def _parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="PII Masking Engine (masking_engine_001)")
    parser.add_argument("--salt", dest="gemin_salt",
                        default=os.environ.get("GEMIN_SALT"),
                        help="Cryptographic salt (or set GEMIN_SALT env var)")
    parser.add_argument("--perspective", default="manufacturing",
                        choices=["manufacturing", "finance"])
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--bfs-path", default=DEFAULT_BFS_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if not args.gemin_salt:
        print("X gemin_salt is required. Use --salt or GEMIN_SALT env var.")
        sys.exit(1)
    mask_pii(
        gemin_salt=args.gemin_salt,
        perspective=args.perspective,
        db_path=args.db_path,
        bfs_path=args.bfs_path,
    )
