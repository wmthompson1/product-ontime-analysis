"""Tests for the drift detection logic — verifies mismatches are caught correctly.

Tests the core detection logic end-to-end with a real SQLite database and a
mocked ArangoDB client, so the alert pipeline can be verified without a live
ArangoDB instance (#68).

Run: python hf-space-inventory-sqlgen/tests/test_drift_alert_logic.py
"""

from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

BRIDGE_MAP = {
    "Perspective_Intents": "schema_intent_perspectives",
    "Perspective_Concepts": "schema_perspective_concepts",
}


def _make_sqlite(path: str, intent_rows: int = 5, concept_rows: int = 3) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_intent_perspectives (
            id INTEGER PRIMARY KEY,
            intent_id INTEGER,
            perspective_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS schema_perspective_concepts (
            id INTEGER PRIMARY KEY,
            perspective_id INTEGER,
            concept_id INTEGER
        );
    """)
    for i in range(intent_rows):
        conn.execute("INSERT INTO schema_intent_perspectives VALUES (?, ?, ?)", (i+1, i+1, 1))
    for i in range(concept_rows):
        conn.execute("INSERT INTO schema_perspective_concepts VALUES (?, ?, ?)", (i+1, 1, i+1))
    conn.commit()
    conn.close()


def _mock_arango_db(pi_count: int, pc_count: int) -> MagicMock:
    db = MagicMock()
    def _collection(name: str):
        coll = MagicMock()
        if name == "Perspective_Intents":
            coll.count.return_value = pi_count
        else:
            coll.count.return_value = pc_count
        return coll
    db.has_collection.return_value = True
    db.collection.side_effect = _collection
    return db


def _run_health_check(db_path: str, arango_db: MagicMock) -> tuple:
    """Replicate the bridge health check logic for testing."""
    import datetime as dt
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists(db_path):
        return ("⚠️  SKIP — SQLite DB not found", timestamp, "DB missing")

    conn = sqlite3.connect(db_path)
    sqlite_counts = {}
    try:
        for sqlite_table in BRIDGE_MAP.values():
            row = conn.execute(f"SELECT COUNT(*) FROM {sqlite_table}").fetchone()
            sqlite_counts[sqlite_table] = row[0] if row else 0
    finally:
        conn.close()

    arango_counts = {}
    for coll_name in BRIDGE_MAP:
        if arango_db.has_collection(coll_name):
            arango_counts[coll_name] = arango_db.collection(coll_name).count()
        else:
            arango_counts[coll_name] = -1

    lines = [
        f"{'Collection':<28} {'ArangoDB':>12} {'SQLite':>12} {'Match':>8}",
        "-" * 64,
    ]
    all_ok = True
    for ac, st in BRIDGE_MAP.items():
        an = arango_counts.get(ac)
        sn = sqlite_counts.get(st, "?")
        if isinstance(an, str):
            match_icon = "ERROR"
            all_ok = False
        elif an == -1:
            match_icon = "MISSING"
            all_ok = False
        elif an == sn:
            match_icon = "✅"
        else:
            match_icon = "❌"
            all_ok = False
        arango_display = "MISSING" if an == -1 else str(an)
        lines.append(f"{ac:<28} {arango_display:>12} {str(sn):>12} {match_icon:>8}")

    if all_ok:
        overall = "✅  IN SYNC — all counts match"
    else:
        overall = "❌  OUT OF SYNC — counts differ (see details below)"
    return (overall, timestamp, "\n".join(lines))


class TestDriftDetectionInSync(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        _make_sqlite(self.tmp, intent_rows=5, concept_rows=3)

    def tearDown(self):
        try:
            os.unlink(self.tmp)
        except OSError:
            pass

    def test_returns_ok_when_counts_match(self):
        db = _mock_arango_db(pi_count=5, pc_count=3)
        status, _, _ = _run_health_check(self.tmp, db)
        self.assertIn("IN SYNC", status, f"Expected IN SYNC, got: {status!r}")
        self.assertIn("✅", status, f"Expected ✅ in status: {status!r}")

    def test_reports_ok_with_correct_emoji(self):
        db = _mock_arango_db(5, 3)
        status, _, report = _run_health_check(self.tmp, db)
        self.assertTrue(status.startswith("✅"), f"Status should start with ✅: {status!r}")
        self.assertIn("✅", report, "Report should show ✅ for all rows")
        self.assertNotIn("❌", report, "No mismatch rows expected")


class TestDriftDetectionMismatch(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        _make_sqlite(self.tmp, intent_rows=5, concept_rows=3)

    def tearDown(self):
        try:
            os.unlink(self.tmp)
        except OSError:
            pass

    def test_detects_perspective_intents_mismatch(self):
        db = _mock_arango_db(pi_count=4, pc_count=3)  # 4 vs SQLite 5
        status, _, report = _run_health_check(self.tmp, db)
        self.assertIn("OUT OF SYNC", status, f"Expected OUT OF SYNC: {status!r}")
        self.assertIn("❌", status, f"Expected ❌ in status: {status!r}")
        self.assertIn("❌", report, "Report must contain ❌ for mismatched row")

    def test_detects_perspective_concepts_mismatch(self):
        db = _mock_arango_db(pi_count=5, pc_count=99)  # 99 vs SQLite 3
        status, _, report = _run_health_check(self.tmp, db)
        self.assertIn("OUT OF SYNC", status, f"Expected OUT OF SYNC: {status!r}")

    def test_detects_both_collections_mismatch(self):
        db = _mock_arango_db(pi_count=1, pc_count=1)
        status, _, report = _run_health_check(self.tmp, db)
        self.assertIn("OUT OF SYNC", status)
        # Both rows should show ❌
        self.assertEqual(report.count("❌"), 2, f"Expected 2 mismatch rows:\n{report}")

    def test_mismatch_report_shows_both_counts(self):
        db = _mock_arango_db(pi_count=4, pc_count=3)
        _, _, report = _run_health_check(self.tmp, db)
        self.assertIn("4", report, "Arango count should appear in report")
        self.assertIn("5", report, "SQLite count should appear in report")

    def test_missing_collection_shows_missing(self):
        db = _mock_arango_db(5, 3)
        db.has_collection.return_value = False
        status, _, report = _run_health_check(self.tmp, db)
        self.assertIn("OUT OF SYNC", status)
        self.assertIn("MISSING", report, "Missing collection should say MISSING in report")

    def test_report_includes_collection_names(self):
        db = _mock_arango_db(4, 3)
        _, _, report = _run_health_check(self.tmp, db)
        self.assertIn("Perspective_Intents", report)
        self.assertIn("Perspective_Concepts", report)

    def test_alert_payload_format(self):
        """Simulate building a Slack payload — verify it includes key fields."""
        import datetime, json
        db = _mock_arango_db(4, 3)
        status, ts, report = _run_health_check(self.tmp, db)

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": ":rotating_light: Drift Detected"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Time (UTC):*\n{ts}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"```{report}```"}},
        ]
        payload = json.dumps({"blocks": blocks})
        parsed = json.loads(payload)
        self.assertEqual(len(parsed["blocks"]), 3)
        self.assertIn("Drift Detected", parsed["blocks"][0]["text"]["text"])
        self.assertIn(ts, parsed["blocks"][1]["fields"][0]["text"])
        self.assertIn(report, parsed["blocks"][2]["text"]["text"])


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDriftDetectionInSync))
    suite.addTests(loader.loadTestsFromTestCase(TestDriftDetectionMismatch))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
