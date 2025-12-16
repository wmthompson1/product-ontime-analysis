#!/usr/bin/env python3
"""
Try persisting to Arango; on connectivity failure, export GraphML and write schema_edges to SQLite.
Usage:
  python scripts/persist_with_fallback.py --graph-path data/schema.graphml --sqlite-fallback data/dev_schema.db
"""
from __future__ import annotations
import argparse
import sys
import os
import traceback
import sqlite3
import json
import networkx as nx

# import your existing persist function; adjust import to actual module
try:
    from scripts.persist_to_arango import persist_graph_to_arango  # you may need to adapt this import
except Exception:
    persist_graph_to_arango = None

from arango.exceptions import ArangoClientError, ConnectionAbortedError

def write_graphml(G: nx.Graph, path: str):
    nx.write_graphml(G, path)
    print(f"Wrote GraphML to {path}")

def write_schema_edges_sqlite(G: nx.DiGraph, sqlite_path: str):
    # create or append schema_edges table: source, target, child_column, parent_column, attrs (JSON)
    if os.path.exists(sqlite_path) and os.path.getsize(sqlite_path) > 0:
        conn = sqlite3.connect(sqlite_path)
    else:
        conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        child_column TEXT,
        parent_column TEXT,
        attrs TEXT
    )""")
    conn.commit()

    for u, v, attrs in G.edges(data=True):
        child = attrs.get("child_column") or attrs.get("child") or attrs.get("from")
        parent = attrs.get("parent_column") or attrs.get("parent") or attrs.get("to")
        extra = {k: v for k, v in attrs.items() if k not in ("child_column","parent_column","child","parent","from","to")}
        cur.execute("INSERT INTO schema_edges (source,target,child_column,parent_column,attrs) VALUES (?,?,?,?,?)",
                    (str(u), str(v), child, parent, json.dumps(extra)))
    conn.commit()
    conn.close()
    print(f"Wrote {G.number_of_edges()} edges to SQLite {sqlite_path}")

def load_graph(graph_path):
    if os.path.exists(graph_path):
        return nx.read_graphml(graph_path)
    # alternatively, if you have networkx graph in memory builder code, call that
    raise FileNotFoundError(graph_path)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--graph-path", default="data/schema.graphml")
    p.add_argument("--sqlite-fallback", default="data/dev_schema.db")
    p.add_argument("--try-arango", action="store_true", help="Attempt Arango persist first (requires persist_graph_to_arango)")
    args = p.parse_args()

    G = load_graph(args.graph_path)

    # Try Arango
    if args.try_arango and persist_graph_to_arango:
        try:
            print("Attempting to persist to Arango...")
            persist_graph_to_arango(G)  # adapt signature as needed
            print("Persist to Arango succeeded.")
            return
        except Exception as e:
            print("Arango persist failed:", e)
            traceback.print_exc()
            # if it's clearly a connection error, fall back
    else:
        print("Skipping Arango attempt (either disabled or persist function not found).")

    # Fallback: write graphml and sqlite table
    print("Falling back: export GraphML and populate SQLite schema_edges")
    write_graphml(G, args.graph_path)
    write_schema_edges_sqlite(G, args.sqlite_fallback)

if __name__ == "__main__":
    main()