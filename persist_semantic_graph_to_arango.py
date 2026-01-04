#!/usr/bin/env python3
"""
Persist Semantic Graph to ArangoDB

Exports the manufacturing semantic layer from SQLite to ArangoDB.
Graph structure: Intent -> Perspective -> Concept <- Field
"""

import os
import sqlite3
import networkx as nx
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

SQLITE_PATH = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"

def load_semantic_graph_from_sqlite():
    """Load the semantic graph from SQLite into NetworkX."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    
    G = nx.DiGraph()
    
    COLLECTION = "manufacturing_semantic_layer_node"
    
    # Load Intents as nodes
    print("Loading intents...")
    cursor = conn.execute("SELECT intent_id, intent_name, description FROM schema_intents")
    for row in cursor:
        node_key = f"intent_{row['intent_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Intent",
                   intent_id=row['intent_id'],
                   name=row['intent_name'],
                   description=row['description'] or "")
    
    # Load Perspectives as nodes
    print("Loading perspectives...")
    cursor = conn.execute("SELECT perspective_id, perspective_name, description FROM schema_perspectives")
    for row in cursor:
        node_key = f"perspective_{row['perspective_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Perspective",
                   perspective_id=row['perspective_id'],
                   name=row['perspective_name'],
                   description=row['description'] or "")
    
    # Load Concepts as nodes
    print("Loading concepts...")
    cursor = conn.execute("SELECT concept_id, concept_name, description FROM schema_concepts")
    for row in cursor:
        node_key = f"concept_{row['concept_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Concept",
                   concept_id=row['concept_id'],
                   name=row['concept_name'],
                   description=row['description'] or "")
    
    # Load Fields as nodes (from concept_fields)
    print("Loading fields...")
    cursor = conn.execute("SELECT DISTINCT table_name, field_name FROM schema_concept_fields")
    for row in cursor:
        node_key = f"field_{row['table_name']}_{row['field_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Field",
                   table_name=row['table_name'],
                   field_name=row['field_name'],
                   name=f"{row['table_name']}.{row['field_name']}")
    
    # Load OPERATES_WITHIN edges (Intent -> Perspective)
    print("Loading Intent -> Perspective edges...")
    cursor = conn.execute("""
        SELECT i.intent_name, p.perspective_name, ip.intent_factor_weight
        FROM schema_intent_perspectives ip
        JOIN schema_intents i ON ip.intent_id = i.intent_id
        JOIN schema_perspectives p ON ip.perspective_id = p.perspective_id
    """)
    for row in cursor:
        G.add_edge(f"{COLLECTION}/intent_{row['intent_name']}", 
                   f"{COLLECTION}/perspective_{row['perspective_name']}",
                   relationship="OPERATES_WITHIN",
                   weight=row['intent_factor_weight'])
    
    # Load USES_DEFINITION edges (Perspective -> Concept)
    print("Loading Perspective -> Concept edges...")
    cursor = conn.execute("""
        SELECT p.perspective_name, c.concept_name
        FROM schema_perspective_concepts pc
        JOIN schema_perspectives p ON pc.perspective_id = p.perspective_id
        JOIN schema_concepts c ON pc.concept_id = c.concept_id
    """)
    for row in cursor:
        G.add_edge(f"{COLLECTION}/perspective_{row['perspective_name']}", 
                   f"{COLLECTION}/concept_{row['concept_name']}",
                   relationship="USES_DEFINITION")
    
    # Load CAN_MEAN edges (Field -> Concept) - note: reverse direction for traversal
    print("Loading Field -> Concept edges...")
    cursor = conn.execute("""
        SELECT c.concept_name, cf.table_name, cf.field_name
        FROM schema_concept_fields cf
        JOIN schema_concepts c ON cf.concept_id = c.concept_id
    """)
    for row in cursor:
        field_key = f"field_{row['table_name']}_{row['field_name']}"
        G.add_edge(f"{COLLECTION}/{field_key}", 
                   f"{COLLECTION}/concept_{row['concept_name']}",
                   relationship="CAN_MEAN")
    
    # Load ELEVATES/SUPPRESSES edges (Intent -> Concept)
    print("Loading Intent -> Concept edges...")
    cursor = conn.execute("""
        SELECT i.intent_name, c.concept_name, ic.intent_factor_weight
        FROM schema_intent_concepts ic
        JOIN schema_intents i ON ic.intent_id = i.intent_id
        JOIN schema_concepts c ON ic.concept_id = c.concept_id
    """)
    for row in cursor:
        weight = row['intent_factor_weight']
        if weight == 1:
            rel = "ELEVATES"
        elif weight == -1:
            rel = "SUPPRESSES"
        else:
            rel = "NEUTRAL"
        G.add_edge(f"{COLLECTION}/intent_{row['intent_name']}", 
                   f"{COLLECTION}/concept_{row['concept_name']}",
                   relationship=rel,
                   weight=weight)
    
    conn.close()
    return G

def main():
    print("=" * 60)
    print("Semantic Graph -> ArangoDB Persistence")
    print("=" * 60)
    
    # Step 1: Load from SQLite
    print("\n📖 Loading semantic graph from SQLite...")
    G = load_semantic_graph_from_sqlite()
    
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {G.number_of_nodes()}")
    print(f"   Edges: {G.number_of_edges()}")
    
    # Count by type
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"   Node types: {type_counts}")
    
    # Count edges by relationship
    rel_counts = {}
    for _, _, data in G.edges(data=True):
        r = data.get('relationship', 'unknown')
        rel_counts[r] = rel_counts.get(r, 0) + 1
    print(f"   Edge types: {rel_counts}")
    
    # Step 2: Connect to ArangoDB
    print("\n🔗 Connecting to ArangoDB...")
    config = ArangoDBConfig()
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")
    
    persistence = ArangoDBGraphPersistence(config)
    
    # Step 3: Persist to ArangoDB
    print("\n💾 Persisting graph to ArangoDB...")
    adb_graph = persistence.persist_graph(
        graph=G,
        name="manufacturing_semantic_layer",
        write_batch_size=1000,
        overwrite=True
    )
    
    print("\n✅ Graph persisted successfully!")
    
    # Step 4: Verify by loading back
    print("\n🔍 Verifying persistence by loading back...")
    loaded = persistence.load_graph(
        name="manufacturing_semantic_layer",
        directed=True
    )
    print(f"   Loaded nodes: {loaded.number_of_nodes()}")
    print(f"   Loaded edges: {loaded.number_of_edges()}")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: Semantic graph persisted to ArangoDB!")
    print("=" * 60)
    print("\nYou can now view your graph at:")
    print(f"   {config.host}")
    print("\nAQL query to explore:")
    print('   FOR doc IN manufacturing_semantic_layer_vertices LIMIT 10 RETURN doc')

if __name__ == "__main__":
    main()
