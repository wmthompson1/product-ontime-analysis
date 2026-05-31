"""
build_table_usage_index.py
──────────────────────────
Parse every ground-truth SQL file in app_schema/queries/ with SQLGlot,
count table references per query, and persist two artefacts:

  1. SQLite table  `ground_truth_table_usage`  (per-query, per-table counts)
  2. Updated       `app_schema/queries/index.json`  (table_usage per category)

Run:
    python scripts/build_table_usage_index.py
"""

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import sqlglot
from sqlglot import exp

QUERIES_DIR = Path(__file__).parent.parent / "app_schema" / "queries"
INDEX_JSON  = QUERIES_DIR / "index.json"
DB_PATH     = Path(__file__).parent.parent / "app_schema" / "manufacturing.db"

QUERY_NAME_RE = re.compile(
    r"--\s*Query\s+\d+\s*[—\-]+\s*(\S+)", re.IGNORECASE
)


def extract_tables(sql_text: str) -> list[str]:
    """Return all table names referenced in a SQL statement (SQLGlot parse)."""
    tables = []
    try:
        for stmt in sqlglot.parse(sql_text, dialect="sqlite"):
            if stmt is None:
                continue
            for node in stmt.walk():
                if isinstance(node, exp.Table) and node.name:
                    tables.append(node.name.lower())
    except Exception:
        pass
    return tables


def split_queries(sql_file_text: str) -> list[tuple[str, str]]:
    """
    Split a multi-query SQL file into (query_name, sql_text) pairs.
    Splits on the '-- Query N — name' comment blocks.
    """
    # Split on lines that look like a query header comment
    parts = re.split(r"(?m)^(--\s*={10,}.*?\n)", sql_file_text)
    # Reassemble: each query block starts at a header separator
    blocks: list[str] = []
    current: list[str] = []
    for part in parts:
        if re.match(r"--\s*={10,}", part):
            if current:
                blocks.append("".join(current))
            current = [part]
        else:
            current.append(part)
    if current:
        blocks.append("".join(current))

    result = []
    for block in blocks:
        name_match = QUERY_NAME_RE.search(block)
        query_name = name_match.group(1) if name_match else "unnamed"
        # Strip comment lines to get just the SQL
        sql_lines = [
            line for line in block.splitlines()
            if not line.strip().startswith("--")
        ]
        sql_text = "\n".join(sql_lines).strip()
        if sql_text:
            result.append((query_name, sql_text))
    return result


def main():
    index = json.loads(INDEX_JSON.read_text())
    category_map = {c["file"]: c["id"] for c in index.get("categories", [])}

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS ground_truth_table_usage (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            query_file      TEXT    NOT NULL,
            category_id     TEXT    NOT NULL,
            query_name      TEXT    NOT NULL,
            table_name      TEXT    NOT NULL,
            reference_count INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_gt_usage
            ON ground_truth_table_usage (category_id, query_name, table_name);

        DELETE FROM ground_truth_table_usage;
    """)

    all_tables_global: Counter = Counter()
    category_table_usage: dict[str, dict] = {}

    for sql_file in sorted(QUERIES_DIR.glob("*.sql")):
        file_name   = sql_file.name
        category_id = category_map.get(file_name, sql_file.stem)
        sql_text    = sql_file.read_text()

        queries = split_queries(sql_text)
        if not queries:
            queries = [("all", sql_text)]

        file_tables: Counter = Counter()
        per_query: list[dict] = []

        for query_name, q_sql in queries:
            tables = extract_tables(q_sql)
            counts = Counter(tables)
            file_tables.update(counts)
            all_tables_global.update(counts)

            for table_name, ref_count in counts.items():
                cur.execute(
                    """INSERT OR REPLACE INTO ground_truth_table_usage
                       (query_file, category_id, query_name, table_name, reference_count)
                       VALUES (?, ?, ?, ?, ?)""",
                    (file_name, category_id, query_name, table_name, ref_count),
                )
            per_query.append({
                "query_name": query_name,
                "tables": dict(counts),
            })

        category_table_usage[category_id] = {
            "file": file_name,
            "per_query": per_query,
            "totals": dict(file_tables),
        }
        print(f"  {file_name}: {len(queries)} queries, "
              f"{len(file_tables)} distinct tables → {dict(file_tables)}")

    conn.commit()
    conn.close()

    # ── Update index.json ────────────────────────────────────────────────────
    for cat in index.get("categories", []):
        usage = category_table_usage.get(cat["id"])
        if usage:
            cat["table_usage"] = usage

    # Global summary across all ground-truth SQL
    index["tables_referenced"] = sorted(all_tables_global.keys())
    index["table_reference_counts"] = {
        t: c for t, c in all_tables_global.most_common()
    }

    INDEX_JSON.write_text(json.dumps(index, indent=2))

    print(f"\nGlobal table reference counts (most used first):")
    for table, count in all_tables_global.most_common():
        print(f"  {table:<35} {count}")

    print(f"\nDone — {sum(all_tables_global.values())} total references across "
          f"{len(all_tables_global)} distinct tables written to SQLite + index.json")


if __name__ == "__main__":
    main()
