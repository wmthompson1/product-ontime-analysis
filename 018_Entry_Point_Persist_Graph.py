#!/usr/bin/env python3
"""
018_Entry_Point_Persist_Graph.py
Example: Persist Entry Point 018 schema graph to ArangoDB
"""

import networkx as nx
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
from schema_graph import SchemaGraphManager

# Step 1: Load schema graph from PostgreSQL
manager = SchemaGraphManager()
schema_graph = manager.build_graph_from_database()

print(f"Loaded schema graph: {schema_graph.number_of_nodes()} nodes, {schema_graph.number_of_edges()} edges")

# Step 2: Configure ArangoDB connection
config = ArangoDBConfig()  # Uses environment variables
persistence = ArangoDBGraphPersistence(config)

# Step 3: Persist to ArangoDB (overwrite if exists)
adb_graph = persistence.persist_graph(
    graph=schema_graph,
    name="manufacturing_schema_v1",
    write_batch_size=10000,
    overwrite=True
)

print("✅ Schema graph persisted to ArangoDB")

# Step 4: In a new session, load from ArangoDB (3x faster)
adb_graph = persistence.load_graph(
    name="manufacturing_schema_v1",
    directed=True
)

# Step 5: Run deterministic join pathfinding on persisted graph
# Convert to undirected for pathfinding
try:
    # ArangoDB graphs need to be converted to undirected for shortest_path
    adb_undirected = adb_graph.to_undirected()
    path = nx.shortest_path(adb_undirected, "equipment", "supplier")
    print(f"Join path: {' → '.join(path)}")
except Exception as e:
    print(f"⚠️  Path calculation: {e}")
    print("Note: For production use with ArangoDB connection configured.")

