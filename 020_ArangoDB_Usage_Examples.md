# Entry Point 020: ArangoDB Graph Persistence - Usage Examples

Persist NetworkX graphs to local ArangoDB for faster session loading and team collaboration.

## Setup

### 1. Install ArangoDB Locally

**macOS (Homebrew)**
```bash
brew install arangodb
brew services start arangodb
```

**Linux (apt)**
```bash
curl -OL https://download.arangodb.com/arangodb311/DEBIAN/Release.key
sudo apt-key add - < Release.key
echo 'deb https://download.arangodb.com/arangodb311/DEBIAN/ /' | sudo tee /etc/apt/sources.list.d/arangodb.list
sudo apt-get update
sudo apt-get install arangodb3
```

**Default Access**: http://localhost:8529

### 2. Install Dependencies

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-arango.txt
```

### 3. Set Environment Variables

Create `.env` file in project root:
```bash
DATABASE_HOST=http://localhost:8529
DATABASE_USERNAME=root
DATABASE_PASSWORD=your_local_password
DATABASE_NAME=manufacturing_graphs
```

### 4. Run Persistence Script

```bash
./.venv/bin/python scripts/persist_to_arango.py
```

The script uses `python-dotenv` to safely load credentials from `.env`.

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

### Pattern 3: Centrality Analysis on Persisted Graph

```python
import networkx as nx
from 020_Entry_Point_ArangoDB_Graph_Persistence import ArangoDBGraphPersistence

# Load graph from local ArangoDB
persistence = ArangoDBGraphPersistence()
adb_graph = persistence.load_graph(
    name="manufacturing_schema_v1",
    directed=True
)

# Run centrality analysis
result = nx.betweenness_centrality(adb_graph.to_undirected())

# Find critical bridge nodes
top_bridges = sorted(result.items(), key=lambda x: x[1], reverse=True)[:5]

print("Top 5 critical bridge nodes:")
for node, score in top_bridges:
    print(f"  {node}: {score:.3f}")
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

## Key Benefits

### Performance Improvements
- **Faster session loading** - Graphs persisted in ArangoDB load faster than rebuilding from SQLite
- **Batch optimization** - Configurable read/write batch sizes for optimal throughput

### Production Features
- **Team Collaboration** - Share graphs across team members and sessions
- **Persistence** - No need to rebuild graphs from source data every time
- **Flexibility** - Support for multiple data models (graph, document, key/value)

### Zero Code Changes
- NetworkX algorithms work on ArangoDB-backed graphs
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

- **nx-arangodb GitHub**: [ArangoDB-Community/nx-arangodb](https://github.com/ArangoDB-Community/nx-arangodb)
- **ArangoDB Downloads**: [arangodb.com/download](https://www.arangodb.com/download/)
- **Entry Point 018**: Structured RAG with Graph-Theoretic Determinism
- **Entry Point 019**: NetworkX Graph Patterns
