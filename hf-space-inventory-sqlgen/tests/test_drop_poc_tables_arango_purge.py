"""
Tests for the ArangoDB purge step in migrations/drop_poc_tables.py.

All tests run without a live ArangoDB connection:
  - Graceful-skip paths (missing env vars, SKIP_ARANGO flag, missing package)
  - Key-format correctness (table_key / column_prefix conventions)
  - EMPTY_TABLES completeness (21 entries, all expected names present)

These tests are CI-safe and require no external services.
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# Resolve the migration module path without importing it as a package.
MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "migrations", "drop_poc_tables.py"
)

def _load_migration():
    spec = importlib.util.spec_from_file_location("drop_poc_tables", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEmptyTablesList(unittest.TestCase):
    """Verify the EMPTY_TABLES constant is complete and correctly typed."""

    def setUp(self):
        self.mod = _load_migration()

    def test_count(self):
        self.assertEqual(len(self.mod.EMPTY_TABLES), 21)

    def test_all_strings(self):
        for t in self.mod.EMPTY_TABLES:
            self.assertIsInstance(t, str, f"{t!r} is not a str")

    def test_expected_tables_present(self):
        expected = {
            "corrective_actions", "daily_deliveries", "downtime_events",
            "effectiveness_metrics", "equipment_metrics", "equipment_reliability",
            "failure_events", "financial_impact", "industry_benchmarks",
            "maintenance_targets", "manufacturing_acronyms",
            "non_conformant_materials", "product_defects", "product_lines",
            "production_lines", "production_quality", "production_schedule",
            "products", "quality_costs", "quality_incidents", "users",
        }
        self.assertEqual(set(self.mod.EMPTY_TABLES), expected)


class TestPurgeSkipPaths(unittest.TestCase):
    """Verify purge_arango_stale_vertices skips correctly in offline conditions."""

    def setUp(self):
        self.mod = _load_migration()
        # Ensure env vars that would trigger a real connection are absent.
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        for var in ("ARANGO_HOST", "DATABASE_HOST", "ARANGO_DB", "SKIP_ARANGO"):
            os.environ.pop(var, None)

    def tearDown(self):
        self._env_patch.stop()

    def test_skip_arango_env_var(self):
        """SKIP_ARANGO=1 must exit before any connection attempt."""
        os.environ["SKIP_ARANGO"] = "1"
        os.environ["ARANGO_HOST"] = "http://fake:8529"
        os.environ["ARANGO_DB"] = "manufacturing_graph"
        # Should not raise; no ArangoClient import attempted.
        with patch.dict("sys.modules", {"arango": None}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])

    def test_missing_arango_host(self):
        """No ARANGO_HOST → skip without error."""
        os.environ.pop("ARANGO_HOST", None)
        os.environ.pop("DATABASE_HOST", None)
        os.environ["ARANGO_DB"] = "manufacturing_graph"
        self.mod.purge_arango_stale_vertices(["corrective_actions"])

    def test_missing_arango_db(self):
        """No ARANGO_DB → skip without error."""
        os.environ["ARANGO_HOST"] = "http://fake:8529"
        os.environ.pop("ARANGO_DB", None)
        self.mod.purge_arango_stale_vertices(["corrective_actions"])

    def test_missing_python_arango_package(self):
        """python-arango not installed → skip without error."""
        os.environ["ARANGO_HOST"] = "http://fake:8529"
        os.environ["ARANGO_DB"] = "manufacturing_graph"
        with patch.dict("sys.modules", {"arango": None}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])

    def test_connection_failure_skips(self):
        """ArangoClient raises on connect → skip without propagating."""
        os.environ["ARANGO_HOST"] = "http://fake:8529"
        os.environ["ARANGO_DB"] = "manufacturing_graph"

        fake_arango = types.ModuleType("arango")

        def bad_client(*a, **kw):
            raise ConnectionError("refused")

        fake_arango.ArangoClient = bad_client
        with patch.dict("sys.modules", {"arango": fake_arango}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])


class TestPurgeAqlShape(unittest.TestCase):
    """Verify the AQL issued for each table uses the correct key conventions."""

    def setUp(self):
        self.mod = _load_migration()
        os.environ["ARANGO_HOST"] = "http://fake:8529"
        os.environ["ARANGO_DB"] = "manufacturing_graph"
        os.environ.pop("SKIP_ARANGO", None)

    def tearDown(self):
        for var in ("ARANGO_HOST", "ARANGO_DB", "SKIP_ARANGO"):
            os.environ.pop(var, None)

    def _make_fake_arango(self):
        """Return a fake arango module whose ArangoClient records AQL calls."""
        aql_calls = []

        def fake_execute(query, bind_vars=None):
            aql_calls.append({"query": query, "bind_vars": bind_vars or {}})
            return iter([])

        fake_aql = MagicMock()
        fake_aql.execute = fake_execute

        fake_db = MagicMock()
        fake_db.aql = fake_aql
        fake_db.collections.return_value = []

        fake_client_instance = MagicMock()
        fake_client_instance.db.return_value = fake_db

        fake_arango = types.ModuleType("arango")
        fake_arango.ArangoClient = MagicMock(return_value=fake_client_instance)

        return fake_arango, aql_calls

    def test_table_key_format(self):
        """table vertex key must be table::{UPPER} (double-colon, uppercase)."""
        fake_arango, calls = self._make_fake_arango()
        with patch.dict("sys.modules", {"arango": fake_arango}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])

        table_calls = [c for c in calls if "tkey" in c["bind_vars"]]
        self.assertTrue(table_calls, "No AQL call with 'tkey' bind var found")
        self.assertEqual(
            table_calls[0]["bind_vars"]["tkey"],
            "table::CORRECTIVE_ACTIONS",
        )

    def test_column_prefix_format(self):
        """column prefix must be column::{UPPER}. (double-colon, dot suffix)."""
        fake_arango, calls = self._make_fake_arango()
        with patch.dict("sys.modules", {"arango": fake_arango}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])

        prefix_calls = [c for c in calls if "prefix" in c["bind_vars"]]
        self.assertTrue(prefix_calls, "No AQL call with 'prefix' bind var found")
        self.assertEqual(
            prefix_calls[0]["bind_vars"]["prefix"],
            "column::CORRECTIVE_ACTIONS.",
        )

    def test_table_name_bind_var_is_uppercase(self):
        """tname bind var (column filter) must be the uppercase table name."""
        fake_arango, calls = self._make_fake_arango()
        with patch.dict("sys.modules", {"arango": fake_arango}):
            self.mod.purge_arango_stale_vertices(["corrective_actions"])

        tname_calls = [c for c in calls if "tname" in c["bind_vars"]]
        self.assertTrue(tname_calls, "No AQL call with 'tname' bind var found")
        self.assertEqual(tname_calls[0]["bind_vars"]["tname"], "CORRECTIVE_ACTIONS")

    def test_all_21_tables_produce_aql_calls(self):
        """Each table in EMPTY_TABLES must produce exactly 3 AQL calls."""
        fake_arango, calls = self._make_fake_arango()
        with patch.dict("sys.modules", {"arango": fake_arango}):
            self.mod.purge_arango_stale_vertices(self.mod.EMPTY_TABLES)

        # 3 AQL statements per table: columns, contains, tables
        self.assertEqual(len(calls), 21 * 3)


if __name__ == "__main__":
    unittest.main()
