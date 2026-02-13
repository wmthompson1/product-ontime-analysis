#!/usr/bin/env python3
"""
Foreign Key Iterator for SQL Server DDL Files

Scans a directory of SQL Server DDL files (.sql) and extracts all foreign key
references using two patterns:
  1. ALTER TABLE ... FOREIGN KEY ... REFERENCES  (explicit FK constraints)
  2. Inline column REFERENCES                    (column-level FK declarations)

Outputs:
  - CSV index of all FK relationships
  - JSON index (same data)
  - DOT graph file for Graphviz visualization

Usage:
    python foreign_key_iterator.py <ddl_directory>
    python foreign_key_iterator.py <ddl_directory> --output-dir ./results
    python foreign_key_iterator.py <ddl_directory> --summary
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set


FK_ALTER_PATTERN = re.compile(
    r'ALTER\s+TABLE\s+'
    r'(?:\[[^\]]+\]\.)?'
    r'(?:\[[^\]]+\]\.)?'
    r'\[(?P<FromTable>[^\]]+)\]'
    r'.*?'
    r'FOREIGN\s+KEY\s*\((?P<FromCols>[^)]+)\)'
    r'.*?'
    r'REFERENCES\s+'
    r'(?:\[[^\]]+\]\.)?'
    r'(?:\[[^\]]+\]\.)?'
    r'\[(?P<ToTable>[^\]]+)\]'
    r'\s*(?:\((?P<ToCols>[^)]+)\))?',
    re.IGNORECASE | re.DOTALL
)

FK_INLINE_PATTERN = re.compile(
    r'\[(?P<ColName>[^\]]+)\]\s+[^,\r\n]+?\s+'
    r'REFERENCES\s+'
    r'(?:\[[^\]]+\]\.)?'
    r'(?:\[[^\]]+\]\.)?'
    r'\[(?P<ToTable>[^\]]+)\]'
    r'\s*(?:\((?P<ToCols>[^)]+)\))?',
    re.IGNORECASE | re.DOTALL
)

CREATE_TABLE_PATTERN = re.compile(
    r'CREATE\s+TABLE\s+'
    r'(?:\[[^\]]+\]\.)?'
    r'(?:\[[^\]]+\]\.)?'
    r'\[(?P<Table>[^\]]+)\]',
    re.IGNORECASE
)

CONSTRAINT_NAME_PATTERN = re.compile(
    r'CONSTRAINT\s+\[(?P<ConstraintName>[^\]]+)\]\s+FOREIGN\s+KEY',
    re.IGNORECASE
)


def _clean_columns(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r'\[|\]', '', raw)
    return ', '.join(c.strip() for c in cleaned.split(','))


def extract_fk_from_file(file_path: str) -> List[Dict[str, str]]:
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    entries = []

    for m in FK_ALTER_PATTERN.finditer(content):
        constraint_region = content[max(0, m.start() - 200):m.start() + len(m.group())]
        cm = CONSTRAINT_NAME_PATTERN.search(constraint_region)
        constraint_name = cm.group('ConstraintName') if cm else ""

        entries.append({
            "source_file": os.path.basename(file_path),
            "constraint_name": constraint_name,
            "from_table": m.group('FromTable').strip(),
            "from_columns": _clean_columns(m.group('FromCols')),
            "to_table": m.group('ToTable').strip(),
            "to_columns": _clean_columns(m.group('ToCols') or ""),
            "match_type": "ALTER_TABLE_FK"
        })

    for m in FK_INLINE_PATTERN.finditer(content):
        preceding = content[max(0, m.start() - 120):m.start()].upper()
        if 'FOREIGN KEY' in preceding or 'ALTER TABLE' in preceding or 'CONSTRAINT' in preceding:
            continue

        create_m = CREATE_TABLE_PATTERN.search(content)
        from_table = create_m.group('Table').strip() if create_m else Path(file_path).stem

        entries.append({
            "source_file": os.path.basename(file_path),
            "constraint_name": "",
            "from_table": from_table,
            "from_columns": m.group('ColName').strip(),
            "to_table": m.group('ToTable').strip(),
            "to_columns": _clean_columns(m.group('ToCols') or ""),
            "match_type": "INLINE_REFERENCE"
        })

    return entries


def deduplicate(entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: Set[tuple] = set()
    unique = []
    for e in entries:
        key = (e["from_table"], e["from_columns"], e["to_table"], e["to_columns"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return sorted(unique, key=lambda x: (x["from_table"], x["from_columns"], x["to_table"]))


def write_csv(entries: List[Dict[str, str]], path: str):
    fieldnames = ["source_file", "constraint_name", "from_table", "from_columns",
                  "to_table", "to_columns", "match_type"]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)


def write_json(entries: List[Dict[str, str]], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)


def write_dot(entries: List[Dict[str, str]], path: str):
    lines = ['digraph ForeignKeyGraph {', '    rankdir=LR;',
             '    node [shape=box, style=filled, fillcolor="#E8F0FE"];', '']

    edges_seen = set()
    for e in entries:
        edge = (e["from_table"], e["to_table"])
        if edge not in edges_seen:
            edges_seen.add(edge)
            label = e["from_columns"]
            lines.append(f'    "{e["from_table"]}" -> "{e["to_table"]}" [label="{label}"];')

    lines.append('}')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def print_summary(entries: List[Dict[str, str]]):
    from_tables: Set[str] = set()
    to_tables: Set[str] = set()
    all_tables: Set[str] = set()
    files: Set[str] = set()
    alter_count = 0
    inline_count = 0

    for e in entries:
        from_tables.add(e["from_table"])
        to_tables.add(e["to_table"])
        all_tables.add(e["from_table"])
        all_tables.add(e["to_table"])
        files.add(e["source_file"])
        if e["match_type"] == "ALTER_TABLE_FK":
            alter_count += 1
        else:
            inline_count += 1

    ref_only = to_tables - from_tables
    leaf_only = from_tables - to_tables

    print("\n" + "=" * 60)
    print("  FOREIGN KEY EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"  Files scanned:           {len(files)}")
    print(f"  Total FK relations:      {len(entries)}")
    print(f"    ALTER TABLE style:     {alter_count}")
    print(f"    Inline REFERENCES:     {inline_count}")
    print(f"  Unique tables involved:  {len(all_tables)}")
    print(f"    Tables with outgoing:  {len(from_tables)}")
    print(f"    Tables referenced:     {len(to_tables)}")
    print(f"    Root tables (ref only):{len(ref_only)}")
    if ref_only:
        for t in sorted(ref_only):
            print(f"      - {t}")
    print(f"    Leaf tables (FK only): {len(leaf_only)}")
    if leaf_only:
        for t in sorted(leaf_only):
            print(f"      - {t}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract foreign key references from SQL Server DDL files"
    )
    parser.add_argument("ddl_path", nargs="?", default=None,
                        help="Directory containing .sql DDL files (default: output/live)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory (default: <ddl_path>/../output)")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Print a summary of findings")
    parser.add_argument("--csv", default="foreign_key_index.csv",
                        help="CSV output filename (default: foreign_key_index.csv)")
    parser.add_argument("--dot", default="foreign_key_graph.dot",
                        help="DOT graph output filename (default: foreign_key_graph.dot)")

    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ddl_path = os.path.abspath(args.ddl_path) if args.ddl_path else os.path.join(script_dir, "output", "live")

    if not os.path.isdir(ddl_path):
        print(f"Error: DDL directory not found: {ddl_path}", file=sys.stderr)
        sys.exit(1)

    sql_files = sorted(Path(ddl_path).glob("*.sql"))
    if not sql_files:
        print(f"No .sql files found in {ddl_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {len(sql_files)} SQL files in {ddl_path} ...")

    all_entries = []
    for sql_file in sql_files:
        fks = extract_fk_from_file(str(sql_file))
        all_entries.extend(fks)

    unique = deduplicate(all_entries)
    print(f"Found {len(all_entries)} FK references ({len(unique)} unique)")

    out_dir = args.output_dir or os.path.join(script_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    csv_path = os.path.join(out_dir, args.csv)
    json_path = os.path.join(out_dir, args.csv.replace('.csv', '.json'))
    dot_path = os.path.join(out_dir, args.dot)

    write_csv(unique, csv_path)
    write_json(unique, json_path)
    write_dot(unique, dot_path)

    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  DOT:  {dot_path}")

    if args.summary:
        print_summary(unique)


if __name__ == "__main__":
    main()
