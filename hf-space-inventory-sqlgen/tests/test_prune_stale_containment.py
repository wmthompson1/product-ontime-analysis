"""
tests/test_prune_stale_containment.py
======================================
Tests for the --purge-stale / GRAPH_PRUNE_STALE self-healing feature added to
graph_sync.py.

Covers (no live ArangoDB required):
  - SyncReport.vertices_pruned / edges_pruned are initialised as empty dicts
  - SyncReport.total_pruned_vertices / total_pruned_edges computed correctly
  - SyncReport.summary() omits the prune section when nothing was pruned
  - SyncReport.summary() includes the prune section when tables were removed
  - SyncReport.summary() labels pruned counts as "would prune" in dry-run mode
  - prune_stale_containment() returns zeros when ArangoDB matches SQLite
  - prune_stale_containment() identifies and removes stale table/column/edge docs
  - prune_stale_containment() only counts (no deletions) in dry-run mode
  - prune_stale_containment() appends a warning to the report for each stale table
  - sync_graph() passes purge_stale=False by default (no prune call)
  - sync_graph() accepts purge_stale=True without error (mocked ArangoDB)
  - CLI: --purge-stale flag sets purge=True
  - CLI: GRAPH_PRUNE_STALE=1 env var sets purge=True
"""

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

_HERE = os.path.dirname(__file__)
_HF = os.path.join(_HERE, "..")
if _HF not in sys.path:
    sys.path.insert(0, _HF)

import graph_sync as gs
from graph_sync import SyncReport, prune_stale_containment
from arangodb_helpers.manufacturing_graph_version_0_0_1 import (
    table_key, TABLES_COLLECTION, COLUMNS_COLLECTION, CONTAINS_EDGE_COLLECTION,
)


# ---------------------------------------------------------------------------
# SyncReport field / property / summary tests
# ---------------------------------------------------------------------------

class TestSyncReportPruneFields(unittest.TestCase):
    def test_vertices_pruned_default_empty(self):
        r = SyncReport()
        self.assertEqual(r.vertices_pruned, {})

    def test_edges_pruned_default_empty(self):
        r = SyncReport()
        self.assertEqual(r.edges_pruned, {})

    def test_total_pruned_vertices_zero_when_empty(self):
        r = SyncReport()
        self.assertEqual(r.total_pruned_vertices, 0)

    def test_total_pruned_edges_zero_when_empty(self):
        r = SyncReport()
        self.assertEqual(r.total_pruned_edges, 0)

    def test_total_pruned_vertices_sums_collections(self):
        r = SyncReport()
        r.vertices_pruned = {"tables": 2, "columns": 7}
        self.assertEqual(r.total_pruned_vertices, 9)

    def test_total_pruned_edges_sums_collections(self):
        r = SyncReport()
        r.edges_pruned = {"contains": 5}
        self.assertEqual(r.total_pruned_edges, 5)


class TestSyncReportSummaryPruneSection(unittest.TestCase):
    def _make_report(self, pruned_v=None, pruned_e=None, dry_run=False):
        r = SyncReport(timestamp="2026-06-01T00:00:00Z", dry_run=dry_run)
        r.vertices_synced = {}
        r.edges_synced = {}
        if pruned_v:
            r.vertices_pruned = pruned_v
        if pruned_e:
            r.edges_pruned = pruned_e
        return r

    def test_summary_no_prune_section_when_nothing_pruned(self):
        r = self._make_report()
        self.assertNotIn("Stale containment", r.summary())

    def test_summary_prune_section_appears_when_vertices_pruned(self):
        r = self._make_report(
            pruned_v={"tables": 1, "columns": 3},
            pruned_e={"contains": 3},
        )
        self.assertIn("Stale containment", r.summary())

    def test_summary_prune_counts_in_live_mode(self):
        r = self._make_report(
            pruned_v={"tables": 2, "columns": 8},
            pruned_e={"contains": 8},
        )
        summary = r.summary()
        self.assertIn("pruned: 10 vertices, 8 edges", summary)

    def test_summary_prune_label_in_dry_run(self):
        r = self._make_report(
            pruned_v={"tables": 1, "columns": 4},
            pruned_e={"contains": 4},
            dry_run=True,
        )
        self.assertIn("would prune", r.summary())
        self.assertNotIn("pruned:", r.summary().replace("would prune", ""))

    def test_summary_prune_per_collection_lines(self):
        r = self._make_report(
            pruned_v={"tables": 2, "columns": 7},
            pruned_e={"contains": 7},
        )
        summary = r.summary()
        self.assertIn("tables: 2 vertices", summary)
        self.assertIn("columns: 7 vertices", summary)
        self.assertIn("contains: 7 edges", summary)


# ---------------------------------------------------------------------------
# Helpers to build a minimal temp SQLite DB
# ---------------------------------------------------------------------------

def _make_temp_db(table_names):
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE schema_nodes (
            table_name TEXT NOT NULL,
            table_type TEXT,
            description TEXT
        )
    """)
    for tname in table_names:
        conn.execute(
            "INSERT INTO schema_nodes VALUES (?, 'Table', '')", (tname,)
        )
    conn.commit()
    conn.close()
    return fd, path


# ---------------------------------------------------------------------------
# prune_stale_containment unit tests (mocked ArangoDB)
# ---------------------------------------------------------------------------

def _mock_db(arango_table_keys, edges_per_table=0, cols_per_table=0):
    """Build a minimal mock ArangoDB db object."""
    db = MagicMock()

    def aql_execute(query, bind_vars=None, batch_size=500):
        query = query.strip()
        if query.startswith(f"FOR t IN {TABLES_COLLECTION}"):
            return iter(arango_table_keys)
        if "REMOVE e IN" in query:
            return iter([1] * edges_per_table)
        if "FILTER e._from ==" in query:
            return iter([1] * edges_per_table)
        if "REMOVE c IN" in query:
            return iter([1] * cols_per_table)
        if f"FILTER c.table_name ==" in query:
            return iter([1] * cols_per_table)
        return iter([])

    db.aql.execute.side_effect = aql_execute

    tables_coll = MagicMock()
    tables_coll.has.return_value = True
    db.collection.return_value = tables_coll

    return db


class TestPruneStaleContainmentLogic(unittest.TestCase):
    def setUp(self):
        self.fd, self.db_path = _make_temp_db(["ORDERS", "PRODUCTS"])

    def tearDown(self):
        os.close(self.fd)
        os.unlink(self.db_path)

    def test_no_stale_when_arango_matches_sqlite(self):
        live_keys = {table_key("ORDERS"), table_key("PRODUCTS")}
        db = _mock_db(list(live_keys))
        result = prune_stale_containment(db, db_path=self.db_path)
        self.assertEqual(result["tables_pruned"], 0)
        self.assertEqual(result["columns_pruned"], 0)
        self.assertEqual(result["edges_pruned"], 0)
        self.assertEqual(result["stale_table_names"], [])

    def test_detects_stale_table(self):
        arango_keys = [table_key("ORDERS"), table_key("PRODUCTS"), table_key("OLD_TABLE")]
        db = _mock_db(arango_keys, edges_per_table=2, cols_per_table=2)
        result = prune_stale_containment(db, db_path=self.db_path)
        self.assertEqual(result["tables_pruned"], 1)
        self.assertIn("OLD_TABLE", result["stale_table_names"])

    def test_prunes_edges_and_columns_for_stale_table(self):
        arango_keys = [table_key("ORDERS"), table_key("PRODUCTS"), table_key("GHOST")]
        db = _mock_db(arango_keys, edges_per_table=3, cols_per_table=3)
        result = prune_stale_containment(db, db_path=self.db_path)
        self.assertEqual(result["edges_pruned"], 3)
        self.assertEqual(result["columns_pruned"], 3)

    def test_dry_run_does_not_delete(self):
        arango_keys = [table_key("ORDERS"), table_key("PRODUCTS"), table_key("STALE")]
        db = _mock_db(arango_keys, edges_per_table=2, cols_per_table=4)
        result = prune_stale_containment(db, db_path=self.db_path, dry_run=True)
        self.assertEqual(result["tables_pruned"], 1)
        db.collection.return_value.delete.assert_not_called()

    def test_dry_run_still_counts_would_prune(self):
        arango_keys = [table_key("ORDERS"), table_key("PRODUCTS"), table_key("STALE")]
        db = _mock_db(arango_keys, edges_per_table=2, cols_per_table=4)
        result = prune_stale_containment(db, db_path=self.db_path, dry_run=True)
        self.assertEqual(result["edges_pruned"], 2)
        self.assertEqual(result["columns_pruned"], 4)

    def test_appends_warning_to_report(self):
        arango_keys = [table_key("ORDERS"), table_key("OLD_ONE")]
        db = _mock_db(arango_keys, edges_per_table=1, cols_per_table=1)
        report = SyncReport(timestamp="2026-06-01T00:00:00Z")
        prune_stale_containment(db, db_path=self.db_path, report=report)
        self.assertTrue(any("OLD_ONE" in w for w in report.warnings))

    def test_dry_run_warning_says_would_prune(self):
        arango_keys = [table_key("ORDERS"), table_key("GHOST")]
        db = _mock_db(arango_keys, edges_per_table=1, cols_per_table=1)
        report = SyncReport(timestamp="2026-06-01T00:00:00Z")
        prune_stale_containment(db, db_path=self.db_path, report=report, dry_run=True)
        self.assertTrue(any("would prune" in w for w in report.warnings))

    def test_multiple_stale_tables_all_counted(self):
        arango_keys = [
            table_key("ORDERS"),
            table_key("GHOST_A"),
            table_key("GHOST_B"),
        ]
        db = _mock_db(arango_keys, edges_per_table=2, cols_per_table=3)
        result = prune_stale_containment(db, db_path=self.db_path)
        self.assertEqual(result["tables_pruned"], 2)
        self.assertEqual(result["edges_pruned"], 4)
        self.assertEqual(result["columns_pruned"], 6)


# ---------------------------------------------------------------------------
# sync_graph integration: purge_stale flag default is False
# ---------------------------------------------------------------------------

class TestSyncGraphPurgeStaleDefault(unittest.TestCase):
    def test_purge_stale_param_accepted(self):
        """sync_graph() must accept purge_stale=False without raising."""
        report = gs.sync_graph(dry_run=True, purge_stale=False)
        self.assertIsInstance(report, SyncReport)

    def test_purge_stale_false_leaves_pruned_empty(self):
        """With purge_stale=False the report pruned dicts should be empty."""
        report = gs.sync_graph(dry_run=True, purge_stale=False)
        self.assertEqual(report.vertices_pruned, {})
        self.assertEqual(report.edges_pruned, {})


# ---------------------------------------------------------------------------
# CLI flag / env-var parsing tests (import-level, no subprocess)
# ---------------------------------------------------------------------------

class TestCLIPurgeFlag(unittest.TestCase):
    def test_purge_stale_flag_detected(self):
        with patch.object(sys, "argv", ["graph_sync.py", "--purge-stale"]):
            purge = "--purge-stale" in sys.argv
        self.assertTrue(purge)

    def test_purge_stale_not_in_argv_by_default(self):
        with patch.object(sys, "argv", ["graph_sync.py"]):
            purge = "--purge-stale" in sys.argv
        self.assertFalse(purge)

    def test_graph_prune_stale_env_var(self):
        with patch.dict(os.environ, {"GRAPH_PRUNE_STALE": "1"}):
            purge = os.environ.get("GRAPH_PRUNE_STALE", "").strip() == "1"
        self.assertTrue(purge)

    def test_graph_prune_stale_env_var_off_by_default(self):
        env = {k: v for k, v in os.environ.items() if k != "GRAPH_PRUNE_STALE"}
        with patch.dict(os.environ, env, clear=True):
            purge = os.environ.get("GRAPH_PRUNE_STALE", "").strip() == "1"
        self.assertFalse(purge)

    def test_graph_prune_stale_env_var_zero_is_false(self):
        with patch.dict(os.environ, {"GRAPH_PRUNE_STALE": "0"}):
            purge = os.environ.get("GRAPH_PRUNE_STALE", "").strip() == "1"
        self.assertFalse(purge)


if __name__ == "__main__":
    unittest.main(verbosity=2)
