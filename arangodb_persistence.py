#!/usr/bin/env python3
"""
ArangoDB Graph Persistence using python-arango

Persists and loads graphs to/from ArangoDB using the official
python-arango client. Works with plain Python dicts — no graph
library dependency required.

Supports hybrid deployment:
  - Local Docker: http://localhost:8529
  - ArangoDB Cloud: https://xxxxx.arangodb.cloud:8529

Safety policy:
  - overwrite=False (default): upserts nodes, inserts edges — safe for re-runs
  - overwrite=True: drops and re-creates the named graph — destructive
  - load/list/test operations are always read-only
  - Credentials read from env vars, never hardcoded
  - See 020_ArangoDB_Usage_Examples.md for full safety documentation

Environment variables (with ARANGO_* prefix):
  ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB
"""

import os
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
        self.host = (host or os.getenv("ARANGO_HOST") or os.getenv("DATABASE_HOST", "http://localhost:8529")).strip()
        self.username = username or os.getenv("ARANGO_USER") or os.getenv("DATABASE_USERNAME", "root")
        self.password = password or os.getenv("ARANGO_ROOT_PASSWORD") or os.getenv("ARANGO_PASSWORD") or os.getenv("DATABASE_PASSWORD", "")
        self.database_name = database_name or os.getenv("ARANGO_DB") or os.getenv("DATABASE_NAME")
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get connection information (safe for logging)"""
        return {
            "host": self.host,
            "username": self.username,
            "database_name": self.database_name,
            "password": "***" if self.password else "Not set"
        }


class ArangoDBGraphPersistence:
    """Persist and load graph data to/from ArangoDB using python-arango.

    Works with plain Python dicts — no graph library required.
    See 020_ArangoDB_Usage_Examples.md for safety policy.
    """

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
        restricted.  In that case we skip auto-creation and assume the database
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

    @staticmethod
    def _sanitize_key(raw: str) -> str:
        """Sanitize a string into a valid ArangoDB document _key."""
        return str(raw).replace("/", "_").replace(" ", "_")

    @staticmethod
    def _safe_value(val: Any) -> Any:
        """Return val if JSON-serializable, else str(val)."""
        try:
            json.dumps(val)
            return val
        except (TypeError, ValueError):
            return str(val)

    def persist_from_dicts(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        vertex_collection: str = "vertices",
        edge_collection: str = "edges",
        overwrite: bool = False,
        node_id_field: str = "id",
        node_collection_field: str = "table",
        edge_relationship_field: str = "relationship",
        edge_from_field: str = "from",
        edge_to_field: str = "to",
    ) -> Dict[str, Any]:
        """Persist graph data from plain Python dicts to ArangoDB.

        Safety:
          - overwrite=False (default): upserts nodes, inserts edges
          - overwrite=True: DESTRUCTIVE — drops the named graph first

        Args:
            name: ArangoDB named graph identifier
            nodes: list of dicts, each with at least an id field
            edges: list of dicts, each with 'from' and 'to' fields
            vertex_collection: default vertex collection name
            edge_collection: default edge collection name
            overwrite: drop existing graph before writing (destructive)
            node_id_field: key in node dicts used as document _key
            node_collection_field: key in node dicts for collection routing
            edge_relationship_field: key in edge dicts for edge collection routing
            edge_from_field: key in edge dicts for source node id
            edge_to_field: key in edge dicts for target node id

        Returns:
            Dict with persistence stats
        """
        print(f"Persisting graph '{name}' to ArangoDB...")
        print(f"   Nodes: {len(nodes)}, Edges: {len(edges)}")

        if overwrite and self._db.has_graph(name):
            print(f"  Overwrite requested: dropping existing graph '{name}'...")
            self._db.delete_graph(name, drop_collections=True)
            print(f"  Dropped existing graph '{name}'")

        vertex_collections: Dict[str, Any] = {}
        edge_collections_map: Dict[str, Any] = {}

        for node in nodes:
            table = node.get(node_collection_field, vertex_collection)
            if table not in vertex_collections:
                vertex_collections[table] = self._ensure_collection(table, edge=False)

        for edge in edges:
            rel = edge.get(edge_relationship_field, edge_collection)
            if rel not in edge_collections_map:
                edge_collections_map[rel] = self._ensure_collection(rel, edge=True)

        from_collections = list(vertex_collections.keys())
        to_collections = list(vertex_collections.keys())
        edge_definitions = [
            {
                "edge_collection": ecoll_name,
                "from_vertex_collections": from_collections,
                "to_vertex_collections": to_collections,
            }
            for ecoll_name in edge_collections_map
        ]
        if edge_definitions:
            self._ensure_graph(name, edge_definitions)

        nodes_inserted = 0
        nodes_updated = 0
        for node in nodes:
            table = node.get(node_collection_field, vertex_collection)
            coll = vertex_collections[table]
            key = self._sanitize_key(node.get(node_id_field, ""))
            doc = {
                k: self._safe_value(v)
                for k, v in node.items()
                if k not in (node_id_field, node_collection_field)
            }
            doc["_key"] = key
            doc["original_id"] = str(node.get(node_id_field, key))
            try:
                if coll.has(key):
                    coll.update(doc)
                    nodes_updated += 1
                else:
                    coll.insert(doc)
                    nodes_inserted += 1
            except Exception as e:
                print(f"  Warning: Could not persist node '{key}': {e}")

        edges_inserted = 0
        for edge in edges:
            rel = edge.get(edge_relationship_field, edge_collection)
            coll = edge_collections_map[rel]
            from_id = self._sanitize_key(edge.get(edge_from_field, ""))
            to_id = self._sanitize_key(edge.get(edge_to_field, ""))
            from_table = vertex_collection
            to_table = vertex_collection
            for n in nodes:
                nid = self._sanitize_key(n.get(node_id_field, ""))
                if nid == from_id:
                    from_table = n.get(node_collection_field, vertex_collection)
                if nid == to_id:
                    to_table = n.get(node_collection_field, vertex_collection)

            edge_doc = {
                "_from": f"{from_table}/{from_id}",
                "_to": f"{to_table}/{to_id}",
            }
            for k, val in edge.items():
                if k not in (edge_from_field, edge_to_field, "_from", "_to"):
                    edge_doc[k] = self._safe_value(val)
            try:
                coll.insert(edge_doc)
                edges_inserted += 1
            except Exception as e:
                print(f"  Warning: Could not persist edge '{from_id}' -> '{to_id}': {e}")

        stats = {
            "graph_name": name,
            "nodes_inserted": nodes_inserted,
            "nodes_updated": nodes_updated,
            "edges_inserted": edges_inserted,
            "vertex_collections": list(vertex_collections.keys()),
            "edge_collections": list(edge_collections_map.keys()),
        }
        print(f"  Graph '{name}' persisted: {nodes_inserted} inserted, {nodes_updated} updated, {edges_inserted} edges")
        return stats

    def load_graph(
        self,
        name: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Load graph from ArangoDB as plain Python dicts (read-only).

        Args:
            name: ArangoDB named graph name

        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        print(f"Loading graph '{name}' from ArangoDB...")

        if not self._db.has_graph(name):
            raise ValueError(f"Graph '{name}' not found in ArangoDB")

        adb_graph = self._db.graph(name)

        nodes: List[Dict[str, Any]] = []
        for vcoll_name in adb_graph.vertex_collections():
            vcoll = self._db.collection(vcoll_name)
            for doc in vcoll.all():
                node = {k: v for k, v in doc.items() if not k.startswith("_")}
                node["_key"] = doc["_key"]
                node["_collection"] = vcoll_name
                nodes.append(node)

        edges: List[Dict[str, Any]] = []
        for edge_def in adb_graph.edge_definitions():
            ecoll_name = edge_def["edge_collection"]
            ecoll = self._db.collection(ecoll_name)
            for doc in ecoll.all():
                edge = {k: v for k, v in doc.items() if not k.startswith("_")}
                edge["_from"] = doc["_from"]
                edge["_to"] = doc["_to"]
                edge["_collection"] = ecoll_name
                edges.append(edge)

        print(f"  Graph loaded: {len(nodes)} nodes, {len(edges)} edges")
        return {"nodes": nodes, "edges": edges}

    def list_graphs(self) -> List[str]:
        """List all named graphs in the database (read-only)"""
        return [g["name"] for g in self._db.graphs()]

    def delete_graph(self, name: str, drop_collections: bool = True):
        """Delete a named graph (DESTRUCTIVE — see safety policy)"""
        if self._db.has_graph(name):
            self._db.delete_graph(name, drop_collections=drop_collections)
            print(f"  Deleted graph '{name}'")
        else:
            print(f"  Graph '{name}' not found")

    def test_connection(self) -> Dict[str, Any]:
        """Test the ArangoDB connection and return status info (read-only)"""
        try:
            version = self._db.version()
            return {
                "connected": True,
                "version": version,
                "database": self.config.database_name,
                "host": self.config.host,
                "graphs": self.list_graphs(),
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "host": self.config.host,
            }
