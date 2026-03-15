"""
020_Entry_Point_Persist_2nd_NetworkX_Arango.py

Second Pass: Load Manufacturing Schema from SQLite → NetworkX → ArangoDB
Simple, focused pattern for persisting schema graphs.

Workflow:
1. Load schema_nodes and schema_edges from SQLite database
2. Create NetworkX graph with proper node metadata
3. Persist to ArangoDB with metadata preservation
"""

from simple_digraph import SimpleDiGraph
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
import os
import sqlite3
from config import SQLITE_DB_PATH

print("=" * 75)
print("NetworkX over ArangoDB - Second Pass")
print("Load Schema from SQLite → Persist to ArangoDB")
print("=" * 75)

# Step 1: Connect to SQLite database
print("\n📊 Step 1: Load schema from SQLite database")
print("-" * 75)

DB_PATH = SQLITE_DB_PATH

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Load nodes
cursor.execute("SELECT * FROM schema_nodes ORDER BY table_name")
nodes = cursor.fetchall()
print(f"✅ Loaded {len(nodes)} nodes from schema_nodes table:")
for node in nodes:
    print(f"   • {node['table_name']} ({node['table_type']}): {node['description']}")

# Load edges
cursor.execute("SELECT * FROM schema_edges ORDER BY edge_id")
edges = cursor.fetchall()
print(f"\n✅ Loaded {len(edges)} edges from schema_edges table:")
for edge in edges:
    print(f"   • {edge['from_table']} → {edge['to_table']} ({edge['relationship_type']})")

cursor.close()
conn.close()

# Step 2: Build NetworkX graph with metadata
print("\n📊 Step 2: Build NetworkX graph with metadata")
print("-" * 75)

G = SimpleDiGraph()
COLLECTION = "manufacturing_schema_node"

# Add nodes with metadata preservation
# Use collection/key format for ArangoDB document key
for node in nodes:
    node_id = f"{COLLECTION}/{node['table_name']}"
    G.add_node(
        node_id,
        label=node['table_name'],
        table_type=node['table_type'],
        description=node['description'],
        node_type='schema_table'
    )

# Add edges with enhanced metadata preservation
for edge in edges:
    from_id = f"{COLLECTION}/{edge['from_table']}"
    to_id = f"{COLLECTION}/{edge['to_table']}"
    G.add_edge(
        from_id,
        to_id,
        relationship_type=edge['relationship_type'],
        join_column=edge['join_column'],
        weight=edge['weight'],
        # Enhanced metadata for semantic layer
        join_column_description=edge.get('join_column_description'),
        natural_language_alias=edge.get('natural_language_alias'),
        few_shot_example=edge.get('few_shot_example'),
        context=edge.get('context')
    )

print(f"✅ NetworkX graph created:")
print(f"   Nodes: {G.number_of_nodes()}")
print(f"   Edges: {G.number_of_edges()}")
print(f"\n   Node details:")
for node, data in G.nodes(data=True):
    print(f"   • {node}: label={data['label']}, type={data['table_type']}")

# Step 3: Persist to ArangoDB
print("\n📊 Step 3: Persist to ArangoDB")
print("-" * 75)

config = ArangoDBConfig()
persistence = ArangoDBGraphPersistence(config)

print(f"   Database: {config.database_name}")
print(f"   Host: {config.host}")

graph_name = "manufacturing_schema"
print(f"\n📤 Persisting graph '{graph_name}' to ArangoDB...")

adb_graph = persistence.persist_graph(
    graph=G,
    name=graph_name,
    overwrite=True
)

print(f"✅ Graph '{graph_name}' persisted successfully!")
print(f"   All node metadata preserved (labels, types, descriptions)")
print(f"   All edge metadata preserved (relationships, join columns, weights)")
print(f"   Enhanced metadata preserved (aliases, descriptions, few-shot examples, context)")

print("\n" + "=" * 75)
print("✅ Complete: SQLite → NetworkX → ArangoDB")
print("=" * 75)
print(f"""
Summary:
• Loaded {len(nodes)} schema nodes from SQLite
• Loaded {len(edges)} schema edges from SQLite
• Created NetworkX graph with full metadata
• Persisted to ArangoDB as '{graph_name}'

Next: Run 020_Entry_Point_Persist_3rd_NetworkX_Arango.py to restore
""")
print("=" * 75)
