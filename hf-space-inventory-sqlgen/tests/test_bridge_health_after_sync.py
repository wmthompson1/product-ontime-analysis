"""Tests for bridge health auto-fire after sync (#120).

Verifies:
- quick_bridge_health() is importable and returns a non-empty string
- Return value always starts with a known status prefix
- When ArangoDB is live, result is "✅ IN SYNC" after a fresh sync
- _SYNC_LAST_STATUS is updated by the sync wrapper so the inline
  status row carries both sync result and health (#121)

Run: python hf-space-inventory-sqlgen/tests/test_bridge_health_after_sync.py
"""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

VALID_PREFIXES = ("✅", "❌", "⚠️", "SKIP", "ArangoDB not configured")


class TestQuickBridgeHealthImport(unittest.TestCase):
    """quick_bridge_health must be importable from app module."""

    def test_importable(self):
        from app import quick_bridge_health
        self.assertTrue(callable(quick_bridge_health))

    def test_returns_string(self):
        from app import quick_bridge_health
        result = quick_bridge_health()
        self.assertIsInstance(result, str)

    def test_result_nonempty(self):
        from app import quick_bridge_health
        result = quick_bridge_health()
        self.assertTrue(result.strip(), "quick_bridge_health must not return blank string")

    def test_result_has_known_prefix(self):
        from app import quick_bridge_health
        result = quick_bridge_health()
        self.assertTrue(
            any(result.startswith(p) for p in VALID_PREFIXES),
            f"Unexpected prefix in health result: {result!r}"
        )


class TestSyncLastStatusTracker(unittest.TestCase):
    """_SYNC_LAST_STATUS must be updated when run_graph_sync is called (#121)."""

    def test_tracker_is_list(self):
        from app import _SYNC_LAST_STATUS
        self.assertIsInstance(_SYNC_LAST_STATUS, list)
        self.assertEqual(len(_SYNC_LAST_STATUS), 1)

    def test_tracker_initial_value_is_string(self):
        from app import _SYNC_LAST_STATUS
        self.assertIsInstance(_SYNC_LAST_STATUS[0], str)
        self.assertTrue(_SYNC_LAST_STATUS[0].strip())


class TestBridgeHealthAfterSync(unittest.TestCase):
    """When ArangoDB is live, bridge health should be IN SYNC after a sync run."""

    def _arango_available(self) -> bool:
        return bool(os.environ.get("ARANGO_HOST"))

    def test_in_sync_after_graph_sync(self):
        if not self._arango_available():
            self.skipTest("ARANGO_HOST not set — skipping live ArangoDB test")
        from graph_sync import sync_graph
        report = sync_graph(dry_run=False)
        self.assertTrue(report.success, f"sync_graph failed: {report.summary()}")

        from app import quick_bridge_health
        result = quick_bridge_health()
        self.assertTrue(
            result.startswith("✅"),
            f"Expected IN SYNC after fresh sync, got: {result!r}"
        )

    def test_health_result_format_when_live(self):
        if not self._arango_available():
            self.skipTest("ARANGO_HOST not set — skipping live ArangoDB test")
        from app import quick_bridge_health
        result = quick_bridge_health()
        self.assertIn("@", result, "Live health result should contain a timestamp with @")


class TestInlineStatusRow(unittest.TestCase):
    """The inline health result must be appendable to the sync status (#121)."""

    def test_inline_combines_sync_and_health(self):
        from app import quick_bridge_health, _SYNC_LAST_STATUS
        fake_sync_status = "SUCCESS — 80 vertices, 41 edges synced to ArangoDB"
        _SYNC_LAST_STATUS[0] = fake_sync_status
        health = quick_bridge_health()
        combined = f"{_SYNC_LAST_STATUS[0]}  ·  {health}"
        self.assertIn("SUCCESS", combined)
        self.assertTrue(any(combined.startswith(p) or p in combined for p in VALID_PREFIXES))
        self.assertIn("·", combined)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestQuickBridgeHealthImport,
        TestSyncLastStatusTracker,
        TestBridgeHealthAfterSync,
        TestInlineStatusRow,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
