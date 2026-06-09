"""Tests for the SQLite graph source tables (sql_graph_nodes / sql_graph_edges).

These guard the contract that the exporter materializes the canonical graph into
SQLite and then serializes the JSON FROM those tables — so SQLite is a provable
source of truth for graph_metadata.json. They cover:

  * round-trip fidelity (materialize → read back == original dicts, exact fields)
  * emission ordering preserved via the ``ordinal`` column
  * idempotency (materializing twice yields identical rows)
  * the document built from the tables matches the document built directly
  * the committed manufacturing.db and graph_metadata.json are in parity
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "replit_integrations"))

import export_graph_metadata as ex  # noqa: E402
import sql_graph_parity_check as parity  # noqa: E402


def _sample_graph():
    """A small but representative slice mirroring the exporter's dict shapes."""
    table_nodes = [
        {
            "_id": f"{ex.NODE_COLLECTION}/CUSTOMER",
            "_key": "CUSTOMER",
            "node_type": "table",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_slot": ex.PLACEHOLDER_ENTITY,
            "predicate": "none",
            "unique_id": "none",
            "description": "Customer master",
        },
    ]
    column_nodes = [
        {
            "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "_key": "column::CUSTOMER.ID",
            "node_type": "column",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_name": "ID",
            "predicate": "none",
            "unique_id": "none",
            "column_type": "INTEGER",
            "notnull": True,
            "default_value": None,
            "primary_key": True,
            "foreign_key": False,
        },
        {
            "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_key": "column::CUSTOMER.NAME",
            "node_type": "column",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_name": "NAME",
            "predicate": "none",
            "unique_id": "none",
            "column_type": "TEXT",
            "notnull": False,
            "default_value": "'anon'",
            "primary_key": False,
            "foreign_key": False,
        },
    ]
    edges = [
        {
            "_id": f"{ex.EDGE_COLLECTION}/hc_CUSTOMER_ID",
            "_key": "hc_CUSTOMER_ID",
            "_from": f"{ex.NODE_COLLECTION}/CUSTOMER",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "edge_family": ex.FAMILY_STRUCTURAL,
            "edge_type": ex.EDGE_PREDICATE_HAS_COLUMN,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "unique_id": "CUS_HAS_ID_001",
        },
        {
            "_id": f"{ex.EDGE_COLLECTION}/ref_ORDER_CUSTOMER",
            "_key": "ref_ORDER_CUSTOMER",
            "_from": f"{ex.NODE_COLLECTION}/column::ORDER.CUSTOMER_ID",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "edge_family": ex.FAMILY_STRUCTURAL,
            "edge_type": ex.EDGE_PREDICATE_REFERENCES,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "unique_id": "none",
            "references_table": "CUSTOMER",
            "references_column": "ID",
        },
        {
            "_id": f"{ex.EDGE_COLLECTION}/ele_CUSTOMER_NAME",
            "_key": "ele_CUSTOMER_NAME",
            "_from": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "edge_family": ex.FAMILY_SEMANTIC,
            "edge_type": ex.EDGE_PREDICATE_ELEVATES,
            "perspective": "Sales",
            "unique_id": "SAL_ELE_CUS_NAM_001",
            "weight": 3,
            "concept": "CustomerNameSales",
        },
    ]
    return table_nodes, column_nodes, edges


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_materialize_then_load_is_exact(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)

        loaded_nodes = ex._load_nodes_from_sqlite(self.conn)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)

        # Exact field set + values + ordering (table nodes precede column nodes).
        self.assertEqual(loaded_nodes, table_nodes + column_nodes)
        self.assertEqual(loaded_edges, edges)

    def test_row_counts_match_inputs(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        n_nodes = self.conn.execute(
            f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_NODES_TABLE}"
        ).fetchone()[0]
        n_edges = self.conn.execute(
            f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_EDGES_TABLE}"
        ).fetchone()[0]
        self.assertEqual(n_nodes, len(table_nodes) + len(column_nodes))
        self.assertEqual(n_edges, len(edges))

    def test_materialize_is_idempotent(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        first_nodes = ex._load_nodes_from_sqlite(self.conn)
        first_edges = ex._load_edges_from_sqlite(self.conn)

        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        second_nodes = ex._load_nodes_from_sqlite(self.conn)
        second_edges = ex._load_edges_from_sqlite(self.conn)

        self.assertEqual(first_nodes, second_nodes)
        self.assertEqual(first_edges, second_edges)
        self.assertEqual(
            self.conn.execute(f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_NODES_TABLE}").fetchone()[0],
            len(table_nodes) + len(column_nodes),
        )

    def test_document_from_tables_matches_direct(self):
        table_nodes, column_nodes, edges = _sample_graph()
        integrity = {
            "tables_without_columns": [],
            "foreign_keys_skipped": [],
            "semantic_elevations_skipped": [],
        }
        direct = ex._build_graph_document(table_nodes + column_nodes, edges, integrity)

        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        from_tables = ex._build_graph_document(
            ex._load_nodes_from_sqlite(self.conn),
            ex._load_edges_from_sqlite(self.conn),
            integrity,
        )

        # Ignore the volatile document timestamp; everything else must match.
        direct.pop("synced_at", None)
        from_tables.pop("synced_at", None)
        self.assertEqual(direct, from_tables)


class CommittedParity(unittest.TestCase):
    def test_committed_db_matches_committed_json(self):
        if not (os.path.exists(ex.DB_PATH) and os.path.exists(ex.JSON_PATH)):
            self.skipTest("committed manufacturing.db or graph_metadata.json not present")
        # If the tables have not been materialized yet, treat as a skip rather
        # than a failure (the post-merge gate uses the strict, non-skip mode).
        rc = parity.check_parity(ex.DB_PATH, ex.JSON_PATH, skip_on_missing=True)
        self.assertEqual(rc, 0, "committed graph_metadata.json is not in parity with the SQLite graph tables")


if __name__ == "__main__":
    unittest.main()
