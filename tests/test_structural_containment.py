"""
tests/test_structural_containment.py
=====================================
Tests for Plan-007: Graph Structural Containment

Covers:
  - arangodb_helpers model: key conventions, document builders
  - graph_sync: load_schema_containment_data populates tables + columns
  - graph_sync: EDGE_DEFINITIONS includes 'contains'
  - graph_sync: VERTEX_COLLECTIONS includes 'tables' and 'columns'
  - ArangoDB integration (skipped when ArangoDB is offline)
"""

import os
import sys
import sqlite3
import tempfile
import unittest

# Make hf-space-inventory-sqlgen importable
_HERE = os.path.dirname(__file__)
_HF = os.path.join(_HERE, "..", "hf-space-inventory-sqlgen")
if _HF not in sys.path:
    sys.path.insert(0, _HF)


# ---------------------------------------------------------------------------
# Model layer tests (no DB, no network)
# ---------------------------------------------------------------------------

class TestSchemaModelConstants(unittest.TestCase):
    def setUp(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import (
            TABLES_COLLECTION, COLUMNS_COLLECTION, CONTAINS_EDGE_COLLECTION,
        )
        self.TABLES = TABLES_COLLECTION
        self.COLUMNS = COLUMNS_COLLECTION
        self.CONTAINS = CONTAINS_EDGE_COLLECTION

    def test_collection_name_tables(self):
        self.assertEqual(self.TABLES, "tables")

    def test_collection_name_columns(self):
        self.assertEqual(self.COLUMNS, "columns")

    def test_collection_name_contains(self):
        self.assertEqual(self.CONTAINS, "contains")


class TestColumnKey(unittest.TestCase):
    def setUp(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import column_key
        self.column_key = column_key

    def test_double_underscore_separator(self):
        self.assertEqual(
            self.column_key("corrective_actions", "capa_id"),
            "corrective_actions__capa_id",
        )

    def test_no_dot_in_key(self):
        key = self.column_key("products", "product_id")
        self.assertNotIn(".", key)

    def test_different_table_same_column_name_are_distinct(self):
        k1 = self.column_key("products", "status")
        k2 = self.column_key("suppliers", "status")
        self.assertNotEqual(k1, k2)


class TestContainsEdgeKey(unittest.TestCase):
    def test_matches_column_key(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import (
            column_key, contains_edge_key,
        )
        t, c = "daily_deliveries", "delivery_date"
        self.assertEqual(contains_edge_key(t, c), column_key(t, c))


class TestTableVertex(unittest.TestCase):
    def setUp(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import table_vertex
        self.tv = table_vertex("production_orders", description="PO lines", synced_at="T")

    def test_key_equals_table_name(self):
        self.assertEqual(self.tv["_key"], "production_orders")

    def test_qualified_name_uppercase(self):
        self.assertEqual(self.tv["qualified_name"], "dbo.PRODUCTION_ORDERS")

    def test_node_type_is_table(self):
        self.assertEqual(self.tv["node_type"], "table")

    def test_description_preserved(self):
        self.assertEqual(self.tv["description"], "PO lines")


class TestColumnVertex(unittest.TestCase):
    def setUp(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import column_vertex
        self.cv = column_vertex(
            "corrective_actions", "capa_id",
            data_type="INTEGER", not_null=True, pk=True, synced_at="T",
        )

    def test_key_format(self):
        self.assertEqual(self.cv["_key"], "corrective_actions__capa_id")

    def test_qualified_name_uses_dot(self):
        self.assertEqual(self.cv["qualified_name"], "corrective_actions.capa_id")

    def test_node_type_is_column(self):
        self.assertEqual(self.cv["node_type"], "column")

    def test_primary_key_flag(self):
        self.assertTrue(self.cv["primary_key"])

    def test_not_null_flag(self):
        self.assertTrue(self.cv["not_null"])

    def test_data_type_preserved(self):
        self.assertEqual(self.cv["data_type"], "INTEGER")


class TestContainsEdgeDoc(unittest.TestCase):
    def setUp(self):
        from arangodb_helpers.manufacturing_graph_version_0_0_1 import contains_edge
        self.ed = contains_edge("daily_deliveries", "delivery_date", synced_at="T")

    def test_from_is_table(self):
        self.assertEqual(self.ed["_from"], "tables/daily_deliveries")

    def test_to_is_column(self):
        self.assertEqual(self.ed["_to"], "columns/daily_deliveries__delivery_date")

    def test_relationship_label(self):
        self.assertEqual(self.ed["relationship"], "CONTAINS")


# ---------------------------------------------------------------------------
# graph_sync collection / edge-definition registration
# ---------------------------------------------------------------------------

class TestGraphSyncCollections(unittest.TestCase):
    def setUp(self):
        import graph_sync as gs
        self.gs = gs

    def test_tables_in_vertex_collections(self):
        self.assertIn("tables", self.gs.VERTEX_COLLECTIONS)

    def test_columns_in_vertex_collections(self):
        self.assertIn("columns", self.gs.VERTEX_COLLECTIONS)

    def test_contains_in_edge_collections(self):
        self.assertIn("contains", self.gs.EDGE_COLLECTIONS)

    def test_contains_edge_definition_present(self):
        defs = {ed["edge_collection"] for ed in self.gs.EDGE_DEFINITIONS}
        self.assertIn("contains", defs)

    def test_contains_edge_def_from_to(self):
        contains_def = next(
            ed for ed in self.gs.EDGE_DEFINITIONS
            if ed["edge_collection"] == "contains"
        )
        self.assertIn("tables", contains_def["from_vertex_collections"])
        self.assertIn("columns", contains_def["to_vertex_collections"])


# ---------------------------------------------------------------------------
# load_schema_containment_data — in-memory SQLite fixture
# ---------------------------------------------------------------------------

class TestLoadSchemaContainmentData(unittest.TestCase):
    def setUp(self):
        """Create a minimal in-memory SQLite DB with schema_nodes + 2 ERP tables."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE schema_nodes (
                table_name TEXT NOT NULL,
                table_type TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO schema_nodes VALUES ('alpha_table', 'Table', 'Alpha desc', '2026-01-01');
            INSERT INTO schema_nodes VALUES ('beta_table',  'Table', 'Beta desc',  '2026-01-01');
            INSERT INTO schema_nodes VALUES ('v_view',      'View',  'A view',     '2026-01-01');

            CREATE TABLE alpha_table (
                alpha_id INTEGER PRIMARY KEY,
                label    TEXT NOT NULL
            );
            CREATE TABLE beta_table (
                beta_id INTEGER PRIMARY KEY,
                value   REAL,
                flag    INTEGER NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _load(self):
        import graph_sync as gs
        return gs.load_schema_containment_data(self.db_path)

    def test_tables_excludes_views(self):
        data = self._load()
        names = [t["table_name"] for t in data["tables"]]
        self.assertIn("alpha_table", names)
        self.assertIn("beta_table", names)
        self.assertNotIn("v_view", names)

    def test_table_count(self):
        data = self._load()
        self.assertEqual(len(data["tables"]), 2)

    def test_columns_populated(self):
        data = self._load()
        col_names = [(c["table_name"], c["column_name"]) for c in data["columns"]]
        self.assertIn(("alpha_table", "alpha_id"), col_names)
        self.assertIn(("alpha_table", "label"), col_names)
        self.assertIn(("beta_table", "beta_id"), col_names)
        self.assertIn(("beta_table", "value"), col_names)
        self.assertIn(("beta_table", "flag"), col_names)

    def test_column_count(self):
        data = self._load()
        self.assertEqual(len(data["columns"]), 5)

    def test_primary_key_flag(self):
        data = self._load()
        pk_cols = [c for c in data["columns"] if c["pk"]]
        pk_names = [(c["table_name"], c["column_name"]) for c in pk_cols]
        self.assertIn(("alpha_table", "alpha_id"), pk_names)
        self.assertIn(("beta_table", "beta_id"), pk_names)

    def test_not_null_flag(self):
        data = self._load()
        nn = {(c["table_name"], c["column_name"]): c["not_null"] for c in data["columns"]}
        self.assertTrue(nn[("alpha_table", "label")])
        self.assertTrue(nn[("beta_table", "flag")])
        self.assertFalse(nn[("beta_table", "value")])

    def test_description_passed_through(self):
        data = self._load()
        alpha = next(t for t in data["tables"] if t["table_name"] == "alpha_table")
        self.assertEqual(alpha["description"], "Alpha desc")


# ---------------------------------------------------------------------------
# ArangoDB integration (live) — skipped when offline
# ---------------------------------------------------------------------------

def _arango_available() -> bool:
    try:
        import graph_sync as gs
        client = gs.get_arango_client()
        db = gs.get_arango_db(client)
        return db is not None
    except Exception:
        return False


@unittest.skipUnless(_arango_available(), "ArangoDB not reachable")
class TestArangoContainmentCollections(unittest.TestCase):
    def setUp(self):
        import graph_sync as gs
        self.gs = gs
        self.client = gs.get_arango_client()
        self.db = gs.get_arango_db(self.client)
        gs.ensure_graph(self.db)

    def test_tables_collection_exists(self):
        self.assertTrue(self.db.has_collection("tables"))

    def test_columns_collection_exists(self):
        self.assertTrue(self.db.has_collection("columns"))

    def test_contains_edge_def_in_named_graph(self):
        graph = self.db.graph(self.gs.GRAPH_NAME)
        edge_defs = {ed["edge_collection"] for ed in graph.edge_definitions()}
        self.assertIn("contains", edge_defs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
