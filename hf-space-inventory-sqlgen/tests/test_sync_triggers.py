"""
test_sync_triggers.py
=====================
Tests for the SQLite sync-trigger installation (install_sync_triggers.py)
and the queue-detection logic used by sync_watcher.py.

These tests operate on a fresh in-memory (or temp-file) SQLite database
so they never touch the production manufacturing.db.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
PACKAGE_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, PACKAGE_DIR)

import install_sync_triggers as ist


def _make_test_db() -> sqlite3.Connection:
    """Create a minimal in-memory DB with the three watched tables."""
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_intents (
            intent_id   INTEGER PRIMARY KEY,
            intent_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schema_perspectives (
            perspective_id   INTEGER PRIMARY KEY,
            perspective_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schema_concepts (
            concept_id   INTEGER PRIMARY KEY,
            concept_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schema_intent_perspectives (
            intent_id       INTEGER,
            perspective_id  INTEGER,
            intent_factor_weight REAL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS schema_perspective_concepts (
            perspective_id INTEGER,
            concept_id     INTEGER,
            relationship_type TEXT,
            priority_weight   REAL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS schema_intent_concepts (
            intent_id  INTEGER,
            concept_id INTEGER,
            intent_factor_weight REAL DEFAULT 0
        );
    """)
    return conn


class TestInstallSyncTriggers(unittest.TestCase):

    def setUp(self):
        self.conn = _make_test_db()

    def tearDown(self):
        self.conn.close()

    def test_queue_table_created(self):
        ist.install(self.conn)
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_sync_queue'"
        ).fetchone()
        self.assertIsNotNone(row, "graph_sync_queue table should exist after install")

    def test_all_triggers_installed(self):
        ist.install(self.conn)
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_arango_sync_%'"
        ).fetchall()
        found = {r[0] for r in rows}
        expected = {
            ist.trigger_name(t, op)
            for t in ist.WATCHED_TABLES
            for op in ist.OPERATIONS
        }
        self.assertEqual(found, expected)

    def test_insert_trigger_fires(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (1, 1)"
        )
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE source_table='schema_intent_perspectives' AND operation='INSERT'"
        ).fetchone()[0]
        self.assertEqual(count, 1, "INSERT trigger should queue one row")

    def test_update_trigger_fires(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (1, 1)"
        )
        self.conn.execute(
            "UPDATE schema_intent_perspectives SET intent_factor_weight=2 WHERE intent_id=1"
        )
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE operation='UPDATE'"
        ).fetchone()[0]
        self.assertEqual(count, 1, "UPDATE trigger should queue one row")

    def test_delete_trigger_fires(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (1, 1)"
        )
        self.conn.commit()
        self.conn.execute("DELETE FROM graph_sync_queue")
        self.conn.commit()
        self.conn.execute("DELETE FROM schema_intent_perspectives WHERE intent_id=1")
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE operation='DELETE'"
        ).fetchone()[0]
        self.assertEqual(count, 1, "DELETE trigger should queue one row")

    def test_perspective_concepts_trigger(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_perspective_concepts (perspective_id, concept_id) VALUES (1, 1)"
        )
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE source_table='schema_perspective_concepts'"
        ).fetchone()[0]
        self.assertGreater(count, 0, "schema_perspective_concepts trigger should fire")

    def test_intent_concepts_trigger(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_intent_concepts (intent_id, concept_id) VALUES (1, 1)"
        )
        self.conn.commit()
        count = self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE source_table='schema_intent_concepts'"
        ).fetchone()[0]
        self.assertGreater(count, 0, "schema_intent_concepts trigger should fire")

    def test_verify_passes_after_install(self):
        ist.install(self.conn)
        ok = ist.verify(self.conn)
        self.assertTrue(ok, "verify() should return True after a clean install")

    def test_verify_fails_before_install(self):
        ok = ist.verify(self.conn)
        self.assertFalse(ok, "verify() should return False before install")

    def test_remove_clears_triggers(self):
        ist.install(self.conn)
        ist.remove(self.conn)
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_arango_sync_%'"
        ).fetchall()
        self.assertEqual(len(rows), 0, "All triggers should be removed after remove()")

    def test_idempotent_install(self):
        """Installing twice should not raise and should leave exactly the right triggers."""
        ist.install(self.conn)
        ist.install(self.conn)
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_arango_sync_%'"
        ).fetchall()
        self.assertEqual(
            len(rows),
            len(ist.WATCHED_TABLES) * len(ist.OPERATIONS),
            "Idempotent install should not duplicate triggers",
        )

    def test_processed_flag_default(self):
        ist.install(self.conn)
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (1, 1)"
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT processed FROM graph_sync_queue LIMIT 1"
        ).fetchone()
        self.assertEqual(row[0], 0, "New queue rows should default to processed=0")


class TestSyncWatcherQueueLogic(unittest.TestCase):
    """
    Tests the queue-polling helpers in sync_watcher without importing it
    (to avoid needing ArangoDB available).  We replicate the key SQL
    assertions here.
    """

    def setUp(self):
        self.conn = _make_test_db()
        ist.install(self.conn)

    def tearDown(self):
        self.conn.close()

    def _pending(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM graph_sync_queue WHERE processed = 0"
        ).fetchone()[0]

    def _mark_processed(self, outcome: str) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.conn.execute(
            "UPDATE graph_sync_queue SET processed=1, processed_at=?, sync_outcome=? WHERE processed=0",
            (now, outcome),
        )
        self.conn.commit()

    def test_no_pending_when_empty(self):
        self.assertEqual(self._pending(), 0)

    def test_pending_after_insert(self):
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (99, 99)"
        )
        self.conn.commit()
        self.assertEqual(self._pending(), 1)

    def test_mark_processed_clears_pending(self):
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (99, 99)"
        )
        self.conn.commit()
        self._mark_processed("SUCCESS")
        self.assertEqual(self._pending(), 0)

    def test_outcome_recorded(self):
        self.conn.execute(
            "INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (99, 99)"
        )
        self.conn.commit()
        self._mark_processed("SUCCESS")
        row = self.conn.execute(
            "SELECT sync_outcome FROM graph_sync_queue WHERE processed=1"
        ).fetchone()
        self.assertEqual(row[0], "SUCCESS")

    def test_multiple_changes_batch_cleared(self):
        for i in range(5):
            self.conn.execute(
                f"INSERT INTO schema_intent_perspectives (intent_id, perspective_id) VALUES ({i}, {i})"
            )
        self.conn.commit()
        self.assertEqual(self._pending(), 5)
        self._mark_processed("SUCCESS")
        self.assertEqual(self._pending(), 0)


if __name__ == "__main__":
    unittest.main()
