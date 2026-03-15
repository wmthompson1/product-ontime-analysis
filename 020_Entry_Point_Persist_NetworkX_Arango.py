# 020_Entry_Point_Persist_NetworkX_Arango.py
from simple_digraph import SimpleDiGraph, shortest_path
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

# networkx over arangodb for graph persistence

# Step 1: Create your NetworkX graph (any way you like)
G = SimpleDiGraph()
G.add_edge("equipment", "product")
G.add_edge("product", "order")
G.add_edge("order", "customer")

# Step 2: Set up ArangoDB connection
# Make sure you have these environment variables set:
# DATABASE_HOST, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME

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

# Convert to regular SimpleDiGraph for full compatibility
nx_graph = SimpleDiGraph()
for node_id, data in loaded_graph.nodes(data=True):
    nx_graph.add_node(node_id, **data)
for u, v, data in loaded_graph.edges(data=True):
    nx_graph.add_edge(u, v, **data)

print(f"\n✅ Converted to SimpleDiGraph:")
print(f"   Nodes: {[n for n, _ in nx_graph.nodes(data=True)]}")
print(f"   Edges: {[(u, v) for u, v, _ in nx_graph.edges(data=True)]}")

# Now run algorithms
if nx_graph.has_node("equipment") and nx_graph.has_node("customer"):
    path = shortest_path(nx_graph.to_undirected(), "equipment", "customer")
    print(f"\n🔍 Shortest path: {' → '.join(path)}")
else:
    print(f"\n⚠️  Note: Node names may be transformed during persistence.")
    print(f"   This is expected with ArangoDB backend.")