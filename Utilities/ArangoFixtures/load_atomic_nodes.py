"""
Atomic Solder Reset: Column-level nodes for manufacturing graph.

Creates vertices where _key = table_name.column_name with explicit
table_name and column_name properties, then draws the 8 manufacturing
FK edges between specific atomic column nodes.

Usage:
    python Utilities/ArangoFixtures/load_atomic_nodes.py
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from arangodb_persistence import ArangoDBConfig, ArangoDBGraphPersistence

SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "hf-space-inventory-sqlgen", "app_schema", "manufacturing.db"
)

SKIP_TABLES = {
    "sqlite_sequence", "users",
    "schema_concepts", "schema_concept_fields",
    "schema_intents", "schema_intent_concepts",
    "schema_intent_queries", "schema_perspectives",
    "schema_intent_perspectives", "schema_perspective_concepts",
    "manufacturing_acronyms",
}

GRAPH_NAME = os.getenv("ARANGO_DB", "manufacturing_graph")
VERTEX_COLLECTION = f"{GRAPH_NAME}_node"
ATOMIC_EDGE_COLLECTION = "ATOMIC_FK"


def build_column_nodes(conn):
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if r[0] not in SKIP_TABLES
    ]

    nodes = []
    for table in sorted(tables):
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        for col in cols:
            col_name = col[1]
            col_type = col[2] or "TEXT"
            is_pk = bool(col[5])
            nodes.append({
                "_key": f"{table}.{col_name}",
                "table_name": table,
                "column_name": col_name,
                "column_type": col_type,
                "is_primary_key": is_pk,
                "node_type": "atomic_column",
            })
    return nodes, tables


def build_fk_edges(conn, tables):
    edges = []
    for table in sorted(tables):
        fks = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        for fk in fks:
            ref_table = fk[2]
            from_col = fk[3]
            to_col = fk[4]

            if ref_table in SKIP_TABLES:
                continue

            edges.append({
                "_from": f"{VERTEX_COLLECTION}/{table}.{from_col}",
                "_to": f"{VERTEX_COLLECTION}/{ref_table}.{to_col}",
                "relationship": "FOREIGN_KEY",
                "solder_type": "binary",
                "from_table": table,
                "from_column": from_col,
                "to_table": ref_table,
                "to_column": to_col,
            })
    return edges


def build_table_to_column_edges(nodes):
    edges = []
    for n in nodes:
        edges.append({
            "_from": f"{VERTEX_COLLECTION}/table_{n['table_name']}",
            "_to": f"{VERTEX_COLLECTION}/{n['_key']}",
            "relationship": "HAS_COLUMN",
            "solder_type": "structural",
        })
    return edges


def main():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row

    nodes, tables = build_column_nodes(conn)
    fk_edges = build_fk_edges(conn, tables)
    has_col_edges = build_table_to_column_edges(nodes)
    conn.close()

    print(f"Column nodes to create : {len(nodes)}")
    print(f"ATOMIC_FK edges        : {len(fk_edges)}")
    print(f"HAS_COLUMN edges       : {len(has_col_edges)}")

    config = ArangoDBConfig()
    persistence = ArangoDBGraphPersistence(config)

    edge_defs = [
        {
            "edge_collection": ATOMIC_EDGE_COLLECTION,
            "from_vertex_collections": [VERTEX_COLLECTION],
            "to_vertex_collections": [VERTEX_COLLECTION],
        },
        {
            "edge_collection": "HAS_COLUMN",
            "from_vertex_collections": [VERTEX_COLLECTION],
            "to_vertex_collections": [VERTEX_COLLECTION],
        },
    ]
    persistence._ensure_graph(GRAPH_NAME, edge_defs)

    col_coll = persistence._ensure_collection(VERTEX_COLLECTION)
    atomic_coll = persistence._ensure_collection(ATOMIC_EDGE_COLLECTION, edge=True)
    has_col_coll = persistence._ensure_collection("HAS_COLUMN", edge=True)

    result = col_coll.import_bulk(nodes, on_duplicate="ignore")
    created_nodes = result.get("created", 0)

    for e in fk_edges:
        key = f"{e['from_table']}.{e['from_column']}___{e['to_table']}.{e['to_column']}"
        e["_key"] = key.replace(".", "_")
    result = atomic_coll.import_bulk(fk_edges, on_duplicate="ignore")
    created_fk = result.get("created", 0)

    for e in has_col_edges:
        to_key = e["_to"].split("/")[1]
        e["_key"] = f"hc_{to_key}".replace(".", "_")
    result = has_col_coll.import_bulk(has_col_edges, on_duplicate="ignore")
    created_hc = result.get("created", 0)

    print(f"\nPersisted (new only):")
    print(f"  Column nodes : {created_nodes}")
    print(f"  ATOMIC_FK    : {created_fk}")
    print(f"  HAS_COLUMN   : {created_hc}")

    print("\n--- Forward Traversal Test: production_schedule columns ---")
    db = persistence._db
    cursor = db.aql.execute(f'''
        FOR col IN {VERTEX_COLLECTION}
            FILTER col.table_name == "production_schedule"
               AND col.node_type == "atomic_column"
            LET solder_points = (
                FOR v, e IN 1..1 OUTBOUND col._id GRAPH "{GRAPH_NAME}"
                    FILTER IS_SAME_COLLECTION("{ATOMIC_EDGE_COLLECTION}", e)
                    RETURN {{
                        target: v._key,
                        relationship: e.relationship,
                        solder_type: e.solder_type
                    }}
            )
            RETURN {{
                column: col._key,
                type: col.column_type,
                is_pk: col.is_primary_key,
                solder_points: solder_points
            }}
    ''')
    for doc in cursor:
        sp = doc["solder_points"]
        marker = f" -> {sp[0]['target']}" if sp else ""
        print(f"  {doc['column']} ({doc['type']}){marker}")

    print("\n--- Backward Traversal Test: What depends on production_lines.line_id? ---")
    cursor = db.aql.execute(f'''
        FOR col_target IN {VERTEX_COLLECTION}
            FILTER col_target._key == "production_lines.line_id"

            FOR v, e IN 1..1 INBOUND col_target._id GRAPH "{GRAPH_NAME}"
                FILTER IS_SAME_COLLECTION("{ATOMIC_EDGE_COLLECTION}", e)
                RETURN {{
                    dependent_table: v.table_name,
                    dependent_column: v.column_name,
                    solder_type: e.solder_type
                }}
    ''')
    results = list(cursor)
    if results:
        for r in results:
            print(f"  {r['dependent_table']}.{r['dependent_column']}  --FK-->  production_lines.line_id")
    else:
        print("  (no inbound FK edges found)")

    print("\n--- Backward Traversal Test: What depends on equipment_metrics.equipment_id? ---")
    cursor = db.aql.execute(f'''
        FOR col_target IN {VERTEX_COLLECTION}
            FILTER col_target._key == "equipment_metrics.equipment_id"

            FOR v, e IN 1..1 INBOUND col_target._id GRAPH "{GRAPH_NAME}"
                FILTER IS_SAME_COLLECTION("{ATOMIC_EDGE_COLLECTION}", e)
                RETURN {{
                    dependent_table: v.table_name,
                    dependent_column: v.column_name,
                    solder_type: e.solder_type
                }}
    ''')
    results = list(cursor)
    if results:
        for r in results:
            print(f"  {r['dependent_table']}.{r['dependent_column']}  --FK-->  equipment_metrics.equipment_id")
    else:
        print("  (no inbound FK edges found)")

    print("\nDone.")


if __name__ == "__main__":
    main()
