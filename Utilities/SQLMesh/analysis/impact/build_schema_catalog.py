#!/usr/bin/env python3
"""
Schema Catalog Builder

Parses SQL Server DDL files and builds a schema_catalog table in SQLite
with column-level metadata for each table.

Columns:
  table_name       - Ground truth table name
  column_name      - Physical field name
  data_type        - DDL type (e.g., NVARCHAR(30), int, DECIMAL(14,2))
  is_nullable      - Whether the column allows NULL
  is_primary_key   - Whether the column is part of the PRIMARY KEY
  is_shadow_key    - Flag for Part/Vendor hash problem (NULL for now)
  semantic_concept - Link to the Concept node (NULL for now)

Usage:
    python build_schema_catalog.py
    python build_schema_catalog.py --ddl-dir ./output/live --db ./output/schema_catalog.db
    python build_schema_catalog.py --csv  (also emit CSV)
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Optional


CREATE_TABLE_PATTERN = re.compile(
    r'CREATE\s+TABLE\s+'
    r'(?:\[[^\]]+\]\.)?'
    r'(?:\[[^\]]+\]\.)?'
    r'\[(?P<Table>[^\]]+)\]',
    re.IGNORECASE
)

COLUMN_PATTERN = re.compile(
    r'^\s*\[(?P<col_name>[^\]]+)\]\s+'
    r'(?P<data_type>\w+(?:\([^)]*\))?)'
    r'(?P<rest>[^,]*)',
    re.IGNORECASE
)

PK_PATTERN = re.compile(
    r'PRIMARY\s+KEY\s*\((?P<pk_cols>[^)]+)\)',
    re.IGNORECASE
)


def parse_ddl_file(file_path: str) -> List[Dict[str, Optional[str]]]:
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    table_match = CREATE_TABLE_PATTERN.search(content)
    if not table_match:
        return []
    table_name = table_match.group('Table').strip()

    create_block_match = re.search(
        r'CREATE\s+TABLE\s+[^(]*\((.+?)\)\s*$',
        content, re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    if not create_block_match:
        return []
    block = create_block_match.group(1)

    pk_cols = set()
    for pk_match in PK_PATTERN.finditer(content):
        raw = pk_match.group('pk_cols')
        for col in raw.split(','):
            cleaned = col.strip().strip('[]')
            pk_cols.add(cleaned.upper())

    columns = []
    for line in block.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue

        m = COLUMN_PATTERN.match(line)
        if not m:
            continue

        col_name = m.group('col_name').strip()
        data_type = m.group('data_type').strip()
        rest = m.group('rest').upper()

        is_nullable = 'NOT NULL' not in rest

        columns.append({
            "table_name": table_name,
            "column_name": col_name,
            "data_type": data_type,
            "is_nullable": is_nullable,
            "is_primary_key": col_name.upper() in pk_cols,
            "is_shadow_key": None,
            "semantic_concept": None,
        })

    return columns


def build_catalog(ddl_dir: str) -> List[Dict]:
    sql_files = sorted(Path(ddl_dir).glob("*.sql"))
    if not sql_files:
        print(f"No .sql files in {ddl_dir}", file=sys.stderr)
        return []

    catalog = []
    for f in sql_files:
        cols = parse_ddl_file(str(f))
        catalog.extend(cols)

    return catalog


def write_sqlite(catalog: List[Dict], db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS schema_catalog")
    conn.execute("""
        CREATE TABLE schema_catalog (
            table_name       TEXT NOT NULL,
            column_name      TEXT NOT NULL,
            data_type        TEXT NOT NULL,
            is_nullable      BOOLEAN NOT NULL DEFAULT 1,
            is_primary_key   BOOLEAN NOT NULL DEFAULT 0,
            is_shadow_key    BOOLEAN,
            semantic_concept TEXT,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    conn.executemany("""
        INSERT INTO schema_catalog 
            (table_name, column_name, data_type, is_nullable, is_primary_key, is_shadow_key, semantic_concept)
        VALUES (:table_name, :column_name, :data_type, :is_nullable, :is_primary_key, :is_shadow_key, :semantic_concept)
    """, catalog)
    conn.commit()
    conn.close()


def write_csv_file(catalog: List[Dict], path: str):
    fieldnames = ["table_name", "column_name", "data_type", "is_nullable",
                  "is_primary_key", "is_shadow_key", "semantic_concept"]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(catalog)


def write_json_file(catalog: List[Dict], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)


def print_summary(catalog: List[Dict]):
    tables = set(c["table_name"] for c in catalog)
    nullable = sum(1 for c in catalog if c["is_nullable"])
    pk_count = sum(1 for c in catalog if c["is_primary_key"])

    print("\n" + "=" * 60)
    print("  SCHEMA CATALOG SUMMARY")
    print("=" * 60)
    print(f"  Tables:             {len(tables)}")
    print(f"  Total columns:      {len(catalog)}")
    print(f"  Primary key cols:   {pk_count}")
    print(f"  Nullable columns:   {nullable}")
    print(f"  NOT NULL columns:   {len(catalog) - nullable}")
    print()
    for t in sorted(tables):
        cols = [c for c in catalog if c["table_name"] == t]
        pks = [c["column_name"] for c in cols if c["is_primary_key"]]
        pk_str = f"  PK({', '.join(pks)})" if pks else ""
        print(f"  {t}: {len(cols)} columns{pk_str}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Build schema catalog from SQL Server DDL files"
    )
    parser.add_argument("--ddl-dir", default=None,
                        help="Directory with .sql DDL files (default: output/live)")
    parser.add_argument("--db", default=None,
                        help="SQLite output path (default: output/schema_catalog.db)")
    parser.add_argument("--csv", action="store_true",
                        help="Also emit CSV output")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Print summary")

    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ddl_dir = args.ddl_dir or os.path.join(script_dir, "output", "live")
    out_dir = os.path.join(script_dir, "output")
    os.makedirs(out_dir, exist_ok=True)
    db_path = args.db or os.path.join(out_dir, "schema_catalog.db")

    print(f"Parsing DDL files from: {ddl_dir}")
    catalog = build_catalog(ddl_dir)

    if not catalog:
        print("No columns extracted.", file=sys.stderr)
        sys.exit(1)

    write_sqlite(catalog, db_path)
    print(f"  SQLite: {db_path} ({len(catalog)} rows)")

    json_path = os.path.join(out_dir, "schema_catalog.json")
    write_json_file(catalog, json_path)
    print(f"  JSON:   {json_path}")

    if args.csv:
        csv_path = os.path.join(out_dir, "schema_catalog.csv")
        write_csv_file(catalog, csv_path)
        print(f"  CSV:    {csv_path}")

    if args.summary:
        print_summary(catalog)


if __name__ == "__main__":
    main()
