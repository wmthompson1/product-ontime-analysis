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
path = nx.shortest_path(loaded_graph.to_undirected(), "equipment", "customer")
print(f"Path: {' → '.join(path)}")