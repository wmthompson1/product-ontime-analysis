from arangodb_persistence import ArangoDBGraphPersistence
import networkx as nx

# Import the pattern builder from Entry Point 019 by loading the file directly
import sys
import importlib.util

# Load the numbered entry point file
spec = importlib.util.spec_from_file_location("ep019", "019_Entry_Point_NetworkX_Graph_Patterns.py")
ep019 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ep019)

# Extract the class we need
ManufacturingNetworkBuilder = ep019.ManufacturingNetworkBuilder

# Step 1: Create manufacturing network locally
builder = ManufacturingNetworkBuilder()
supply_chain = builder.create_directed_supply_chain()

# Step 2: Persist for team collaboration
persistence = ArangoDBGraphPersistence()
adb_graph = persistence.persist_graph(
    graph=supply_chain,
    name="supply_chain_2025_q1",
    write_batch_size=5000
)

# Step 3: Team member loads in new session
adb_graph = persistence.load_graph("supply_chain_2025_q1")

# Step 4: Run centrality analysis on persisted graph
import networkx as nx

centrality = nx.degree_centrality(adb_graph)
most_connected = max(centrality.items(), key=lambda x: x[1])

print(f"Most connected node: {most_connected[0]} (score: {most_connected[1]:.3f})")