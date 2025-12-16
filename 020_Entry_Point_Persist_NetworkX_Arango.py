# 020_Entry_Point_Persist_NetworkX_Arango.py
import networkx as nx
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

# networkx over arangodb for graph persistence

# Step 1: Create your NetworkX graph (any way you like)
G = nx.DiGraph()
G.add_edges_from([
    ("equipment", "product"),
    ("product", "order"),
    ("order", "customer")
])

# Step 2: Set up ArangoDB connection
# Make sure you have these environment variables set (prefer ARANGO_* names):
# ARANGO_URL (or ARANGO_HOST/ARANGO_PORT), ARANGO_USER, ARANGO_PASSWORD (or ARANGO_ROOT_PASSWORD), ARANGO_DB

config = ArangoDBConfig()  # Uses environment variables
persistence = ArangoDBGraphPersistence(config)

# Step 3: Persist your graph to ArangoDB
adb_graph = persistence.persist_graph(
    graph=G,
    name="manufacturing_demand",        # Give it a unique name
    write_batch_size=10000,      # Optional: tune for performance
    overwrite=True               # Optional: True to replace existing
)

print("✅ Graph saved to ArangoDB!")

# Step 4: Later, load it back in a new session
loaded_graph = persistence.load_graph(
    name="manufacturing_demand",
    directed=True                # Match your graph type
)

# Step 5: Use it like any NetworkX graph
print(f"\n📊 Loaded graph analysis:")
print(f"   Nodes: {list(loaded_graph.nodes())[:10]}")  # Show first 10 nodes
print(f"   Edges: {list(loaded_graph.edges())[:10]}")  # Show first 10 edges

# Convert to regular NetworkX graph for full compatibility
nx_graph = nx.DiGraph()
nx_graph.add_nodes_from(loaded_graph.nodes(data=True))
nx_graph.add_edges_from(loaded_graph.edges(data=True))

print(f"\n✅ Converted to NetworkX DiGraph:")
print(f"   Nodes: {list(nx_graph.nodes())}")
print(f"   Edges: {list(nx_graph.edges())}")

# Now run NetworkX algorithms
if "equipment" in nx_graph and "customer" in nx_graph:
    path = nx.shortest_path(nx_graph.to_undirected(), "equipment", "customer")
    print(f"\n🔍 Shortest path: {' → '.join(path)}")
else:
    print(f"\n⚠️  Note: Node names may be transformed during persistence.")
    print(f"   This is expected with ArangoDB backend.")