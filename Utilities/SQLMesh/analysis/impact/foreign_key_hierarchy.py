#!/usr/bin/env python3
"""
Foreign Key Hierarchy Builder

Reads the foreign_key_index.csv produced by foreign_key_iterator.py and builds
a parent-child hierarchy index using BFS traversal from root tables (tables that
are referenced but never reference others).

Outputs:
  - CSV hierarchy index with Level, Parent, Child, Columns
  - DOT graph with color-coded depth levels

Usage:
    python foreign_key_hierarchy.py
    python foreign_key_hierarchy.py --fk-csv ./output/foreign_key_index.csv
    python foreign_key_hierarchy.py --fk-csv ./output/foreign_key_index.csv --output-dir ./results
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple


LEVEL_COLORS = [
    "#2196F3", "#4CAF50", "#FF9800", "#E91E63",
    "#9C27B0", "#00BCD4", "#795548", "#607D8B",
    "#F44336", "#3F51B5", "#CDDC39", "#FF5722",
]


def read_fk_edges(csv_path: str) -> List[Dict[str, str]]:
    edges = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            edges.append({
                "from_table": row["from_table"].strip(),
                "from_columns": row["from_columns"].strip(),
                "to_table": row["to_table"].strip(),
                "to_columns": row["to_columns"].strip(),
            })
    return edges


def build_hierarchy(edges: List[Dict[str, str]]) -> List[Dict]:
    children_of: Dict[str, List[Dict]] = defaultdict(list)
    from_tables: Set[str] = set()
    to_tables: Set[str] = set()

    for e in edges:
        children_of[e["to_table"]].append(e)
        from_tables.add(e["from_table"])
        to_tables.add(e["to_table"])

    roots = sorted(to_tables - from_tables)

    if not roots:
        all_tables = from_tables | to_tables
        ref_count = defaultdict(int)
        for e in edges:
            ref_count[e["to_table"]] += 1
        roots = sorted(all_tables, key=lambda t: -ref_count.get(t, 0))[:3]

    hierarchy = []
    visited: Set[str] = set()
    queue: deque = deque()

    for root in roots:
        queue.append((root, 0, None, "", ""))
        visited.add(root)

    while queue:
        table, level, parent, from_cols, to_cols = queue.popleft()

        hierarchy.append({
            "level": level,
            "parent": parent or "(root)",
            "child": table,
            "fk_columns": from_cols,
            "referenced_columns": to_cols,
        })

        for edge in sorted(children_of.get(table, []), key=lambda e: e["from_table"]):
            child = edge["from_table"]
            if child not in visited:
                visited.add(child)
                queue.append((child, level + 1, table,
                              edge["from_columns"], edge["to_columns"]))

    orphan_tables = (from_tables | to_tables) - visited
    for t in sorted(orphan_tables):
        hierarchy.append({
            "level": -1,
            "parent": "(orphan)",
            "child": t,
            "fk_columns": "",
            "referenced_columns": "",
        })

    return hierarchy


def write_hierarchy_csv(hierarchy: List[Dict], path: str):
    fieldnames = ["level", "parent", "child", "fk_columns", "referenced_columns"]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(hierarchy)


def write_hierarchy_json(hierarchy: List[Dict], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)


def write_hierarchy_dot(hierarchy: List[Dict], edges: List[Dict], path: str):
    table_level: Dict[str, int] = {}
    for h in hierarchy:
        if h["level"] >= 0:
            table_level[h["child"]] = h["level"]

    max_level = max((h["level"] for h in hierarchy if h["level"] >= 0), default=0)

    lines = [
        'digraph ForeignKeyHierarchy {',
        '    rankdir=TB;',
        '    node [shape=box, style="filled,rounded", fontname="Arial"];',
        '    edge [color="#666666"];',
        '',
    ]

    for level in range(max_level + 1):
        tables_at_level = sorted(t for t, l in table_level.items() if l == level)
        if tables_at_level:
            color = LEVEL_COLORS[level % len(LEVEL_COLORS)]
            lines.append(f'    // Level {level}')
            for t in tables_at_level:
                lines.append(f'    "{t}" [fillcolor="{color}", '
                             f'label="{t}\\nL{level}"];')
            lines.append('')

    orphans = [h["child"] for h in hierarchy if h["level"] == -1]
    if orphans:
        lines.append('    // Orphans')
        for t in orphans:
            lines.append(f'    "{t}" [fillcolor="#EEEEEE", style="filled,dashed"];')
        lines.append('')

    seen_edges: Set[Tuple[str, str]] = set()
    for e in edges:
        edge_key = (e["from_table"], e["to_table"])
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            lines.append(f'    "{e["from_table"]}" -> "{e["to_table"]}";')

    lines.append('}')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def print_tree(hierarchy: List[Dict]):
    print("\n" + "=" * 70)
    print("  FOREIGN KEY HIERARCHY (BFS traversal from root tables)")
    print("=" * 70)

    max_level = max((h["level"] for h in hierarchy if h["level"] >= 0), default=0)

    for level in range(max_level + 1):
        entries = [h for h in hierarchy if h["level"] == level]
        if not entries:
            continue
        print(f"\n  Level {level}:")
        for h in entries:
            indent = "    " + "  " * level
            if h["parent"] == "(root)":
                print(f"{indent}📦 {h['child']}  (root table)")
            else:
                print(f"{indent}└─ {h['child']}  ← FK({h['fk_columns']}) → {h['parent']}")

    orphans = [h for h in hierarchy if h["level"] == -1]
    if orphans:
        print(f"\n  Orphans (in cycles or disconnected):")
        for h in orphans:
            print(f"    ⚠  {h['child']}")

    level_counts = defaultdict(int)
    for h in hierarchy:
        if h["level"] >= 0:
            level_counts[h["level"]] += 1

    print(f"\n  Depth: {max_level + 1} levels, {len(hierarchy)} total entries")
    for lvl in sorted(level_counts):
        print(f"    Level {lvl}: {level_counts[lvl]} tables")
    if orphans:
        print(f"    Orphans: {len(orphans)} tables")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Build parent-child hierarchy from foreign key index"
    )
    parser.add_argument("--fk-csv", default=None,
                        help="Path to foreign_key_index.csv (default: reports/impact/foreign_key_index.csv)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory (default: same as fk-csv directory)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress tree output")

    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_csv = os.path.join(script_dir, "..", "reports", "impact", "foreign_key_index.csv")

    fk_csv = args.fk_csv or default_csv
    if not os.path.exists(fk_csv):
        print(f"Error: FK index not found: {fk_csv}", file=sys.stderr)
        print("Run foreign_key_iterator.py first to generate it.", file=sys.stderr)
        sys.exit(1)

    out_dir = args.output_dir or os.path.dirname(fk_csv)
    os.makedirs(out_dir, exist_ok=True)

    print(f"Reading FK index: {fk_csv}")
    edges = read_fk_edges(fk_csv)
    print(f"Loaded {len(edges)} FK edges")

    hierarchy = build_hierarchy(edges)

    csv_path = os.path.join(out_dir, "foreign_key_hierarchy.csv")
    json_path = os.path.join(out_dir, "foreign_key_hierarchy.json")
    dot_path = os.path.join(out_dir, "foreign_key_hierarchy.dot")

    write_hierarchy_csv(hierarchy, csv_path)
    write_hierarchy_json(hierarchy, json_path)
    write_hierarchy_dot(hierarchy, edges, dot_path)

    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  DOT:  {dot_path}")

    if not args.quiet:
        print_tree(hierarchy)


if __name__ == "__main__":
    main()
