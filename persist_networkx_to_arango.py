"""
Persist a NetworkX graph to ArangoDB.

Requirements:
- ARANGO_URL, ARANGO_USER, ARANGO_PASSWORD must be set in the environment.
- Optional: ARANGO_DB (defaults to "_system").
"""
from arango import ArangoClient
import os

def require_env(key):
    try:
        return os.environ[key]
    except KeyError:
        raise RuntimeError(f"Required environment variable '{key}' is not set. Please set it before running.")

ARANGO_URL = require_env("ARANGO_URL")
ARANGO_USER = require_env("ARANGO_USER")
ARANGO_PASSWORD = require_env("ARANGO_PASSWORD")
ARANGO_DB = os.environ.get("ARANGO_DB", "_system")

client = ArangoClient(hosts=ARANGO_URL)
db = client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)

def ensure_vertex_collection(name):
    if not db.has_collection(name):
        db.create_collection(name)
    return db.collection(name)

def ensure_edge_collection(name):
    if not db.has_collection(name):
        db.create_collection(name, edge=True)
    return db.collection(name)

def persist_graph(G,
                  vertex_collection_suffix="_vertex",
                  edge_collection_suffix="_edge",
                  node_table_attr="table"):
    """
    G: networkx.Graph (or DiGraph)
    Nodes must include an attribute (default 'table') that identifies the table/type.
    Node IDs are used as Arango _key values. Ensure they are URL-safe (no slashes).
    """
    vertex_collections = {}
    edge_collections = {}

    # Create vertex collections
    for node, attrs in G.nodes(data=True):
        table = attrs.get(node_table_attr, "default")
        coll_name = f"{table}{vertex_collection_suffix}"
        if table not in vertex_collections:
            vertex_collections[table] = ensure_vertex_collection(coll_name)

    # Create edge collections
    for u, v, attrs in G.edges(data=True):
        table = attrs.get("table", "edge")
        coll_name = f"{table}{edge_collection_suffix}"
        if table not in edge_collections:
            edge_collections[table] = ensure_edge_collection(coll_name)

    # Upsert nodes
    for node, attrs in G.nodes(data=True):
        table = attrs.get(node_table_attr, "default")
        coll = vertex_collections[table]
        key = str(node)
        doc = {k: v for k, v in attrs.items() if k != node_table_attr}
        doc["_key"] = key
        if coll.has(key):
            coll.update(doc)
        else:
            coll.insert(doc)

    # Insert edges
    for u, v, attrs in G.edges(data=True):
        table = attrs.get("table", "edge")
        coll = edge_collections[table]
        u_attrs = G.nodes[u]
        v_attrs = G.nodes[v]
        u_table = u_attrs.get(node_table_attr, "default")
        v_table = v_attrs.get(node_table_attr, "default")
        from_id = f"{u_table}{vertex_collection_suffix}/{u}"
        to_id   = f"{v_table}{vertex_collection_suffix}/{v}"
        edge_doc = {"_from": from_id, "_to": to_id}
        for k, val in attrs.items():
            if k != "table":
                edge_doc[k] = val
        coll.insert(edge_doc)