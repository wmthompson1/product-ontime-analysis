"""
020_Entry_Point_Persist_2nd_NetworkX_Arango.py

Second Pass: Advanced NetworkX-over-ArangoDB Patterns
Demonstrates production patterns for manufacturing intelligence graphs

Key Concepts:
1. Node metadata preservation (labels, attributes)
2. Loading existing graphs from previous sessions (3x faster)
3. Running advanced NetworkX algorithms on ArangoDB-backed graphs
4. Team collaboration workflow (persist once, load many times)

Based on: NVIDIA Developer Blog "Accelerated, Production-Ready Graph Analytics for NetworkX Users"
"""

import networkx as nx
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence
import os

print("=" * 75)
print("NetworkX over ArangoDB - Second Pass: Advanced Patterns")
print("=" * 75)

# Initialize ArangoDB connection
config = ArangoDBConfig()
persistence = ArangoDBGraphPersistence(config)

print(f"\n📊 Connected to ArangoDB:")
print(f"   Database: {config.database_name}")
print(f"   Host: {config.host}")


# =============================================================================
# Pattern 1: Preserve Node Metadata for Identification
# =============================================================================
print("\n" + "=" * 75)
print("Pattern 1: Node Metadata Preservation")
print("=" * 75)

# Create graph with meaningful node attributes
G = nx.DiGraph()

# Add nodes with metadata (labels help identify them after loading)
G.add_node("equipment_A", label="equipment_A", type="machine", capacity=100)
G.add_node("product_X", label="product_X", type="product", sku="SKU-001")
G.add_node("order_123", label="order_123", type="order", quantity=50)
G.add_node("customer_C1", label="customer_C1", type="customer", region="West")

# Add edges with metadata
G.add_edge("equipment_A", "product_X", relationship="produces", rate=10)
G.add_edge("product_X", "order_123", relationship="fulfills", units=50)
G.add_edge("order_123", "customer_C1", relationship="ships_to", priority="high")

print(f"\n✅ Created graph with metadata:")
print(f"   Nodes: {G.number_of_nodes()}")
print(f"   Edges: {G.number_of_edges()}")
for node, data in G.nodes(data=True):
    print(f"   • {node}: {data}")

# Persist to ArangoDB
print(f"\n📤 Persisting graph 'manufacturing_flow' to ArangoDB...")
adb_graph = persistence.persist_graph(
    graph=G,
    name="manufacturing_flow",
    overwrite=True
)
print(f"✅ Graph 'manufacturing_flow' persisted successfully!")


# =============================================================================
# Pattern 2: Load Graph in New Session (3x Faster)
# =============================================================================
print("\n" + "=" * 75)
print("Pattern 2: Fast Session Loading (Team Collaboration)")
print("=" * 75)

print(f"\n📥 Simulating new session: Loading 'manufacturing_flow' from ArangoDB...")
loaded_graph = persistence.load_graph(
    name="manufacturing_flow",
    directed=True
)

print(f"✅ Graph loaded: {loaded_graph.number_of_nodes()} nodes, {loaded_graph.number_of_edges()} edges")
print(f"   ⚡ Benefit: 3x faster than loading from source files")
print(f"   🤝 Team can collaborate on the same graph")

# Convert to NetworkX for full algorithm support
nx_graph = nx.DiGraph()
nx_graph.add_nodes_from(loaded_graph.nodes(data=True))
nx_graph.add_edges_from(loaded_graph.edges(data=True))

# Access nodes by their labels (metadata preserved!)
print(f"\n🔍 Node metadata preserved:")
for node, data in nx_graph.nodes(data=True):
    if 'label' in data:
        print(f"   • ArangoDB ID: {node}")
        print(f"     Label: {data['label']}, Type: {data.get('type', 'N/A')}")


# =============================================================================
# Pattern 3: Advanced NetworkX Algorithms on ArangoDB-Backed Graphs
# =============================================================================
print("\n" + "=" * 75)
print("Pattern 3: Advanced NetworkX Algorithms")
print("=" * 75)

# Build label-to-id mapping for easy node access
label_to_id = {data['label']: node for node, data in nx_graph.nodes(data=True) if 'label' in data}
print(f"\n📋 Label-to-ID mapping created:")
for label, node_id in label_to_id.items():
    print(f"   {label} → {node_id}")

# Run shortest path analysis
print(f"\n🔍 Shortest Path Analysis:")
if "equipment_A" in label_to_id and "customer_C1" in label_to_id:
    source_id = label_to_id["equipment_A"]
    target_id = label_to_id["customer_C1"]
    
    path = nx.shortest_path(nx_graph, source=source_id, target=target_id)
    
    # Convert path back to labels for readability
    path_labels = [nx_graph.nodes[node]['label'] for node in path]
    print(f"   Path (by label): {' → '.join(path_labels)}")
    print(f"   Path length: {len(path) - 1} hops")

# Run centrality analysis
print(f"\n📊 Centrality Analysis:")
degree_centrality = nx.degree_centrality(nx_graph)
betweenness_centrality = nx.betweenness_centrality(nx_graph)

print(f"\n   Top nodes by degree centrality:")
for node, centrality in sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:3]:
    label = nx_graph.nodes[node].get('label', node)
    print(f"   • {label}: {centrality:.3f}")

print(f"\n   Top nodes by betweenness centrality:")
for node, centrality in sorted(betweenness_centrality.items(), key=lambda x: x[1], reverse=True)[:3]:
    label = nx_graph.nodes[node].get('label', node)
    print(f"   • {label}: {centrality:.3f}")


# =============================================================================
# Pattern 4: Load Schema Graph from Entry Point 018
# =============================================================================
print("\n" + "=" * 75)
print("Pattern 4: Loading Existing Schema Graphs")
print("=" * 75)

# Check if schema graph exists from Entry Point 018
print(f"\n🔍 Checking for existing schema graphs...")
try:
    # Try to load the supply chain graph from Entry Point 018
    schema_graph = persistence.load_graph(
        name="supply_chain_2025_q1",
        directed=True
    )
    print(f"✅ Found 'supply_chain_2025_q1' graph!")
    print(f"   Nodes: {schema_graph.number_of_nodes()}")
    print(f"   Edges: {schema_graph.number_of_edges()}")
    
    # Convert and analyze
    schema_nx = nx.DiGraph()
    schema_nx.add_nodes_from(schema_graph.nodes(data=True))
    schema_nx.add_edges_from(schema_graph.edges(data=True))
    
    print(f"\n📊 Schema graph analysis:")
    print(f"   Density: {nx.density(schema_nx):.3f}")
    print(f"   Is DAG: {nx.is_directed_acyclic_graph(schema_nx)}")
    
except Exception as e:
    print(f"⚠️  'supply_chain_2025_q1' not found: {e}")
    print(f"   Run '018_Entry_Point_Persist_Graph.py' first to create it")


# =============================================================================
# Pattern 5: Team Collaboration Workflow
# =============================================================================
print("\n" + "=" * 75)
print("Pattern 5: Team Collaboration Workflow")
print("=" * 75)

print(f"""
🤝 Team Collaboration Pattern:

1. Data Engineer: Loads raw data → Creates NetworkX graph → Persists to ArangoDB
   python 018_Entry_Point_Persist_Graph.py

2. Data Analyst: Loads graph from ArangoDB (3x faster) → Runs analysis
   loaded_graph = persistence.load_graph("supply_chain_2025_q1")

3. Data Scientist: Loads same graph → Runs ML algorithms
   nx_graph = convert_to_networkx(loaded_graph)
   communities = nx.community.louvain_communities(nx_graph)

4. Business User: Loads graph → Queries insights via LangChain semantic layer
   This enables natural language queries over the graph structure!

Benefits:
✅ Single source of truth (ArangoDB)
✅ 3x faster session loading vs. loading from CSV/DB
✅ GPU acceleration available (11-600x speedup with nx-cugraph)
✅ Scales to billions of edges with ArangoDB clustering
""")


# =============================================================================
# Summary
# =============================================================================
print("=" * 75)
print("Summary: NetworkX over ArangoDB Production Patterns")
print("=" * 75)

print(f"""
✅ Pattern 1: Node metadata preservation → Nodes identifiable after loading
✅ Pattern 2: Fast session loading → 3x faster than source files
✅ Pattern 3: Advanced algorithms → Full NetworkX API compatibility
✅ Pattern 4: Schema graph integration → Entry Point 018 graphs accessible
✅ Pattern 5: Team collaboration → Shared graph workspace

Next Steps:
1. Connect Entry Point 018 (Structured RAG) with ArangoDB-backed graphs
2. Integrate LangChain semantic layer with graph queries
3. Deploy to production with ArangoDB clustering
4. Enable GPU acceleration with nx-cugraph backend

🎯 Goal: Production-ready manufacturing intelligence platform with:
   • Graph-theoretic determinism (NetworkX algorithms)
   • Natural language interface (LangChain semantic layer)
   • Scalable persistence (ArangoDB)
   • Team collaboration (shared graph workspace)
""")

print("=" * 75)
