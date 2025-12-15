#!/usr/bin/env python3
"""
020_Entry_Point_ArangoDB_Graph_Persistence.py
ArangoDB Graph Persistence for NetworkX

Based on NVIDIA Developer Blog:
"Accelerated, Production-Ready Graph Analytics for NetworkX Users"
https://developer.nvidia.com/blog/accelerated-production-ready-graph-analytics-for-networkx-users/

Demonstrates production-ready graph persistence using nx-arangodb:
- Persist NetworkX graphs to ArangoDB
- Load graphs from ArangoDB in new sessions
- Collaborative graph analytics with shared persistence layer
- Integration with Entry Point 018 (Structured RAG) and 019 (NetworkX patterns)
"""

import os
import networkx as nx
from typing import Optional, Dict, Any, Union, TYPE_CHECKING
import json

if TYPE_CHECKING:
    import nx_arangodb as nxadb

try:
    import nx_arangodb as nxadb
    NXADB_AVAILABLE = True
except ImportError:
    NXADB_AVAILABLE = False
    nxadb = None  # type: ignore
    print("⚠️  nx-arangodb not available. Install with: pip install nx-arangodb")


class ArangoDBConfig:
    """
    Configuration manager for ArangoDB connection
    
    Best practices from NVIDIA blog:
    - Use environment variables for credentials
    - Support both cloud and self-hosted ArangoDB
    - Configurable batch sizes for optimal performance
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        """
        Initialize ArangoDB configuration
        
        Args:
            host: ArangoDB host URL (default: env DATABASE_HOST)
            username: Database username (default: env DATABASE_USERNAME)
            password: Database password (default: env DATABASE_PASSWORD)
            database_name: Database name (default: env DATABASE_NAME or 'networkx_graphs')
        """
        # Prefer ARANGO_* variables if present, fall back to older DATABASE_* names
        self.host = host or os.getenv("ARANGO_URL") or os.getenv("ARANGO_HOST") or os.getenv("DATABASE_HOST", "http://localhost:8529")
        self.username = username or os.getenv("ARANGO_USER") or os.getenv("ARANGO_USERNAME") or os.getenv("DATABASE_USERNAME", "root")
        self.password = password or os.getenv("ARANGO_PASSWORD") or os.getenv("ARANGO_ROOT_PASSWORD") or os.getenv("DATABASE_PASSWORD", "")
        self.database_name = database_name or os.getenv("ARANGO_DB") or os.getenv("ARANGO_DATABASE") or os.getenv("DATABASE_NAME", "networkx_graphs")

    def set_environment_variables(self):
        """Set environment variables for nx-arangodb and provide compatibility aliases"""
        # Maintain DATABASE_* envs for backward compatibility
        os.environ["DATABASE_HOST"] = self.host
        os.environ["DATABASE_USERNAME"] = self.username
        os.environ["DATABASE_PASSWORD"] = self.password
        os.environ["DATABASE_NAME"] = self.database_name
        # Ensure ARANGO_* are set if callers prefer the new names
        os.environ.setdefault("ARANGO_URL", self.host)
        os.environ.setdefault("ARANGO_USER", self.username)
        os.environ.setdefault("ARANGO_PASSWORD", self.password)
        os.environ.setdefault("ARANGO_DB", self.database_name)
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get connection information (safe for logging)"""
        return {
            "host": self.host,
            "username": self.username,
            "database_name": self.database_name,
            "password": "***" if self.password else "Not set"
        }


class ArangoDBGraphPersistence:
    """
    Utility class for persisting NetworkX graphs to ArangoDB
    
    Pattern from NVIDIA blog:
    1. Create NetworkX graph locally
    2. Persist to ArangoDB with nxadb.DiGraph/Graph
    3. Re-instantiate from ArangoDB in new sessions
    4. Run algorithms on persisted graphs
    """
    
    def __init__(self, config: Optional[ArangoDBConfig] = None):
        """
        Initialize with ArangoDB configuration
        
        Args:
            config: ArangoDBConfig instance (creates default if None)
        """
        if not NXADB_AVAILABLE:
            raise ImportError("nx-arangodb package required. Install: pip install nx-arangodb")
        
        self.config = config or ArangoDBConfig()
        self.config.set_environment_variables()
    
    def persist_graph(
        self,
        graph: Union[nx.Graph, nx.DiGraph],
        name: str,
        write_batch_size: int = 50000,
        overwrite: bool = False
    ) -> Any:
        """
        Persist NetworkX graph to ArangoDB
        
        Pattern from NVIDIA blog (Step 3):
        ```python
        G_nxadb = nxadb.DiGraph(
            name="cit_patents",
            incoming_graph_data=G_nx,
            write_batch_size=50000
        )
        ```
        
        Args:
            graph: NetworkX Graph or DiGraph to persist
            name: Unique name for the graph in ArangoDB
            write_batch_size: Batch size for write operations (default: 50000)
            overwrite: Whether to overwrite existing graph with same name
        
        Returns:
            nx-arangodb Graph or DiGraph instance
        """
        print(f"📤 Persisting graph '{name}' to ArangoDB...")
        print(f"   Graph type: {type(graph).__name__}")
        print(f"   Nodes: {graph.number_of_nodes()}")
        print(f"   Edges: {graph.number_of_edges()}")
        print(f"   Write batch size: {write_batch_size}")
        
        try:
            # Choose appropriate ArangoDB graph type
            # Ensure nodes carry a persistent key/name attribute so Arango documents
            # retain human-readable table names instead of numeric keys. Build a
            # shallow copy of the graph where each node has an explicit '_key' and
            # 'name' attribute derived from the original node identifier.
            G_persist = nx.DiGraph() if isinstance(graph, nx.DiGraph) else nx.Graph()
            for n, attrs in graph.nodes(data=True):
                # create a safe string key
                key = str(n)
                new_attrs = dict(attrs)
                # prefer existing name-like attributes, but ensure '_key' exists
                if '_key' not in new_attrs:
                    new_attrs['_key'] = key
                if 'name' not in new_attrs and 'label' not in new_attrs:
                    new_attrs['name'] = key
                G_persist.add_node(key, **new_attrs)
            for u, v, attrs in graph.edges(data=True):
                G_persist.add_edge(str(u), str(v), **dict(attrs))

            if isinstance(graph, nx.DiGraph):
                adb_graph = nxadb.DiGraph(
                    name=name,
                    incoming_graph_data=G_persist,
                    write_batch_size=write_batch_size,
                    overwrite=overwrite,
                    # nx-arangodb accepts overwrite_graph to force clearing existing data
                    overwrite_graph=overwrite
                )
            else:
                adb_graph = nxadb.Graph(
                    name=name,
                    incoming_graph_data=G_persist,
                    write_batch_size=write_batch_size,
                    overwrite=overwrite,
                    overwrite_graph=overwrite
                )
            
            print(f"✅ Graph '{name}' successfully persisted to ArangoDB")
            return adb_graph
            
        except Exception as e:
            print(f"❌ Failed to persist graph: {e}")
            raise
    
    def load_graph(
        self,
        name: str,
        directed: bool = True,
        read_batch_size: int = 50000,
        read_parallelism: int = 4
    ) -> Any:
        """
        Load persisted graph from ArangoDB
        
        Pattern from NVIDIA blog (Step 4):
        ```python
        G_nxadb = nxadb.DiGraph(
            name="cit_patents",
            read_batch_size=100000,
            read_parallelism=10
        )
        ```
        
        Args:
            name: Name of the graph in ArangoDB
            directed: Whether to load as DiGraph (True) or Graph (False)
            read_batch_size: Batch size for read operations (default: 50000)
            read_parallelism: Parallelism level for reads (default: 4)
        
        Returns:
            nx-arangodb Graph or DiGraph instance
        """
        print(f"📥 Loading graph '{name}' from ArangoDB...")
        print(f"   Graph type: {'DiGraph' if directed else 'Graph'}")
        print(f"   Read batch size: {read_batch_size}")
        print(f"   Read parallelism: {read_parallelism}")
        
        try:
            if directed:
                adb_graph = nxadb.DiGraph(
                    name=name,
                    read_batch_size=read_batch_size,
                    read_parallelism=read_parallelism
                )
            else:
                adb_graph = nxadb.Graph(
                    name=name,
                    read_batch_size=read_batch_size,
                    read_parallelism=read_parallelism
                )
            
            print(f"✅ Graph '{name}' successfully loaded from ArangoDB")
            print(f"   Nodes: {adb_graph.number_of_nodes()}")
            print(f"   Edges: {adb_graph.number_of_edges()}")
            
            return adb_graph
            
        except Exception as e:
            print(f"❌ Failed to load graph: {e}")
            raise
    
    def convert_to_networkx(
        self,
        adb_graph: Any
    ) -> Union[nx.Graph, nx.DiGraph]:
        """
        Convert ArangoDB graph to in-memory NetworkX graph
        
        Useful for local analysis or algorithm execution
        
        Args:
            adb_graph: nx-arangodb Graph or DiGraph
        
        Returns:
            NetworkX Graph or DiGraph
        """
        print(f"🔄 Converting ArangoDB graph to NetworkX...")
        
        if isinstance(adb_graph, nxadb.DiGraph):
            nx_graph = nx.DiGraph(adb_graph)
        else:
            nx_graph = nx.Graph(adb_graph)
        
        print(f"✅ Conversion complete")
        print(f"   Nodes: {nx_graph.number_of_nodes()}")
        print(f"   Edges: {nx_graph.number_of_edges()}")
        
        return nx_graph


def demo_arangodb_persistence_local():
    """
    Demonstration using local NetworkX graphs (no ArangoDB connection required)
    
    Shows the pattern and code structure for when ArangoDB is available
    """
    print("🧪 ArangoDB Graph Persistence Demo (Local Mode)")
    print("=" * 75)
    
    print("\n📋 SETUP INSTRUCTIONS:")
    print("To use ArangoDB persistence, you need:")
    print("1. ArangoDB instance (ArangoGraph Cloud or self-hosted)")
    print("2. Set environment variables:")
    print("   - DATABASE_HOST (e.g., https://your-instance.arangodb.cloud:8529)")
    print("   - DATABASE_USERNAME (e.g., root)")
    print("   - DATABASE_PASSWORD (your password)")
    print("   - DATABASE_NAME (e.g., manufacturing_graphs)")
    print("3. Install: pip install nx-arangodb")
    
    if not NXADB_AVAILABLE:
        print("\n⚠️  nx-arangodb not installed. Showing code patterns only.")
        print("\n📝 PATTERN 1: Persist Entry Point 018 Schema Graph")
        print("""
# Load schema graph from database (Entry Point 018)
from 018_Entry_Point_Structured_RAG_Graph import SchemaGraphManager

manager = SchemaGraphManager()
schema_graph = manager.build_graph_from_database()

# Persist to ArangoDB
config = ArangoDBConfig(
    host="https://your-instance.arangodb.cloud:8529",
    username="root",
    password="your-password",
    database_name="manufacturing_graphs"
)

persistence = ArangoDBGraphPersistence(config)
adb_graph = persistence.persist_graph(
    graph=schema_graph,
    name="manufacturing_schema_v1",
    write_batch_size=50000
)

# New session - load from ArangoDB
adb_graph = persistence.load_graph(
    name="manufacturing_schema_v1",
    directed=True
)

# Run shortest path on persisted graph
path = nx.shortest_path(adb_graph, "equipment", "supplier")
print(f"Join path: {' → '.join(path)}")
        """)
        
        print("\n📝 PATTERN 2: Persist Entry Point 019 Manufacturing Networks")
        print("""
# Create manufacturing network (Entry Point 019)
from 019_Entry_Point_NetworkX_Graph_Patterns import ManufacturingNetworkBuilder

builder = ManufacturingNetworkBuilder()
supply_chain = builder.create_directed_supply_chain()

# Persist to ArangoDB
persistence = ArangoDBGraphPersistence(config)
adb_graph = persistence.persist_graph(
    graph=supply_chain,
    name="supply_chain_2025_q1",
    write_batch_size=10000
)

# Team member can now load and analyze
adb_graph = persistence.load_graph("supply_chain_2025_q1")
centrality = nx.degree_centrality(adb_graph)
print(f"Most connected: {max(centrality.items(), key=lambda x: x[1])}")
        """)
        
        print("\n📝 PATTERN 3: GPU-Accelerated Analysis with cuGraph")
        print("""
# Load large graph from ArangoDB
adb_graph = persistence.load_graph(
    name="large_manufacturing_network",
    read_batch_size=100000,
    read_parallelism=10
)

# Run GPU-accelerated algorithm (if NVIDIA GPU available)
result = nx.betweenness_centrality(
    adb_graph,
    k=100,
    backend="cugraph"  # Uses GPU acceleration
)

# Save results back to ArangoDB
for node, score in result.items():
    adb_graph.nodes[node]['betweenness'] = score
        """)
        
        print("\n🎯 Key Benefits from NVIDIA Blog:")
        print("   ✓ 3x faster session loading (data persisted in ArangoDB)")
        print("   ✓ 11-600x speedup with GPU acceleration (nx-cugraph)")
        print("   ✓ Collaborative graph analytics (shared persistence layer)")
        print("   ✓ Scalability across multiple nodes (ArangoDB clustering)")
        print("   ✓ Zero code changes for NetworkX users")
    
    else:
        print("\n✅ nx-arangodb is installed!")
        print("⚠️  No ArangoDB connection configured.")
        print("Set DATABASE_HOST, DATABASE_USERNAME, DATABASE_PASSWORD, DATABASE_NAME")
        print("to enable persistence features.")
    
    print(f"\n{'=' * 75}")
    print("📖 Reference: NVIDIA Developer Blog")
    print("🔗 https://developer.nvidia.com/blog/accelerated-production-ready-graph-analytics-for-networkx-users/")
    
    return True


def demo_integration_with_entry_points():
    """
    Show how Entry Point 020 integrates with Entry Points 018 and 019
    """
    print("\n\n🔗 Integration with Previous Entry Points")
    print("=" * 75)
    
    print("\n📊 Entry Point 018: Structured RAG Graph → ArangoDB")
    print("   Use case: Persist database schema graph for team collaboration")
    print("   Pattern: Load from PostgreSQL → Persist to ArangoDB → Share with team")
    print("   Benefit: Deterministic join pathfinding available to all team members")
    
    print("\n📊 Entry Point 019: NetworkX Patterns → ArangoDB")
    print("   Use case: Persist manufacturing networks (equipment, supply chain)")
    print("   Pattern: Build network locally → Persist to ArangoDB → Analyze in new sessions")
    print("   Benefit: 3x faster loading, collaborative analytics")
    
    print("\n🎯 Production-Ready Architecture:")
    print("   1. Local development: NetworkX (Entry Points 018, 019)")
    print("   2. Persistence layer: ArangoDB (Entry Point 020)")
    print("   3. Acceleration layer: cuGraph + GPU (NVIDIA pattern)")
    print("   4. Result: Scalable, collaborative, GPU-accelerated graph analytics")
    
    return True


if __name__ == "__main__":
    # Run demonstrations
    demo_arangodb_persistence_local()
    demo_integration_with_entry_points()
