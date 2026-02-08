#!/usr/bin/env python3
"""
ArangoDB Graph Persistence using python-arango

Persists and loads NetworkX graphs to/from ArangoDB using the official
python-arango client. No nx-arangodb or GPU dependencies required.

Supports hybrid deployment:
  - Local Docker: http://localhost:8529
  - ArangoDB Cloud: https://xxxxx.arangodb.cloud:8529

Environment variables (with ARANGO_* prefix):
  ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB
"""

import os
import networkx as nx
from typing import Optional, Dict, Any, Union, List
import json

from arango import ArangoClient


class ArangoDBConfig:
    """Configuration manager for ArangoDB connection"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database_name: Optional[str] = None
    ):
        self.host = host or os.getenv("ARANGO_HOST") or os.getenv("DATABASE_HOST", "http://localhost:8529")
        self.username = username or os.getenv("ARANGO_USER") or os.getenv("DATABASE_USERNAME", "root")
        self.password = password or os.getenv("ARANGO_ROOT_PASSWORD") or os.getenv("ARANGO_PASSWORD") or os.getenv("DATABASE_PASSWORD", "")
        self.database_name = database_name or os.getenv("ARANGO_DB") or os.getenv("DATABASE_NAME", "manufacturing_semantic_layer")
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get connection information (safe for logging)"""
        return {
            "host": self.host,
            "username": self.username,
            "database_name": self.database_name,
            "password": "***" if self.password else "Not set"
        }


class ArangoDBGraphPersistence:
    """Utility class for persisting NetworkX graphs to ArangoDB using python-arango"""
    
    def __init__(self, config: Optional[ArangoDBConfig] = None):
        self.config = config or ArangoDBConfig()
        self._client = ArangoClient(hosts=self.config.host)
        self._ensure_database_exists()
        self._db = self._client.db(
            self.config.database_name,
            username=self.config.username,
            password=self.config.password
        )
    
    def _ensure_database_exists(self):
        """Create the database if it doesn't exist.
        
        On cloud instances (ArangoDB Oasis/Cloud), _system access is typically
        restricted. In that case we skip auto-creation and assume the database
        was pre-created via the cloud console.
        """
        try:
            sys_db = self._client.db(
                "_system",
                username=self.config.username,
                password=self.config.password
            )
            if not sys_db.has_database(self.config.database_name):
                print(f"Creating database '{self.config.database_name}'...")
                sys_db.create_database(self.config.database_name)
                print(f"Database created")
        except Exception as e:
            if "401" in str(e) or "not authorized" in str(e).lower():
                print(f"Skipping _system check (cloud instance): will connect directly to '{self.config.database_name}'")
            else:
                print(f"Could not verify/create database '{self.config.database_name}': {e}")
                raise

    def _ensure_collection(self, name: str, edge: bool = False):
        """Ensure a collection exists, creating it if needed"""
        if not self._db.has_collection(name):
            self._db.create_collection(name, edge=edge)
        return self._db.collection(name)

    def _ensure_graph(self, name: str, edge_definitions: List[Dict]) -> Any:
        """Ensure an ArangoDB named graph exists"""
        if self._db.has_graph(name):
            return self._db.graph(name)
        return self._db.create_graph(name, edge_definitions=edge_definitions)

    def persist_graph(
        self,
        graph: Union[nx.Graph, nx.DiGraph],
        name: str,
        vertex_collection: str = "vertices",
        edge_collection: str = "edges",
        overwrite: bool = False,
        node_table_attr: str = "table"
    ) -> Dict[str, Any]:
        """Persist NetworkX graph to ArangoDB using python-arango.
        
        Args:
            graph: NetworkX graph to persist
            name: Name for the ArangoDB named graph
            vertex_collection: Default vertex collection name (used when nodes lack a table attr)
            edge_collection: Default edge collection name
            overwrite: If True, drop existing graph and collections first
            node_table_attr: Node attribute used to group nodes into separate collections
            
        Returns:
            Dict with persistence stats
        """
        print(f"Persisting graph '{name}' to ArangoDB...")
        print(f"   Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")
        
        if overwrite and self._db.has_graph(name):
            print(f"  Overwrite requested: dropping existing graph '{name}'...")
            self._db.delete_graph(name, drop_collections=True)
            print(f"  Dropped existing graph '{name}'")
        
        vertex_collections = {}
        edge_collections_map = {}
        
        for node, attrs in graph.nodes(data=True):
            table = attrs.get(node_table_attr, vertex_collection)
            if table not in vertex_collections:
                coll = self._ensure_collection(table, edge=False)
                vertex_collections[table] = coll

        for u, v, attrs in graph.edges(data=True):
            rel = attrs.get("relationship", attrs.get(node_table_attr, edge_collection))
            if rel not in edge_collections_map:
                coll = self._ensure_collection(rel, edge=True)
                edge_collections_map[rel] = coll

        edge_definitions = []
        from_collections = list(vertex_collections.keys())
        to_collections = list(vertex_collections.keys())
        for edge_coll_name in edge_collections_map.keys():
            edge_definitions.append({
                "edge_collection": edge_coll_name,
                "from_vertex_collections": from_collections,
                "to_vertex_collections": to_collections
            })
        
        if edge_definitions:
            self._ensure_graph(name, edge_definitions)
        
        nodes_inserted = 0
        nodes_updated = 0
        for node, attrs in graph.nodes(data=True):
            table = attrs.get(node_table_attr, vertex_collection)
            coll = vertex_collections[table]
            key = str(node).replace("/", "_").replace(" ", "_")
            doc = {}
            for k, v in attrs.items():
                try:
                    json.dumps(v)
                    doc[k] = v
                except (TypeError, ValueError):
                    doc[k] = str(v)
            doc["_key"] = key
            doc["nx_node_id"] = str(node)
            
            try:
                if coll.has(key):
                    coll.update(doc)
                    nodes_updated += 1
                else:
                    coll.insert(doc)
                    nodes_inserted += 1
            except Exception as e:
                print(f"  Warning: Could not persist node '{node}': {e}")
        
        edges_inserted = 0
        for u, v, attrs in graph.edges(data=True):
            rel = attrs.get("relationship", attrs.get(node_table_attr, edge_collection))
            coll = edge_collections_map[rel]
            
            u_table = graph.nodes[u].get(node_table_attr, vertex_collection)
            v_table = graph.nodes[v].get(node_table_attr, vertex_collection)
            u_key = str(u).replace("/", "_").replace(" ", "_")
            v_key = str(v).replace("/", "_").replace(" ", "_")
            
            edge_doc = {
                "_from": f"{u_table}/{u_key}",
                "_to": f"{v_table}/{v_key}"
            }
            for k, val in attrs.items():
                if k not in ("_from", "_to"):
                    try:
                        json.dumps(val)
                        edge_doc[k] = val
                    except (TypeError, ValueError):
                        edge_doc[k] = str(val)
            
            try:
                coll.insert(edge_doc)
                edges_inserted += 1
            except Exception as e:
                print(f"  Warning: Could not persist edge '{u}' -> '{v}': {e}")
        
        stats = {
            "graph_name": name,
            "nodes_inserted": nodes_inserted,
            "nodes_updated": nodes_updated,
            "edges_inserted": edges_inserted,
            "vertex_collections": list(vertex_collections.keys()),
            "edge_collections": list(edge_collections_map.keys())
        }
        print(f"  Graph '{name}' persisted: {nodes_inserted} inserted, {nodes_updated} updated, {edges_inserted} edges")
        return stats
    
    def load_graph(
        self,
        name: str,
        directed: bool = True
    ) -> Union[nx.Graph, nx.DiGraph]:
        """Load graph from ArangoDB into NetworkX.
        
        Args:
            name: ArangoDB named graph name
            directed: If True, return DiGraph; otherwise Graph
            
        Returns:
            NetworkX graph with all node/edge attributes
        """
        print(f"Loading graph '{name}' from ArangoDB...")
        
        if not self._db.has_graph(name):
            raise ValueError(f"Graph '{name}' not found in ArangoDB")
        
        adb_graph = self._db.graph(name)
        
        if directed:
            nx_graph = nx.DiGraph()
        else:
            nx_graph = nx.Graph()
        
        for vcoll_name in adb_graph.vertex_collections():
            vcoll = self._db.collection(vcoll_name)
            for doc in vcoll.all():
                node_id = doc.get("nx_node_id", doc["_key"])
                attrs = {k: v for k, v in doc.items() if not k.startswith("_")}
                nx_graph.add_node(node_id, **attrs)
        
        for edge_def in adb_graph.edge_definitions():
            ecoll_name = edge_def["edge_collection"]
            ecoll = self._db.collection(ecoll_name)
            for doc in ecoll.all():
                from_key = doc["_from"].split("/", 1)[1]
                to_key = doc["_to"].split("/", 1)[1]
                from_node = doc.get("nx_from_id", from_key)
                to_node = doc.get("nx_to_id", to_key)
                attrs = {k: v for k, v in doc.items() if not k.startswith("_")}
                nx_graph.add_edge(from_node, to_node, **attrs)
        
        print(f"  Graph loaded: {nx_graph.number_of_nodes()} nodes, {nx_graph.number_of_edges()} edges")
        return nx_graph
    
    def list_graphs(self) -> List[str]:
        """List all named graphs in the database"""
        return [g["name"] for g in self._db.graphs()]
    
    def delete_graph(self, name: str, drop_collections: bool = True):
        """Delete a named graph"""
        if self._db.has_graph(name):
            self._db.delete_graph(name, drop_collections=drop_collections)
            print(f"  Deleted graph '{name}'")
        else:
            print(f"  Graph '{name}' not found")

    def test_connection(self) -> Dict[str, Any]:
        """Test the ArangoDB connection and return status info"""
        try:
            version = self._db.version()
            return {
                "connected": True,
                "version": version,
                "database": self.config.database_name,
                "host": self.config.host,
                "graphs": self.list_graphs()
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "host": self.config.host
            }
