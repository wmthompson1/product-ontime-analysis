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
            "field_component": 1,
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

    def test_field_component_round_trips_for_multiple_definitions(self):
        """A field with N definitions yields N elevates edges numbered 1..N, and
        ``field_component`` survives the materialize → read-back round trip."""
        table_nodes, column_nodes, edges = _sample_graph()
        # Give CUSTOMER.NAME a second meaning (component 2) under another
        # perspective — same source column, distinct definition.
        edges.append({
            "_id": f"{ex.EDGE_COLLECTION}/ele_CUSTOMER_NAME_2",
            "_key": "ele_CUSTOMER_NAME_2",
            "_from": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "edge_family": ex.FAMILY_SEMANTIC,
            "edge_type": ex.EDGE_PREDICATE_ELEVATES,
            "perspective": "Marketing",
            "unique_id": "MAR_ELE_CUS_NAM_001",
            "weight": 3,
            "concept": "CustomerNameMarketing",
            "field_component": 2,
        })
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)
        self.assertEqual(loaded_edges, edges)

        elevates = [e for e in loaded_edges
                    if e["edge_type"] == ex.EDGE_PREDICATE_ELEVATES]
        self.assertEqual(
            sorted(e["field_component"] for e in elevates), [1, 2],
            "two definitions of one field must carry field_component 1 and 2",
        )

    def test_non_elevates_edges_omit_field_component(self):
        """field_component is an elevates-only attribute; structural edges never
        carry it (its column is NULL for them and absent from their dict)."""
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)
        for e in loaded_edges:
            if e["edge_type"] != ex.EDGE_PREDICATE_ELEVATES:
                self.assertNotIn("field_component", e)

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


# The sql_graph_nodes shape that predates the concept node type: node_type CHECK
# admits only table/column, table_name is NOT NULL, and there is no concept_name
# column. This is what an old manufacturing.db carries before M1.
_LEGACY_NODES_DDL = """
CREATE TABLE sql_graph_nodes (
    ordinal       INTEGER NOT NULL,
    _key          TEXT    NOT NULL PRIMARY KEY,
    _id           TEXT    NOT NULL,
    node_type     TEXT    NOT NULL CHECK(node_type IN ('table', 'column')),
    node_family   TEXT    NOT NULL,
    perspective   TEXT    NOT NULL,
    table_name    TEXT    NOT NULL,
    column_name   TEXT,
    column_slot   TEXT,
    predicate     TEXT    NOT NULL,
    unique_id     TEXT    NOT NULL,
    description   TEXT,
    column_type   TEXT,
    "notnull"     INTEGER,
    default_value TEXT,
    primary_key   INTEGER,
    foreign_key   INTEGER
);
"""


class LegacyDbMigration(unittest.TestCase):
    """The exporter must rebuild an old sql_graph_nodes even after app.py's boot
    guard has additively bolted on the concept_name column (which leaves the old
    CHECK + table_name NOT NULL intact). Keying the rebuild on the column alone
    would miss this half-migrated state and break concept inserts."""

    def _half_migrated_conn(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(_LEGACY_NODES_DDL)
        # Simulate app.py's additive boot guard adding only the new column.
        conn.execute("ALTER TABLE sql_graph_nodes ADD COLUMN concept_name TEXT")
        return conn

    def test_half_migrated_table_is_detected_stale(self):
        conn = self._half_migrated_conn()
        self.addCleanup(conn.close)
        self.assertTrue(
            ex._sql_graph_nodes_is_stale(conn),
            "old table with concept_name bolted on must still be seen as stale",
        )

    def test_fresh_modern_table_is_not_stale(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(ex.SQL_GRAPH_DDL)
        self.assertFalse(ex._sql_graph_nodes_is_stale(conn))

    def test_ensure_rebuilds_half_migrated_table_so_concept_inserts(self):
        conn = self._half_migrated_conn()
        self.addCleanup(conn.close)

        ex._ensure_sql_graph_tables(conn)

        # A concept row has table_name NULL and node_type 'concept' — both of
        # which the legacy shape rejected. After the rebuild it must insert.
        name = "CertificationType"
        key = ex.concept_key(name)
        conn.execute(
            f"INSERT INTO {ex.SQL_GRAPH_NODES_TABLE} "
            "(ordinal, _key, _id, node_type, node_family, perspective, "
            " table_name, concept_name, predicate, unique_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (1, key, ex.concept_id(name), "concept", ex.FAMILY_SEMANTIC,
             ex.PERSPECTIVE_CANONICAL, None, name, "none", "none"),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT node_type, table_name, concept_name FROM {ex.SQL_GRAPH_NODES_TABLE}"
        ).fetchone()
        self.assertEqual(row, ("concept", None, name))


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
