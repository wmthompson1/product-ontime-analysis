#!/usr/bin/env python3
"""
Generate per-table schema metadata JSON files under `schema/tables/`.

Heuristic for `candidate_keys`:
- If table has PRIMARY KEY columns (sqlite PRAGMA), use them.
- Else, include columns that end with `_id` as candidates.

Run with the project's venv python. It reads `DATABASE_URL` env or defaults to
`data/manufacturing_analytics.sqlite3`.
"""
import os
import json
import sqlite3
from urllib.parse import urlparse

WORKDIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_DB = os.path.join(WORKDIR, "data", "manufacturing_analytics.sqlite3")
OUT_DIR = os.path.join(WORKDIR, "schema", "tables")


def get_sqlite_path_from_database_url(url: str) -> str:
    if not url:
        return DEFAULT_DB
    # Accept formats: sqlite:///path or sqlite:////absolute/path
    if url.startswith("sqlite:"):
        # remove sqlite: prefix
        parsed = url.split("sqlite:", 1)[1]
        # strip leading //
        parsed = parsed.lstrip('/')
        # if path contains ':' (windows), fallback
        return '/' + parsed if os.path.isabs('/' + parsed) else parsed
    return DEFAULT_DB


def list_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [r[0] for r in cur.fetchall()]


def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    cols = []
    pk_cols = []
    for cid, name, ctype, notnull, dflt_value, pk in cur.fetchall():
        cols.append({"name": name, "type": ctype, "notnull": bool(notnull), "default": dflt_value})
        if pk:
            pk_cols.append(name)
    return cols, pk_cols


def main():
    db_url = os.environ.get('DATABASE_URL')
    db_path = get_sqlite_path_from_database_url(db_url)
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)

    conn = sqlite3.connect(db_path)
    tables = list_tables(conn)
    for t in tables:
        cols, pk_cols = get_columns(conn, t)
        candidate_keys = pk_cols[:] if pk_cols else []
        if not candidate_keys:
            # heuristic: columns ending with _id
            candidate_keys = [c['name'] for c in cols if c['name'].endswith('_id')]

        meta = {
            "table": t,
            "columns": cols,
            "primary_keys": pk_cols,
            "candidate_keys": candidate_keys,
        }

        out_path = os.path.join(OUT_DIR, f"{t}.json")
        with open(out_path, 'w') as fh:
            json.dump(meta, fh, indent=2)
        print(f"Wrote {out_path}")

    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
