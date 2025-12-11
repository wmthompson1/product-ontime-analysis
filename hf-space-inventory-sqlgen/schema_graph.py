#!/usr/bin/env python3
"""
schema_graph.py - Build NetworkX graph from schema_edges table

Uses pre-defined table relationships from schema_edges rather than 
auto-discovering foreign keys (which SQLite doesn't enforce).
"""

import os
import sqlite3
import networkx as nx
from pathlib import Path


def get_db_path():
    """Get database path from DATABASE_URL or default"""
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "schema/manufacturing.db"


def load_tables(cursor):
    """Load all table names"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def load_edges_from_schema_edges(cursor):
    """Load edges from schema_edges table (pre-defined relationships)"""
    try:
        cursor.execute("""
            SELECT from_table, to_table, relationship_type, join_column, weight,
                   join_column_description, natural_language_alias, few_shot_example, context
            FROM schema_edges
            ORDER BY edge_id
        """)
        return cursor.fetchall()
    except sqlite3.OperationalError:
        print("Warning: schema_edges table not found")
        return []


def build_graph(tables, edges):
    """Build NetworkX DiGraph from tables and edges"""
    G = nx.DiGraph()
    
    for table in tables:
        G.add_node(table, type='table')
    
    for edge in edges:
        from_t, to_t, rel_type, join_col, weight = edge[:5]
        join_desc = edge[5] if len(edge) > 5 else None
        nl_alias = edge[6] if len(edge) > 6 else None
        few_shot = edge[7] if len(edge) > 7 else None
        context = edge[8] if len(edge) > 8 else None
        
        G.add_edge(
            from_t, to_t,
            relationship=rel_type,
            join_column=join_col,
            weight=weight or 1,
            join_column_description=join_desc,
            natural_language_alias=nl_alias,
            few_shot_example=few_shot,
            context=context
        )
    
    return G


def main():
    db_path = get_db_path()
    print(f"Database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = load_tables(cursor)
    print(f"\nFound tables:")
    for t in tables:
        print(f" - {t}")
    print(f"Total tables: {len(tables)}")
    
    edges = load_edges_from_schema_edges(cursor)
    print(f"\nLoaded {len(edges)} edges from schema_edges table:")
    for edge in edges:
        print(f" - {edge[0]} --[{edge[2]}]--> {edge[1]} (on {edge[3]})")
    
    conn.close()
    
    G = build_graph(tables, edges)
    print(f"\nGraph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "schema.graphml"
    nx.write_graphml(G, output_path)
    print(f"\nWrote graph to: {output_path}")
    
    if G.number_of_edges() > 0:
        print("\nSample path test:")
        try:
            undirected = G.to_undirected()
            nodes = list(G.nodes())
            if len(nodes) >= 2:
                path = nx.shortest_path(undirected, nodes[0], nodes[-1])
                print(f"  {nodes[0]} → {nodes[-1]}: {' → '.join(path)}")
        except nx.NetworkXNoPath:
            print("  No path found between test nodes")


if __name__ == "__main__":
    main()
