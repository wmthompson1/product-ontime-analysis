#!/usr/bin/env python3
"""
026 - NCM Elevation Weights for ArangoDB Semantic Graph
========================================================
Updates the ArangoDB semantic graph with explicit elevation weights
for the NCM vs Defect disambiguation pattern.

Perspective-driven Concept Elevation:
- Quality Perspective: Elevates MATERIAL_NON_CONFORMANCE (NCM.severity)
- Finance Perspective: Elevates FINANCIAL_LIABILITY_NCM (NCM.cost_impact)

The Solder Pattern:
(:Intent) -> [:OPERATES_WITHIN] -> (:Perspective) 
    -> [:ELEVATES weight=1.0] -> (:Concept) 
    -> [:CAN_MEAN] -> (:Field)
"""

import os
import sqlite3
import networkx as nx
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

SQLITE_PATH = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"


def ensure_ncm_concepts_exist(conn):
    """Ensure NCM-related concepts exist in SQLite."""
    cursor = conn.cursor()
    
    new_concepts = [
        ("MATERIAL_NON_CONFORMANCE", "Material-centric defect tracking preferred by Quality perspective. Links to ncm.severity for root cause analysis."),
        ("FINANCIAL_LIABILITY_NCM", "Financial impact from NCM events preferred by Finance perspective. Links to ncm.cost_impact for actual costs."),
        ("PRODUCTION_DEFECT", "Generic production defect tracking. Links to product_defects table for estimated costs."),
    ]
    
    for concept_name, description in new_concepts:
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concepts (concept_name, description)
            VALUES (?, ?)
        """, (concept_name, description))
    
    conn.commit()
    print(f"  Ensured {len(new_concepts)} NCM-related concepts exist")


def ensure_ncm_fields_exist(conn):
    """Ensure NCM field mappings exist."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT concept_id FROM schema_concepts WHERE concept_name = 'MATERIAL_NON_CONFORMANCE'")
    ncm_concept_id = cursor.fetchone()
    
    cursor.execute("SELECT concept_id FROM schema_concepts WHERE concept_name = 'FINANCIAL_LIABILITY_NCM'")
    fin_ncm_concept_id = cursor.fetchone()
    
    cursor.execute("SELECT concept_id FROM schema_concepts WHERE concept_name = 'PRODUCTION_DEFECT'")
    defect_concept_id = cursor.fetchone()
    
    if ncm_concept_id:
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_non_conformant_materials', 'severity')
        """, (ncm_concept_id[0],))
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_non_conformant_materials', 'defect_description')
        """, (ncm_concept_id[0],))
    
    if fin_ncm_concept_id:
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_non_conformant_materials', 'cost_impact')
        """, (fin_ncm_concept_id[0],))
    
    if defect_concept_id:
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_product_defects', 'severity')
        """, (defect_concept_id[0],))
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_product_defects', 'defect_type')
        """, (defect_concept_id[0],))
        cursor.execute("""
            INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name)
            VALUES (?, 'stg_product_defects', 'cost_impact')
        """, (defect_concept_id[0],))
    
    conn.commit()
    print("  Added NCM field mappings (including cost_impact collision fields)")


def load_semantic_graph_with_elevations(conn):
    """Load semantic graph with explicit elevation weights for NCM pattern."""
    G = nx.DiGraph()
    COLLECTION = "manufacturing_semantic_layer_node"
    
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
    
    print("Loading concepts (including NCM concepts)...")
    cursor = conn.execute("SELECT concept_id, concept_name, description FROM schema_concepts")
    for row in cursor:
        node_key = f"concept_{row['concept_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Concept",
                   concept_id=row['concept_id'],
                   name=row['concept_name'],
                   description=row['description'] or "")
    
    print("Loading fields (including NCM fields)...")
    cursor = conn.execute("SELECT DISTINCT table_name, field_name FROM schema_concept_fields")
    for row in cursor:
        node_key = f"field_{row['table_name']}_{row['field_name']}"
        node_id = f"{COLLECTION}/{node_key}"
        G.add_node(node_id, 
                   type="Field",
                   table_name=row['table_name'],
                   field_name=row['field_name'],
                   name=f"{row['table_name']}.{row['field_name']}")
    
    print("Loading Intent -> Perspective edges (OPERATES_WITHIN)...")
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
    
    print("Loading Perspective -> Concept edges (USES_DEFINITION)...")
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
    
    print("Loading Field -> Concept edges (CAN_MEAN)...")
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
    
    print("Loading Intent -> Concept edges (ELEVATES/SUPPRESSES)...")
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
    
    print("\nAdding explicit NCM elevation edges...")
    
    ncm_concept = f"{COLLECTION}/concept_MATERIAL_NON_CONFORMANCE"
    fin_ncm_concept = f"{COLLECTION}/concept_FINANCIAL_LIABILITY_NCM"
    defect_concept = f"{COLLECTION}/concept_PRODUCTION_DEFECT"
    quality_perspective = f"{COLLECTION}/perspective_Quality"
    finance_perspective = f"{COLLECTION}/perspective_Finance"
    
    if G.has_node(quality_perspective) and G.has_node(ncm_concept):
        G.add_edge(quality_perspective, ncm_concept,
                   relationship="ELEVATES",
                   elevation_weight=1.0,
                   solder_priority="primary",
                   collision_resolution="Quality perspective selects NCM.severity over defect.severity")
        print(f"  Added: Quality -> MATERIAL_NON_CONFORMANCE (weight=1.0)")
    
    if G.has_node(quality_perspective) and G.has_node(defect_concept):
        G.add_edge(quality_perspective, defect_concept,
                   relationship="SUPPRESSES",
                   elevation_weight=0.0,
                   solder_priority="secondary",
                   collision_resolution="Suppressed when NCM is elevated")
        print(f"  Added: Quality -> PRODUCTION_DEFECT (weight=0.0, suppressed)")
    
    if G.has_node(finance_perspective) and G.has_node(fin_ncm_concept):
        G.add_edge(finance_perspective, fin_ncm_concept,
                   relationship="ELEVATES",
                   elevation_weight=1.0,
                   solder_priority="primary",
                   collision_resolution="Finance perspective selects NCM.cost_impact (actual) over defect.cost_impact (estimated)")
        print(f"  Added: Finance -> FINANCIAL_LIABILITY_NCM (weight=1.0)")
    
    if G.has_node(finance_perspective) and G.has_node(defect_concept):
        G.add_edge(finance_perspective, defect_concept,
                   relationship="SUPPRESSES",
                   elevation_weight=0.0,
                   solder_priority="secondary",
                   collision_resolution="Suppressed in Finance - defect.cost_impact is estimated, NCM.cost_impact is actual")
        print(f"  Added: Finance -> PRODUCTION_DEFECT (weight=0.0, suppressed)")
    
    ncm_severity_field = f"{COLLECTION}/field_stg_non_conformant_materials_severity"
    ncm_cost_field = f"{COLLECTION}/field_stg_non_conformant_materials_cost_impact"
    defect_severity_field = f"{COLLECTION}/field_stg_product_defects_severity"
    defect_cost_field = f"{COLLECTION}/field_stg_product_defects_cost_impact"
    
    if G.has_node(defect_cost_field) and G.has_node(defect_concept):
        G.add_edge(defect_cost_field, defect_concept,
                   relationship="CAN_MEAN",
                   is_primary=False,
                   table_alias="defect",
                   note="Estimated cost - suppressed in Finance perspective")
        print(f"  Added: stg_product_defects.cost_impact -> PRODUCTION_DEFECT (estimated)")
    
    if G.has_node(ncm_severity_field) and G.has_node(ncm_concept):
        G.add_edge(ncm_severity_field, ncm_concept,
                   relationship="CAN_MEAN",
                   is_primary=True,
                   table_alias="ncm")
    
    if G.has_node(ncm_cost_field) and G.has_node(fin_ncm_concept):
        G.add_edge(ncm_cost_field, fin_ncm_concept,
                   relationship="CAN_MEAN",
                   is_primary=True,
                   table_alias="ncm")
    
    return G


def print_graph_stats(G):
    """Print graph statistics."""
    print(f"\n📊 Graph Statistics:")
    print(f"   Nodes: {G.number_of_nodes()}")
    print(f"   Edges: {G.number_of_edges()}")
    
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"   Node types: {type_counts}")
    
    rel_counts = {}
    for _, _, data in G.edges(data=True):
        r = data.get('relationship', 'unknown')
        rel_counts[r] = rel_counts.get(r, 0) + 1
    print(f"   Edge types: {rel_counts}")


def main():
    print("=" * 70)
    print("NCM Elevation Weights - ArangoDB Semantic Graph Update")
    print("=" * 70)
    
    print("\n📖 Step 1: Update SQLite with NCM concepts...")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    
    ensure_ncm_concepts_exist(conn)
    ensure_ncm_fields_exist(conn)
    
    print("\n📖 Step 2: Load semantic graph with elevation weights...")
    G = load_semantic_graph_with_elevations(conn)
    conn.close()
    
    print_graph_stats(G)
    
    print("\n🔗 Step 3: Connecting to ArangoDB...")
    config = ArangoDBConfig()
    print(f"   Host: {config.host}")
    print(f"   Database: {config.database_name}")
    
    persistence = ArangoDBGraphPersistence(config)
    
    print("\n💾 Step 4: Persisting updated graph to ArangoDB...")
    adb_graph = persistence.persist_graph(
        graph=G,
        name="manufacturing_semantic_layer",
        write_batch_size=1000,
        overwrite=True
    )
    
    print("\n✅ Graph persisted successfully!")
    
    print("\n🔍 Step 5: Verifying persistence...")
    loaded = persistence.load_graph(
        name="manufacturing_semantic_layer",
        directed=True
    )
    print(f"   Loaded nodes: {loaded.number_of_nodes()}")
    print(f"   Loaded edges: {loaded.number_of_edges()}")
    
    print("\n" + "=" * 70)
    print("✅ SUCCESS: NCM elevation weights added to ArangoDB!")
    print("=" * 70)
    
    print("\n📋 NCM vs Defect Disambiguation Pattern:")
    print("-" * 70)
    print("| Perspective | Elevated Concept           | Field Priority       |")
    print("|-------------|----------------------------|----------------------|")
    print("| Quality     | MATERIAL_NON_CONFORMANCE   | ncm.severity (1.0)   |")
    print("| Finance     | FINANCIAL_LIABILITY_NCM    | ncm.cost_impact(1.0) |")
    print("-" * 70)
    
    print("\n🔎 Test AQL queries saved to: 026_AQL_Path_Resolution_Test.aql")


if __name__ == "__main__":
    main()
