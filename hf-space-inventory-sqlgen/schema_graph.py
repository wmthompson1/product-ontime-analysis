#!/usr/bin/env python3
"""Load tables and foreign-key edges from SQLite into a NetworkX graph.

Usage:
  DATABASE_URL="sqlite:///data/manufacturing_analytics.sqlite3" \
    ./.venv/bin/python hf-space-inventory-sqlgen/schema_graph.py

The script prints a summary and writes `data/schema.graphml` if NetworkX is available.
"""
import os
import sqlite3
import sys

DB_ENV = os.environ.get("DATABASE_URL", "sqlite:///data/manufacturing_analytics.sqlite3")

def sqlite_path_from_url(url: str) -> str:
    # support sqlite:///path/to/db
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return url


def build_graph(conn):
    try:
        import networkx as nx
    except Exception:
        nx = None

    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tables = [r[0] for r in cur.fetchall()]

    edges = []
    for tbl in tables:
        try:
            cur.execute(f"PRAGMA foreign_key_list('{tbl}')")
            fks = cur.fetchall()
            # pragma returns: id, seq, table, from, to, on_update, on_delete, match
            for fk in fks:
                ref_table = fk[2]
                from_col = fk[3]
                to_col = fk[4]
                edges.append((tbl, ref_table, from_col, to_col))
        except sqlite3.OperationalError:
            continue

    # Print summary
    print("Found tables:")
    for t in tables:
        print(" -", t)
    print(f"Total tables: {len(tables)}")

    if edges:
        print("\nForeign key edges:")
        for src, dst, fcol, tcol in edges:
            print(f" - {src} -> {dst}    ({fcol} -> {tcol})")
    else:
        print("\nNo foreign key edges discovered.")

    if nx is None:
        print("\nNetworkX not available. Install it with: '.venv/bin/pip install networkx' to save graph files.")
        return

    G = nx.DiGraph()
    for t in tables:
        G.add_node(t)
    for src, dst, fcol, tcol in edges:
        G.add_edge(src, dst, from_col=fcol, to_col=tcol)

    out_path = os.path.join("data", "schema.graphml")
    try:
        nx.write_graphml(G, out_path)
        print(f"\nWrote graph to: {out_path}")
    except Exception as e:
        print(f"Failed to write graph file: {e}")


def main():
    db_path = sqlite_path_from_url(DB_ENV)
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        sys.exit(2)

    conn = sqlite3.connect(db_path)
    try:
        build_graph(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
