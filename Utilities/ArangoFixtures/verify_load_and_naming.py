"""
Verify SQLite-to-ArangoDB Load & Object Naming
=================================================
Run this after syncing the repo to confirm:

  1. ARANGO_DB env var is set and matches graph/collection names
  2. SQLite source exists and has the expected tables
  3. ArangoDB database, graph, and collections exist with correct names
  4. Atomic column nodes loaded (count + _key format)
  5. FK edges loaded (count + direction)
  6. Forward round-trip: every SQLite column appears in the graph
  7. get_information_schema() output matches raw AQL exactly

Usage:
    python Utilities/ArangoFixtures/verify_load_and_naming.py

Requires: ARANGO_HOST, ARANGO_USER, ARANGO_ROOT_PASSWORD, ARANGO_DB
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

passed = 0
failed = 0


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f"  — {detail}"
        print(msg)


def section(title):
    print()
    print("-" * 60)
    print(f"  {title}")
    print("-" * 60)


def main():
    global passed, failed

    print("=" * 60)
    print("  VERIFY: SQLite → ArangoDB Load & Object Naming")
    print("=" * 60)

    section("1. Environment Variable")

    arango_db = os.getenv("ARANGO_DB")
    check("ARANGO_DB is set", arango_db is not None,
          "Set ARANGO_DB=manufacturing_graph in your .env or environment")
    if not arango_db:
        print("\n  Cannot continue without ARANGO_DB. Exiting.")
        sys.exit(1)

    expected_db = "manufacturing_graph"
    check(f"ARANGO_DB == '{expected_db}'", arango_db == expected_db,
          f"Got '{arango_db}'")

    graph_name = arango_db
    vertex_coll = f"{graph_name}_node"
    edge_coll = f"{graph_name}_edge"
    atomic_fk_coll = "ATOMIC_FK"
    has_column_coll = "HAS_COLUMN"

    print(f"\n  Derived names:")
    print(f"    Database:          {graph_name}")
    print(f"    Graph:             {graph_name}")
    print(f"    Vertex collection: {vertex_coll}")
    print(f"    Edge collection:   {edge_coll}")
    print(f"    Atomic FK edges:   {atomic_fk_coll}")
    print(f"    HAS_COLUMN edges:  {has_column_coll}")

    section("2. SQLite Source")

    check("SQLite file exists", os.path.isfile(SQLITE_PATH), SQLITE_PATH)
    if not os.path.isfile(SQLITE_PATH):
        print("\n  Cannot continue without SQLite. Exiting.")
        sys.exit(1)

    conn = sqlite3.connect(SQLITE_PATH)
    all_tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if r[0] not in SKIP_TABLES
    ]

    check(f"SQLite has tables (found {len(all_tables)})", len(all_tables) > 0)

    sqlite_col_count = 0
    sqlite_fk_count = 0
    for table in all_tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        fks = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        fks = [fk for fk in fks if fk[2] not in SKIP_TABLES]
        sqlite_col_count += len(cols)
        sqlite_fk_count += len(fks)

    print(f"\n  SQLite summary:")
    print(f"    Tables:  {len(all_tables)}")
    print(f"    Columns: {sqlite_col_count}")
    print(f"    FKs:     {sqlite_fk_count}")

    section("3. ArangoDB Connection & Objects")

    try:
        config = ArangoDBConfig()
        persistence = ArangoDBGraphPersistence(config)
        db = persistence._db
        check("ArangoDB connection succeeded", True)
    except Exception as e:
        check("ArangoDB connection succeeded", False, str(e))
        conn.close()
        print("\n  Cannot continue without ArangoDB. Exiting.")
        sys.exit(1)

    check(f"Database name is '{graph_name}'", db.name == graph_name,
          f"Got '{db.name}'")

    graphs = db.graphs()
    graph_names = [g["name"] for g in graphs]
    check(f"Named graph '{graph_name}' exists", graph_name in graph_names,
          f"Found: {graph_names}")

    collections = [c["name"] for c in db.collections() if not c["name"].startswith("_")]
    check(f"Vertex collection '{vertex_coll}' exists", vertex_coll in collections)
    if edge_coll in collections:
        check(f"Edge collection '{edge_coll}' exists (semantic edges)", True)
    else:
        check(f"Edge collection '{edge_coll}' absent (uses named edge collections instead)", True)
    check(f"Edge collection '{atomic_fk_coll}' exists", atomic_fk_coll in collections)
    check(f"Edge collection '{has_column_coll}' exists", has_column_coll in collections)

    section("4. Atomic Column Nodes")

    node_count = db.collection(vertex_coll).count()
    check(f"Vertex count > 0 (found {node_count})", node_count > 0)

    atomic_nodes = list(db.aql.execute(
        "FOR n IN @@coll FILTER n.node_type == 'atomic_column' RETURN n",
        bind_vars={"@coll": vertex_coll}
    ))
    check(f"Atomic column nodes == SQLite columns ({sqlite_col_count})",
          len(atomic_nodes) == sqlite_col_count,
          f"Got {len(atomic_nodes)}")

    bad_keys = [n["_key"] for n in atomic_nodes if "." not in n["_key"]]
    check("All atomic _keys use table.column format",
          len(bad_keys) == 0,
          f"Bad keys: {bad_keys[:5]}")

    missing_fields = []
    for n in atomic_nodes[:5]:
        for field in ["table_name", "column_name", "data_type", "is_primary_key", "node_type"]:
            if field not in n:
                missing_fields.append(f"{n['_key']}.{field}")
    check("Atomic nodes have required fields (sample of 5)",
          len(missing_fields) == 0,
          f"Missing: {missing_fields}")

    graph_tables = set(n["table_name"] for n in atomic_nodes)
    check(f"Graph tables == SQLite tables ({len(all_tables)})",
          graph_tables == set(all_tables),
          f"Diff: {graph_tables.symmetric_difference(set(all_tables))}")

    section("5. FK Edges")

    if atomic_fk_coll in collections:
        fk_edge_count = db.collection(atomic_fk_coll).count()
        check(f"ATOMIC_FK edges == SQLite FKs ({sqlite_fk_count})",
              fk_edge_count == sqlite_fk_count,
              f"Got {fk_edge_count}")

        fk_edges = list(db.aql.execute(
            "FOR e IN ATOMIC_FK RETURN e"
        ))
        bad_fk = [e["_key"] for e in fk_edges
                   if not e["_from"].startswith(f"{vertex_coll}/")
                   or not e["_to"].startswith(f"{vertex_coll}/")]
        check("FK edges reference correct vertex collection",
              len(bad_fk) == 0,
              f"Bad refs: {bad_fk[:3]}")

        fk_with_flag = [e for e in fk_edges if e.get("is_foreign_key") == True]
        check("All FK edges have is_foreign_key=true",
              len(fk_with_flag) == len(fk_edges),
              f"{len(fk_with_flag)}/{len(fk_edges)}")
    else:
        check("ATOMIC_FK collection exists", False, "Not found")

    section("6. Forward Round-Trip (SQLite cols vs Graph nodes)")

    mismatch_count = 0
    for table in all_tables:
        sqlite_cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        graph_cols = list(db.aql.execute(
            '''FOR n IN @@coll
               FILTER n.table_name == @t AND n.node_type == "atomic_column"
               RETURN n.column_name''',
            bind_vars={"@coll": vertex_coll, "t": table}
        ))

        sqlite_names = {c[1] for c in sqlite_cols}
        graph_names = set(graph_cols)

        if sqlite_names != graph_names:
            mismatch_count += 1
            diff = sqlite_names.symmetric_difference(graph_names)
            print(f"    {table}: column mismatch — {diff}")

    check(f"All {len(all_tables)} tables have matching columns",
          mismatch_count == 0,
          f"{mismatch_count} tables with mismatches")

    conn.close()

    section("7. get_information_schema() vs Raw AQL")

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "hf-space-inventory-sqlgen"
    ))
    from solder_engine_extended import SolderEngineExtended

    engine = SolderEngineExtended(
        db_path=SQLITE_PATH,
        manifest_path=os.path.join(
            os.path.dirname(SQLITE_PATH), "ground_truth", "reviewer_manifest.json"
        )
    )

    test_tables = ["production_lines", "downtime_events", "equipment_metrics", "suppliers"]
    for table in test_tables:
        result = engine.get_information_schema(table)
        raw = engine.get_raw_graph_nodes(table)

        info_map = {c.column_name: {
            "data_type": c.data_type,
            "is_primary_key": c.is_primary_key,
            "is_foreign_key": c.is_foreign_key,
            "references_table": c.references_table,
            "references_column": c.references_column,
        } for c in result.columns}

        raw_map = {r["column_name"]: {
            "data_type": r["data_type"],
            "is_primary_key": r["is_primary_key"],
            "is_foreign_key": r["is_foreign_key"],
            "references_table": r.get("references_table"),
            "references_column": r.get("references_column"),
        } for r in raw}

        check(f"{table}: info_schema == raw AQL ({len(info_map)} cols)",
              info_map == raw_map)

    print()
    print("=" * 60)
    total = passed + failed
    print(f"  RESULT: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("  ALL CHECKS PASSED")
    else:
        print("  FAILURES DETECTED — review output above")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
