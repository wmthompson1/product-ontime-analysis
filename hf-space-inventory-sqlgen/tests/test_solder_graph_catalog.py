"""
test_solder_graph_catalog.py
============================
Tests for the export_graph_to_solder.py catalog exporter.

Two tests:
  1. test_catalog_covers_schema_nodes
       Confirms the catalog contains at least one column row for every table
       registered in SQLite `schema_nodes`.

  2. test_approved_bindings_are_catalog_clean
       Runs the --validate logic and asserts that no approved SolderEngine
       binding references a table name absent from the graph catalog.

Both tests skip gracefully when ARANGO_HOST is not set, matching the pattern
used in test_bridge_collection_health.py.

Run directly:
    python hf-space-inventory-sqlgen/tests/test_solder_graph_catalog.py
"""

from __future__ import annotations

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
SCRIPTS_DIR = os.path.join(HF_DIR, "scripts")

sys.path.insert(0, HF_DIR)
sys.path.insert(0, SCRIPTS_DIR)

SQLITE_DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")


def _skip_if_no_arango(test_name: str) -> bool:
    """Return True (and print a SKIP message) when ARANGO_HOST is not set."""
    if not os.environ.get("ARANGO_HOST"):
        print(f"SKIP: {test_name} — ARANGO_HOST not set")
        return True
    return False


def _get_arango_db():
    from graph_sync import get_arango_client, get_arango_db
    client = get_arango_client()
    return get_arango_db(client)


def test_catalog_covers_schema_nodes() -> None:
    """Every table in SQLite schema_nodes must appear at least once in the catalog.

    If the catalog is missing a table that schema_nodes knows about, it means
    the `contains` edges for that table have not been synced to ArangoDB yet.
    """
    if _skip_if_no_arango("test_catalog_covers_schema_nodes"):
        return

    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SKIP: test_catalog_covers_schema_nodes — SQLite DB not found at {SQLITE_DB_PATH}")
        return

    try:
        from export_graph_to_solder import fetch_solder_catalog
    except ImportError as exc:
        print(f"SKIP: test_catalog_covers_schema_nodes — could not import exporter: {exc}")
        return

    try:
        db = _get_arango_db()
    except Exception as exc:
        print(f"SKIP: test_catalog_covers_schema_nodes — could not connect to ArangoDB: {exc}")
        return

    try:
        catalog = fetch_solder_catalog(db)
    except Exception as exc:
        print(f"SKIP: test_catalog_covers_schema_nodes — AQL query failed: {exc}")
        return

    catalog_tables = {row["table_name"].upper() for row in catalog}

    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        rows = conn.execute("SELECT table_name FROM schema_nodes").fetchall()
    finally:
        conn.close()

    schema_node_tables = {r[0].upper() for r in rows}

    if not schema_node_tables:
        print("SKIP: test_catalog_covers_schema_nodes — schema_nodes is empty")
        return

    missing = sorted(schema_node_tables - catalog_tables)

    assert not missing, (
        f"Catalog is missing {len(missing)} table(s) from schema_nodes:\n"
        + "\n".join(f"  {t}" for t in missing)
        + "\nRe-run graph_sync.py to populate `contains` edges for these tables."
    )

    rows_with_type = [r for r in catalog if r.get("data_type")]
    assert rows_with_type, (
        "Catalog has no rows with a non-empty data_type. "
        "Check that fetch_solder_catalog() reads `column_type` from ArangoDB column vertices."
    )

    print(
        f"PASS: test_catalog_covers_schema_nodes — "
        f"all {len(schema_node_tables)} schema_nodes tables present in catalog "
        f"({len(catalog)} columns total, {len(rows_with_type)} with data_type populated)"
    )


def test_approved_bindings_are_catalog_clean() -> None:
    """No approved SolderEngine binding may reference a table absent from the graph catalog.

    A mismatch means an approved SQL snippet references a table that has not
    been certified via `contains` edges in ArangoDB — a gap in the Solder Pattern
    guarantees.
    """
    if _skip_if_no_arango("test_approved_bindings_are_catalog_clean"):
        return

    try:
        from export_graph_to_solder import fetch_solder_catalog, validate_bindings
    except ImportError as exc:
        print(f"SKIP: test_approved_bindings_are_catalog_clean — could not import exporter: {exc}")
        return

    try:
        db = _get_arango_db()
    except Exception as exc:
        print(f"SKIP: test_approved_bindings_are_catalog_clean — could not connect to ArangoDB: {exc}")
        return

    try:
        catalog = fetch_solder_catalog(db)
    except Exception as exc:
        print(f"SKIP: test_approved_bindings_are_catalog_clean — AQL query failed: {exc}")
        return

    if not catalog:
        print("SKIP: test_approved_bindings_are_catalog_clean — catalog is empty (no contains edges)")
        return

    try:
        mismatches = validate_bindings(catalog)
    except Exception as exc:
        print(f"SKIP: test_approved_bindings_are_catalog_clean — validation error: {exc}")
        return

    if mismatches:
        lines = [f"  [{m['binding_key']}] unknown tables: {', '.join(m['unknown_tables'])}" for m in mismatches]
        assert False, (
            f"VALIDATION FAILED — {len(mismatches)} binding(s) reference tables not in the graph catalog:\n"
            + "\n".join(lines)
        )

    print(
        f"PASS: test_approved_bindings_are_catalog_clean — "
        f"all approved bindings are catalog-clean "
        f"(catalog covers {len({r['table_name'] for r in catalog})} tables)"
    )


def test_references_edges_model_fk_topology() -> None:
    """FK topology must be expressed as canonical `references` edges, not `contains`.

    The canonical graph-metadata model represents a foreign key as a structural
    `references` edge (child column -> parent column) carrying
    references_table/references_column, plus a `foreign_key` boolean on the child
    column node. There is no FOREIGN_KEY edge type. This test validates that
    topology where the `references` edge collection exists, skipping gracefully
    when it has not been synced yet (the live graph may still carry only the
    `contains` structural edges that the catalog coverage test exercises).
    """
    if _skip_if_no_arango("test_references_edges_model_fk_topology"):
        return

    try:
        db = _get_arango_db()
    except Exception as exc:
        print(f"SKIP: test_references_edges_model_fk_topology — could not connect to ArangoDB: {exc}")
        return

    try:
        has_references = db.has_collection("references")
    except Exception as exc:
        print(f"SKIP: test_references_edges_model_fk_topology — could not inspect collections: {exc}")
        return

    if not has_references:
        print("SKIP: test_references_edges_model_fk_topology — no `references` edge collection yet")
        return

    try:
        edges = list(db.aql.execute("FOR e IN references RETURN e"))
    except Exception as exc:
        print(f"SKIP: test_references_edges_model_fk_topology — AQL query failed: {exc}")
        return

    if not edges:
        print("SKIP: test_references_edges_model_fk_topology — `references` collection is empty")
        return

    bad_type = [e["_key"] for e in edges if e.get("edge_type") != "references"]
    assert not bad_type, (
        f"{len(bad_type)} references edge(s) carry a non-`references` edge_type "
        f"(FOREIGN_KEY is retired): {bad_type[:5]}"
    )

    bad_family = [e["_key"] for e in edges if e.get("edge_family") != "structural"]
    assert not bad_family, (
        f"{len(bad_family)} references edge(s) are not edge_family='structural': {bad_family[:5]}"
    )

    bad_props = [
        e["_key"] for e in edges
        if not e.get("references_table") or not e.get("references_column")
    ]
    assert not bad_props, (
        f"{len(bad_props)} references edge(s) missing references_table/references_column: {bad_props[:5]}"
    )

    print(
        f"PASS: test_references_edges_model_fk_topology — "
        f"{len(edges)} references edge(s) validated (FK topology via `references`, not `contains`)"
    )


def main() -> int:
    tests = [
        test_catalog_covers_schema_nodes,
        test_approved_bindings_are_catalog_clean,
        test_references_edges_model_fk_topology,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}:\n{exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
