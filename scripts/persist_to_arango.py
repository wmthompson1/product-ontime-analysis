#!/usr/bin/env python3
"""
persist_to_arango.py - Persist NetworkX schema graph to local ArangoDB

Uses python-dotenv for safe credential loading.
Requires: nx-arangodb, python-arango, python-dotenv, networkx

Usage:
    ./.venv/bin/python scripts/persist_to_arango.py
    
Environment variables (in .env):
    ARANGO_HOST      - ArangoDB host (default: http://localhost:8529)
    ARANGO_USERNAME  - ArangoDB username (default: root)
    ARANGO_PASSWORD  - ArangoDB password
    ARANGO_DATABASE  - Target database name (default: manufacturing_graphs)
"""

import os
import sys
from pathlib import Path
import argparse

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
    # verify the expected API exists in this nx_arangodb version
    try:
        from nx_arangodb import ArangoDBConfig, ArangoDBGraphPersistence  # type: ignore
        HAS_NX_ARANGO = True
    except Exception:
        # older/newer nx_arangodb may have a different API; fall back to manual persist
        HAS_NX_ARANGO = False
except ImportError:
    HAS_NX_ARANGO = False


def get_config():
    """Load configuration from environment"""
    config = {
        # prefer explicit ARANGO_* but fall back to DATABASE_* entries for compatibility
        'host': os.getenv('ARANGO_HOST', os.getenv('DATABASE_HOST', 'http://localhost:8529')),
        'username': os.getenv('ARANGO_USERNAME', os.getenv('DATABASE_USERNAME', 'root')),
        'password': os.getenv('ARANGO_PASSWORD', os.getenv('DATABASE_PASSWORD', '')),
        'database': os.getenv('ARANGO_DATABASE', os.getenv('DATABASE_NAME', 'manufacturing_graphs')),
    }
    
    if not config['password']:
        print("Warning: ARANGO_PASSWORD not set in .env")
    
    # If running inside a container, localhost refers to the container, not the host
    # Try to prefer host.docker.internal when the host is set to localhost
    try:
        in_container = os.path.exists('/.dockerenv') or os.path.exists('/.containerenv')
    except Exception:
        in_container = False

    if in_container:
        host_lower = config['host'].lower()
        if host_lower.startswith('http://localhost') or host_lower.startswith('http://127.0.0.1') or host_lower.startswith('localhost'):
            # switch to host.docker.internal which Docker Desktop maps to the host
            old = config['host']
            config['host'] = 'http://host.docker.internal:8529'
            print(f"Detected container environment: rewriting host {old} -> {config['host']}")

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
    # Attempt to use nx_arangodb if it exposes the expected API; otherwise fall back
    if not HAS_NX_ARANGO:
        print("nx_arangodb not available or incompatible; falling back to manual persistence")
        return persist_manual(G, config, graph_name)

    try:
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
    except Exception as e:
        print(f"nx_arangodb persistence failed ({e}), falling back to manual persistence")
        return persist_manual(G, config, graph_name)


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

    # Attempt to register a gharial graph wiring the edge collection to the node collection
    try:
        edge_def = {
            "collection": edges_collection,
            "from": [nodes_collection],
            "to": [nodes_collection],
        }
        try:
            # python-arango: create_graph will raise if graph exists
            db.create_graph(graph_name, edge_definitions=[edge_def])
            print(f"Registered gharial graph: {graph_name}")
        except Exception as e:
            # graph may already exist or api differs; try to fetch existing graph
            try:
                existing = db.graph(graph_name)
                print(f"Graph '{graph_name}' already exists (skipping create).")
            except Exception:
                print(f"Warning: failed to create or fetch graph '{graph_name}': {e}")
    except Exception as e:
        print(f"Warning: error while attempting to register gharial graph: {e}")

    print(f"Persisted to collections: {nodes_collection}, {edges_collection}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Persist NetworkX schema graph to ArangoDB")
    parser.add_argument("--no-register", dest="no_register", action="store_true",
                        help="Persist collections but do not register the gharial graph")
    args = parser.parse_args()

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
        # Respect the --no-register flag: if set, always use manual persistence
        # which writes collections but will not register via nx_arangodb's graph helper.
        if getattr(args, 'no_register', False):
            print("--no-register specified: skipping automatic gharial registration")
            persist_manual(G, config, graph_name)
        else:
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
