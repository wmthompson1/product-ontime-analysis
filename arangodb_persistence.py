#!/usr/bin/env python3
"""
Importable module version of Entry Point 020: ArangoDB Graph Persistence

Based on NVIDIA Developer Blog:
"Accelerated, Production-Ready Graph Analytics for NetworkX Users"
https://developer.nvidia.com/blog/accelerated-production-ready-graph-analytics-for-networkx-users/
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


class ArangoDBConfig:
    """Configuration manager for ArangoDB connection"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        self.host = host or os.getenv("DATABASE_HOST", "http://localhost:8529")
        self.username = username or os.getenv("DATABASE_USERNAME", "root")
        self.password = password or os.getenv("DATABASE_PASSWORD", "")
        self.database_name = database_name or os.getenv("DATABASE_NAME", "networkx_graphs")
    
    def set_environment_variables(self):
        """Set environment variables for nx-arangodb"""
        os.environ["DATABASE_HOST"] = self.host
        os.environ["DATABASE_USERNAME"] = self.username
        # nx_arangodb treats an empty DATABASE_PASSWORD as "not set" which
        # prevents it from attempting a connection. To be defensive, if the
        # configured password is empty we set a placeholder so the adapter will
        # still attempt to connect (useful when ArangoDB is started with
        # ARANGO_NO_AUTH=1 in local tests).
        os.environ["DATABASE_PASSWORD"] = self.password or "__placeholder_password__"
        os.environ["DATABASE_NAME"] = self.database_name
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get connection information (safe for logging)"""
        return {
            "host": self.host,
            "username": self.username,
            "database_name": self.database_name,
            "password": "***" if self.password else "Not set"
        }


class ArangoDBGraphPersistence:
    """Utility class for persisting NetworkX graphs to ArangoDB"""
    
    def __init__(self, config: Optional[ArangoDBConfig] = None):
        if not NXADB_AVAILABLE:
            raise ImportError("nx-arangodb package required. Install: pip install nx-arangodb")
        
        self.config = config or ArangoDBConfig()
        self.config.set_environment_variables()
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create the database if it doesn't exist"""
        from arango import ArangoClient
        client = ArangoClient(hosts=self.config.host)
        try:
            sys_db = client.db("_system", username=self.config.username, password=self.config.password)
        except Exception:
            # Try without auth as a fallback for local testing
            sys_db = client.db("_system")

        try:
            if not sys_db.has_database(self.config.database_name):
                print(f"📦 Creating database '{self.config.database_name}'...")
                sys_db.create_database(self.config.database_name)
                print(f"✅ Database created")
        except Exception as e:
            # If permission issues occur, surface a clear message
            print(f"⚠️  Could not verify/create database '{self.config.database_name}': {e}")
            raise
    
    def persist_graph(
        self,
        graph: Union[nx.Graph, nx.DiGraph],
        name: str,
        write_batch_size: int = 50000,
        overwrite: bool = False
    ) -> Any:
        """Persist NetworkX graph to ArangoDB"""
        print(f"📤 Persisting graph '{name}' to ArangoDB...")
        print(f"   Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
        
        try:
            # Defensive overwrite behavior: if overwrite is requested and the
            # graph exists in ArangoDB, remove it first to guarantee a clean
            # persistence.
            from arango import ArangoClient

            client = ArangoClient(hosts=self.config.host)
            try:
                sys_db = client.db("_system", username=self.config.username, password=self.config.password)
            except Exception:
                sys_db = client.db("_system")

            db = client.db(self.config.database_name, username=self.config.username, password=self.config.password)
            if overwrite:
                try:
                    if db.has_graph(name):
                        print(f"🗑️  Overwrite requested: dropping existing graph '{name}'...")
                        db.delete_graph(name, drop_collections=True)
                        print(f"✅ Dropped existing graph '{name}'")
                except Exception as e:
                    print(f"⚠️  Could not drop existing graph '{name}': {e}")

            if isinstance(graph, nx.DiGraph):
                adb_graph = nxadb.DiGraph(  # type: ignore
                    name=name,
                    incoming_graph_data=graph,
                    write_batch_size=write_batch_size,
                    overwrite_graph=overwrite
                )
            else:
                adb_graph = nxadb.Graph(  # type: ignore
                    name=name,
                    incoming_graph_data=graph,
                    write_batch_size=write_batch_size,
                    overwrite_graph=overwrite
                )

            print(f"✅ Graph '{name}' persisted successfully")
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
        """Load persisted graph from ArangoDB"""
        print(f"📥 Loading graph '{name}' from ArangoDB...")
        
        try:
            if directed:
                adb_graph = nxadb.DiGraph(  # type: ignore
                    name=name,
                    read_batch_size=read_batch_size,
                    read_parallelism=read_parallelism
                )
            else:
                adb_graph = nxadb.Graph(  # type: ignore
                    name=name,
                    read_batch_size=read_batch_size,
                    read_parallelism=read_parallelism
                )
            
            print(f"✅ Graph loaded: {adb_graph.number_of_nodes()} nodes, {adb_graph.number_of_edges()} edges")
            return adb_graph
            
        except Exception as e:
            print(f"❌ Failed to load graph: {e}")
            raise
    
    def convert_to_networkx(self, adb_graph: Any) -> Union[nx.Graph, nx.DiGraph]:
        """Convert ArangoDB graph to in-memory NetworkX graph"""
        print(f"🔄 Converting to NetworkX...")
        
        if hasattr(adb_graph, '__class__') and 'DiGraph' in adb_graph.__class__.__name__:
            nx_graph = nx.DiGraph(adb_graph)
        else:
            nx_graph = nx.Graph(adb_graph)
        
        print(f"✅ Converted: {nx_graph.number_of_nodes()} nodes, {nx_graph.number_of_edges()} edges")
        return nx_graph
