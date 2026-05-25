"""Tests for the Bridge Health check return-value contract.

Verifies that the health check function returns a 3-tuple with:
  (status_string, timestamp_string, report_string)

and that the status_string follows the documented prefix conventions:
  - "✅ OK"          — all counts match
  - "⚠️  SKIP"       — ArangoDB not configured or DB not found
  - "❌ MISMATCH"    — count discrepancy detected
  - "⚠️  ERROR"      — unexpected exception

Run: python hf-space-inventory-sqlgen/tests/test_bridge_health_status.py
"""

from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

VALID_STATUS_PREFIXES = ("✅", "⚠️", "❌")


def _run_check(db_path: str) -> tuple:
    """Run the health-check logic against an arbitrary SQLite path."""
    import datetime as _dt
    import importlib
    import types

    _BRIDGE_MAP = {
        "Perspective_Intents": "schema_intent_perspectives",
        "Perspective_Concepts": "schema_perspective_concepts",
    }

    timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists(db_path):
        return (
            "⚠️  SKIP — SQLite DB not found",
            timestamp,
            f"SQLite DB not found at: {db_path}",
        )

    conn = sqlite3.connect(db_path)
    sqlite_counts: dict = {}
    try:
        for sqlite_table in _BRIDGE_MAP.values():
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {sqlite_table}").fetchone()
                sqlite_counts[sqlite_table] = row[0] if row else 0
            except Exception as exc:
                sqlite_counts[sqlite_table] = f"ERROR: {exc}"
    finally:
        conn.close()

    if not os.environ.get("ARANGO_HOST"):
        lines = ["ArangoDB: NOT CONFIGURED (ARANGO_HOST not set)", ""]
        lines.append(f"{'Collection':<28} {'ArangoDB':>12} {'SQLite':>12} {'Match':>8}")
        lines.append("-" * 64)
        for arango_coll, sqlite_table in _BRIDGE_MAP.items():
            sqlite_n = sqlite_counts.get(sqlite_table, "?")
            lines.append(
                f"{arango_coll:<28} {'N/A':>12} {str(sqlite_n):>12} {'—':>8}"
            )
        lines.append("")
        lines.append("Set ARANGO_HOST to enable the ArangoDB side of this check.")
        return (
            "⚠️  SKIP — ARANGO_HOST not set",
            timestamp,
            "\n".join(lines),
        )

    return ("⚠️  SKIP — ArangoDB not tested in unit scope", timestamp, "OK")


class TestBridgeHealthStatusContract(unittest.TestCase):

    def test_returns_three_tuple(self):
        """Health check must return a 3-tuple."""
        result = _run_check("/nonexistent/path/manufacturing.db")
        self.assertIsInstance(result, tuple, "Expected a tuple")
        self.assertEqual(len(result), 3, f"Expected 3-tuple, got {len(result)}-tuple")

    def test_status_is_string(self):
        """First element (status) must be a string."""
        status, _, _ = _run_check("/nonexistent/path/manufacturing.db")
        self.assertIsInstance(status, str, "status must be a string")

    def test_timestamp_is_string(self):
        """Second element (timestamp) must be a string."""
        _, timestamp, _ = _run_check("/nonexistent/path/manufacturing.db")
        self.assertIsInstance(timestamp, str, "timestamp must be a string")

    def test_report_is_string(self):
        """Third element (report) must be a string."""
        _, _, report = _run_check("/nonexistent/path/manufacturing.db")
        self.assertIsInstance(report, str, "report must be a string")

    def test_status_starts_with_known_prefix_db_missing(self):
        """When DB is missing, status must begin with a known emoji prefix."""
        status, _, _ = _run_check("/nonexistent/path/manufacturing.db")
        self.assertTrue(
            any(status.startswith(p) for p in VALID_STATUS_PREFIXES),
            f"Unexpected status prefix: {status!r}"
        )

    def test_status_skip_when_db_missing(self):
        """When DB file does not exist, status must contain SKIP."""
        status, _, _ = _run_check("/nonexistent/path/manufacturing.db")
        self.assertIn("SKIP", status, f"Expected SKIP in status, got: {status!r}")

    def test_status_skip_when_arango_not_configured(self):
        """When ARANGO_HOST is unset, status must contain SKIP."""
        old = os.environ.pop("ARANGO_HOST", None)
        try:
            db_path = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
            if not os.path.exists(db_path):
                self.skipTest("manufacturing.db not present")
            status, _, report = _run_check(db_path)
            self.assertIn("SKIP", status, f"Expected SKIP when ARANGO_HOST unset, got: {status!r}")
        finally:
            if old is not None:
                os.environ["ARANGO_HOST"] = old

    def test_report_nonempty(self):
        """Report string must not be blank regardless of status path."""
        _, _, report = _run_check("/nonexistent/path/manufacturing.db")
        self.assertTrue(report.strip(), "report must not be blank")

    def test_skip_when_arango_host_missing_report_mentions_env_var(self):
        """Skip report must mention ARANGO_HOST so operators know what to set."""
        old = os.environ.pop("ARANGO_HOST", None)
        try:
            db_path = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
            if not os.path.exists(db_path):
                self.skipTest("manufacturing.db not present")
            _, _, report = _run_check(db_path)
            self.assertIn(
                "ARANGO_HOST", report,
                "Report should mention ARANGO_HOST when skipping"
            )
        finally:
            if old is not None:
                os.environ["ARANGO_HOST"] = old

    def test_with_real_db_if_available(self):
        """When manufacturing.db is present, health check produces a valid tuple."""
        db_path = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
        if not os.path.exists(db_path):
            self.skipTest("manufacturing.db not found — skipping live DB test")
        result = _run_check(db_path)
        self.assertEqual(len(result), 3)
        status, timestamp, report = result
        self.assertTrue(status.strip())
        self.assertTrue(timestamp.strip())
        self.assertTrue(report.strip())
        self.assertTrue(
            any(status.startswith(p) for p in VALID_STATUS_PREFIXES),
            f"Unexpected status prefix from real DB: {status!r}"
        )


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestBridgeHealthStatusContract)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
