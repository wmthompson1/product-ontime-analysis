#!/usr/bin/env python3
"""
persist_to_arango.py - Persist NetworkX schema graph to local ArangoDB

Uses python-dotenv for safe credential loading.
Requires: nx-arangodb, python-arango, python-dotenv, networkx

Usage:
    ./.venv/bin/python scripts/persist_to_arango.py
    
Environment variables (in .env):
    DATABASE_HOST      - ArangoDB host (default: http://localhost:8529)
    DATABASE_USERNAME  - ArangoDB username (default: root)
    DATABASE_PASSWORD  - ArangoDB password
    DATABASE_NAME      - Target database name (default: manufacturing_graphs)
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv not installed")
    print("Run: pip install python-dotenv")
    sys.exit(1)

load_dotenv()

try:
    import networkx as nx
    from arango.client import ArangoClient
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("Run: pip install -r requirements-arango.txt")
    sys.exit(1)

HAS_NX_ARANGO = False
try:
    import nx_arangodb
    HAS_NX_ARANGO = True
except ImportError:
    pass


def get_config():
    """Load configuration from environment"""
    config = {
        'host': os.getenv('DATABASE_HOST', 'http://localhost:8529'),
        'username': os.getenv('DATABASE_USERNAME', 'root'),
        'password': os.getenv('DATABASE_PASSWORD', ''),
        'database': os.getenv('DATABASE_NAME', 'manufacturing_graphs'),
    }
    
    if not config['password']:
        print("Warning: DATABASE_PASSWORD not set in .env")
    
    return config


def load_schema_graph_from_sqlite(db_path: str | None = None) -> nx.DiGraph:
    """Load schema graph from SQLite schema_edges table"""
    import sqlite3
    
    if db_path is None:
        db_path = os.getenv('SQLITE_DATABASE', 'schema/manufacturing.db')
    
    print(f"Loading graph from SQLite: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    G = nx.DiGraph()
    
    cursor.execute("""
        SELECT from_table, to_table, relationship_type, join_column, weight,
               join_column_description, natural_language_alias, few_shot_example, context
        FROM schema_edges
        ORDER BY edge_id
    """)
    edges = cursor.fetchall()
    
    for edge in edges:
        from_t, to_t, rel_type, join_col, weight = edge[:5]
        G.add_edge(
            from_t, to_t,
            relationship=rel_type,
            join_column=join_col,
            weight=weight or 1,
            join_column_description=edge[5] if len(edge) > 5 else '',
            natural_language_alias=edge[6] if len(edge) > 6 else '',
            few_shot_example=edge[7] if len(edge) > 7 else '',
            context=edge[8] if len(edge) > 8 else ''
        )
    
    conn.close()
    
    print(f"Loaded graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def persist_with_nx_arangodb(G: nx.DiGraph, config: dict, graph_name: str):
    """Persist using nx-arangodb library"""
    if not HAS_NX_ARANGO:
        raise ImportError("nx-arangodb not installed")
    
    from nx_arangodb import ArangoDBConfig, ArangoDBGraphPersistence  # type: ignore
    
    arango_config = ArangoDBConfig(
        host=config['host'],
        username=config['username'],
        password=config['password'],
        database=config['database']
    )
    
    persistence = ArangoDBGraphPersistence(arango_config)
    
    adb_graph = persistence.persist_graph(
        graph=G,
        name=graph_name,
        write_batch_size=10000,
        overwrite=True
    )
    
    return adb_graph


def persist_manual(G: nx.DiGraph, config: dict, graph_name: str):
    """Manual persistence using python-arango directly"""
    client = ArangoClient(hosts=config['host'])
    
    sys_db = client.db('_system', username=config['username'], password=config['password'])
    
    if not sys_db.has_database(config['database']):
        sys_db.create_database(config['database'])
        print(f"Created database: {config['database']}")
    
    db = client.db(config['database'], username=config['username'], password=config['password'])
    
    nodes_collection = f"{graph_name}_nodes"
    edges_collection = f"{graph_name}_edges"
    
    if db.has_collection(nodes_collection):
        db.delete_collection(nodes_collection)
    if db.has_collection(edges_collection):
        db.delete_collection(edges_collection)
    
    nodes_col = db.create_collection(nodes_collection)
    edges_col = db.create_collection(edges_collection, edge=True)
    
    for node, data in G.nodes(data=True):
        doc = {'_key': str(node), 'name': str(node)}
        doc.update({k: v for k, v in data.items() if v is not None})
        nodes_col.insert(doc)
    
    for from_node, to_node, data in G.edges(data=True):
        doc = {
            '_from': f"{nodes_collection}/{from_node}",
            '_to': f"{nodes_collection}/{to_node}",
        }
        doc.update({k: v for k, v in data.items() if v is not None})
        edges_col.insert(doc)
    
    print(f"Persisted to collections: {nodes_collection}, {edges_collection}")
    return True


def main():
    print("=" * 60)
    print("Persist NetworkX Schema Graph to ArangoDB")
    print("=" * 60)
    
    config = get_config()
    print(f"\nArangoDB Host: {config['host']}")
    print(f"Database: {config['database']}")
    print(f"Username: {config['username']}")
    
    G = load_schema_graph_from_sqlite()
    
    if G.number_of_edges() == 0:
        print("\nError: No edges found in schema_edges table")
        print("Run schema_graph.py first to populate the table")
        sys.exit(1)
    
    graph_name = "manufacturing_schema_v1"
    
    print(f"\nPersisting graph as: {graph_name}")
    
    try:
        if HAS_NX_ARANGO:
            persist_with_nx_arangodb(G, config, graph_name)
        else:
            persist_manual(G, config, graph_name)
        
        print("\n" + "=" * 60)
        print("Graph persisted successfully to ArangoDB!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError persisting graph: {e}")
        print("\nTroubleshooting:")
        print("1. Is ArangoDB running? Check: http://localhost:8529")
        print("2. Are credentials correct in .env?")
        print("3. Is network accessible?")
        sys.exit(1)


if __name__ == "__main__":
    main()
