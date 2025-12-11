#!/usr/bin/env python3
"""Local equivalent of Entry Point 018: build NetworkX graph from local SQLite schema tables.

Writes `data/schema_018.graphml` and prints a summary.
"""
import os
import sqlite3
import networkx as nx

DB = os.environ.get('DATABASE_URL', 'sqlite:///data/manufacturing_analytics.sqlite3')

def sqlite_path(url: str) -> str:
    if url.startswith('sqlite:///'):
        return url[len('sqlite:///'):]
    if url.startswith('sqlite://'):
        return url[len('sqlite://'):]
    return url

def main():
    dbpath = sqlite_path(DB)
    if not os.path.isabs(dbpath):
        dbpath = os.path.join(os.getcwd(), dbpath)
    if not os.path.exists(dbpath):
        print('DB file not found:', dbpath); return

    conn = sqlite3.connect(dbpath)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Read nodes
    nodes = []
    try:
        cur.execute("SELECT table_name, table_type, description FROM schema_nodes")
        nodes = cur.fetchall()
    except sqlite3.OperationalError:
        print('No schema_nodes table found; proceeding without nodes')

    # Read edges
    edges = []
    try:
        cur.execute("SELECT from_table, to_table, relationship_type, join_column, weight FROM schema_edges")
        edges = cur.fetchall()
    except sqlite3.OperationalError:
        print('No schema_edges table found; aborting')

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n['table_name'], table_type=n['table_type'], description=n['description'])

    for e in edges:
        G.add_edge(e['from_table'], e['to_table'], relationship=e['relationship_type'], join_column=e['join_column'], weight=e['weight'])

    print(f'Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')

    out = os.path.join('data', 'schema_018.graphml')
    try:
        nx.write_graphml(G, out)
        print('Wrote graph to', out)
    except Exception as exc:
        print('Failed to write graph:', exc)

    conn.close()

if __name__ == '__main__':
    main()
