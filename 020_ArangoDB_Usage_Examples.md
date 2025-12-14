# Entry Point 020: ArangoDB Graph Persistence - Usage Examples

Based on NVIDIA Developer Blog: [Accelerated, Production-Ready Graph Analytics for NetworkX Users](https://developer.nvidia.com/blog/accelerated-production-ready-graph-analytics-for-networkx-users/)

## Setup

### 1. Get ArangoDB Instance

**Option A: ArangoGraph Cloud (Recommended)**
- Visit [ArangoGraph](https://arangodb.com/arangograph-managedgraphdb/)
- Create free account
- Provision database instance
- Note your connection details

**Option B: Self-Hosted**
- Download from [ArangoDB Downloads](https://www.arangodb.com/download/)
- Install and start local instance
- Default: http://localhost:8529

### 2. Set Environment Variables

```bash
# Add to Secrets or .env file
DATABASE_HOST=https://your-instance.arangodb.cloud:8529
DATABASE_USERNAME=root
DATABASE_PASSWORD=your_password
DATABASE_NAME=manufacturing_graphs
```

## Usage Patterns

### Pattern 1: Persist Entry Point 018 Schema Graph

```python
from 020_Entry_Point_ArangoDB_Graph_Persistence import (
    ArangoDBConfig,
    ArangoDBGraphPersistence
)
from 018_Entry_Point_Structured_RAG_Graph import SchemaGraphManager

# Step 1: Load schema graph from PostgreSQL
manager = SchemaGraphManager()
schema_graph = manager.build_graph_from_database()

print(f"Loaded schema graph: {schema_graph.number_of_nodes()} nodes, {schema_graph.number_of_edges()} edges")

# Step 2: Configure ArangoDB connection
config = ArangoDBConfig()  # Uses environment variables
persistence = ArangoDBGraphPersistence(config)

# Step 3: Persist to ArangoDB
adb_graph = persistence.persist_graph(
    graph=schema_graph,
    name="manufacturing_schema_v1",
    write_batch_size=10000
)

print("✅ Schema graph persisted to ArangoDB")

# Step 4: In a new session, load from ArangoDB (3x faster)
adb_graph = persistence.load_graph(
    name="manufacturing_schema_v1",
    directed=True
)

# Step 5: Run deterministic join pathfinding on persisted graph
import networkx as nx

path = nx.shortest_path(adb_graph, "equipment", "supplier")
print(f"Join path: {' → '.join(path)}")
```

### Pattern 2: Persist Entry Point 019 Manufacturing Networks

```python
from 020_Entry_Point_ArangoDB_Graph_Persistence import ArangoDBGraphPersistence
from 019_Entry_Point_NetworkX_Graph_Patterns import ManufacturingNetworkBuilder

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
```

### Pattern 3: GPU-Accelerated Analytics (NVIDIA cuGraph)

```python
import networkx as nx
from 020_Entry_Point_ArangoDB_Graph_Persistence import ArangoDBGraphPersistence

# Load large graph from ArangoDB
persistence = ArangoDBGraphPersistence()
adb_graph = persistence.load_graph(
    name="large_manufacturing_network",
    read_batch_size=100000,
    read_parallelism=10
)

# Run GPU-accelerated algorithm (if NVIDIA GPU available)
# NVIDIA blog reports 11-600x speedup for betweenness centrality
result = nx.betweenness_centrality(
    adb_graph,
    k=100,
    backend="cugraph"  # Automatically uses GPU if available
)

# Find critical bridge nodes
top_bridges = sorted(result.items(), key=lambda x: x[1], reverse=True)[:5]

print("Top 5 critical bridge nodes:")
for node, score in top_bridges:
    print(f"  {node}: {score:.3f}")

# Save results back to graph
for node, score in result.items():
    adb_graph.nodes[node]['betweenness'] = score
```

### Pattern 4: Convert Between ArangoDB and NetworkX

```python
from 020_Entry_Point_ArangoDB_Graph_Persistence import ArangoDBGraphPersistence
import networkx as nx

persistence = ArangoDBGraphPersistence()

# Load from ArangoDB
adb_graph = persistence.load_graph("manufacturing_schema_v1")

# Convert to in-memory NetworkX for local analysis
nx_graph = persistence.convert_to_networkx(adb_graph)

# Run local analysis
communities = list(nx.community.greedy_modularity_communities(nx_graph.to_undirected()))

print(f"Found {len(communities)} communities in schema graph")

# Modify locally
nx_graph.nodes["equipment"]["analyzed"] = True

# Persist updated graph back to ArangoDB
updated_adb_graph = persistence.persist_graph(
    graph=nx_graph,
    name="manufacturing_schema_v1",
    overwrite=True  # Replace existing graph
)
```

## Key Benefits from NVIDIA Blog

### Performance Improvements
- **3x faster session loading** - Graphs persisted in ArangoDB load much faster than rebuilding from source
- **11-600x speedup** - GPU-accelerated betweenness centrality with cuGraph
- **Batch optimization** - Configurable read/write batch sizes for optimal throughput

### Production Features
- **Scalability** - Horizontal scaling across multiple ArangoDB nodes
- **Collaboration** - Share graphs across team members and sessions
- **Persistence** - No need to rebuild graphs from source data every time
- **Flexibility** - Support for multiple data models (graph, document, key/value)

### Zero Code Changes
- NetworkX algorithms work on ArangoDB-backed graphs
- GPU acceleration with `backend="cugraph"` parameter
- Seamless integration with existing NetworkX workflows

## Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│ Entry Points 018, 019                               │
│ (Local NetworkX Graph Development)                  │
└─────────────────────┬───────────────────────────────┘
                      │
                      │ persist_graph()
                      ▼
┌─────────────────────────────────────────────────────┐
│ Entry Point 020 - ArangoDB Persistence Layer        │
│ - Configuration management                          │
│ - Batch read/write optimization                     │
│ - Environment variable security                     │
└─────────────────────┬───────────────────────────────┘
                      │
                      │ load_graph()
                      ▼
┌─────────────────────────────────────────────────────┐
│ Team Collaboration & Production Analytics           │
│ - Shared graph access                               │
│ - GPU-accelerated algorithms (nx-cugraph)           │
│ - 3x faster session loading                         │
└─────────────────────────────────────────────────────┘
```

## References

- **NVIDIA Blog**: [Accelerated, Production-Ready Graph Analytics for NetworkX Users](https://developer.nvidia.com/blog/accelerated-production-ready-graph-analytics-for-networkx-users/)
- **nx-arangodb GitHub**: [ArangoDB-Community/nx-arangodb](https://github.com/ArangoDB-Community/nx-arangodb)
- **ArangoGraph**: [ArangoDB Managed Service](https://arangodb.com/arangograph-managedgraphdb/)
- **Entry Point 018**: Structured RAG with Graph-Theoretic Determinism
- **Entry Point 019**: NetworkX Graph Patterns (Edward L. Platt)
