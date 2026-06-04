"""Tests for bridge_health.get_sweep1_coverage_gaps.

Covers:
  - skip when ARANGO_HOST not set
  - skip/error when ArangoDB connection fails
  - skip when no ELEVATES edges are found
  - all-passing result (status="ok")
  - gaps found result (status="gaps")
  - dangling vertex skip_count (edges with None/empty intent or concept label)

Uses the injection-seam pattern (_arango_env_getter, _arango_factory) so
no live ArangoDB is required.  get_ground_truth_bindings is patched via
unittest.mock so no reviewer_manifest.json file is needed.

Run: python hf-space-inventory-sqlgen/tests/test_sweep1_coverage_gaps.py
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

from bridge_health import get_sweep1_coverage_gaps  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_arango(key: str) -> str | None:
    return None


def _has_arango(key: str) -> str | None:
    return "http://localhost:8529" if key == "ARANGO_HOST" else None


def _make_db(edges: list[dict]) -> MagicMock:
    """Return a minimal mock ArangoDB db object whose AQL returns *edges*."""
    cursor = MagicMock()
    cursor.__iter__ = MagicMock(return_value=iter(edges))

    aql_mock = MagicMock()
    aql_mock.execute.return_value = cursor

    db = MagicMock()
    db.aql = aql_mock
    return db


def _make_factory(edges: list[dict]):
    """Wrap _make_db in a zero-arg callable."""
    db = _make_db(edges)
    return lambda: db


def _failing_factory(msg: str = "refused"):
    def _factory():
        raise ConnectionError(msg)
    return _factory


_FAKE_MANIFEST = "/fake/reviewer_manifest.json"


def _patch_bindings(bindings: list[dict]):
    """Return a context manager that patches get_ground_truth_bindings.

    The function is imported inside get_sweep1_coverage_gaps via
    ``from metadata_query_templates import get_ground_truth_bindings``,
    so we patch the name on the source module, not on bridge_health.
    """
    return patch(
        "metadata_query_templates.get_ground_truth_bindings",
        return_value=bindings,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSweep1CoverageGapsNoArango(unittest.TestCase):
    """Cases that skip before any ArangoDB call."""

    def test_skip_when_arango_host_not_set(self):
        result = get_sweep1_coverage_gaps(
            _FAKE_MANIFEST,
            _arango_env_getter=_no_arango,
        )
        self.assertEqual(result["status"], "skip")
        self.assertEqual(result["total_edges"], 0)
        self.assertEqual(result["pass_count"], 0)
        self.assertEqual(result["gap_concepts"], [])
        self.assertEqual(result["skip_count"], 0)
        self.assertIn("ARANGO_HOST", result["message"])

    def test_skip_message_nonempty(self):
        result = get_sweep1_coverage_gaps(
            _FAKE_MANIFEST,
            _arango_env_getter=_no_arango,
        )
        self.assertTrue(result["message"].strip())

    def test_result_has_all_required_keys(self):
        result = get_sweep1_coverage_gaps(
            _FAKE_MANIFEST,
            _arango_env_getter=_no_arango,
        )
        for key in ("status", "total_edges", "pass_count", "gap_concepts",
                    "skip_count", "message"):
            self.assertIn(key, result, f"Missing key: {key!r}")


class TestSweep1CoverageGapsConnectionError(unittest.TestCase):
    """Cases where ArangoDB factory raises."""

    def test_error_on_connection_failure(self):
        result = get_sweep1_coverage_gaps(
            _FAKE_MANIFEST,
            _arango_env_getter=_has_arango,
            _arango_factory=_failing_factory("connection refused"),
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("connection refused", result["message"])

    def test_error_result_counts_are_zero(self):
        result = get_sweep1_coverage_gaps(
            _FAKE_MANIFEST,
            _arango_env_getter=_has_arango,
            _arango_factory=_failing_factory(),
        )
        self.assertEqual(result["total_edges"], 0)
        self.assertEqual(result["pass_count"], 0)
        self.assertEqual(result["gap_concepts"], [])
        self.assertEqual(result["skip_count"], 0)


class TestSweep1CoverageGapsNoEdges(unittest.TestCase):
    """Skip when ELEVATES collection is empty."""

    def test_skip_when_no_edges(self):
        with _patch_bindings([]):
            result = get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory([]),
            )
        self.assertEqual(result["status"], "skip")
        self.assertEqual(result["total_edges"], 0)

    def test_skip_message_mentions_empty_graph(self):
        with _patch_bindings([]):
            result = get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory([]),
            )
        msg_lower = result["message"].lower()
        self.assertTrue(
            "empty" in msg_lower or "no elevates" in msg_lower or "unsynced" in msg_lower,
            f"Expected empty/unsynced mention, got: {result['message']!r}",
        )


class TestSweep1CoverageGapsAllPassing(unittest.TestCase):
    """All edges have an approved binding — status should be 'ok'."""

    _EDGES = [
        {
            "intent_key": "k1",
            "intent_name": "Check Inventory",
            "concept_key": "ck1",
            "concept_name": "INVENTORY_LEVEL",
            "weight": 1,
        },
        {
            "intent_key": "k2",
            "intent_name": "Low Stock Alert",
            "concept_key": "ck2",
            "concept_name": "REORDER_POINT",
            "weight": 1,
        },
    ]

    _BINDINGS = [
        {"concept_anchor": "INVENTORY_LEVEL", "file_path": "sql/inv.sql", "binding_key": "b1"},
        {"concept_anchor": "REORDER_POINT",   "file_path": "sql/reorder.sql", "binding_key": "b2"},
    ]

    def _run(self):
        with _patch_bindings(self._BINDINGS):
            return get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory(self._EDGES),
            )

    def test_status_is_ok(self):
        self.assertEqual(self._run()["status"], "ok")

    def test_pass_count_equals_edge_count(self):
        result = self._run()
        self.assertEqual(result["pass_count"], len(self._EDGES))

    def test_no_gap_concepts(self):
        self.assertEqual(self._run()["gap_concepts"], [])

    def test_total_edges(self):
        self.assertEqual(self._run()["total_edges"], len(self._EDGES))

    def test_skip_count_zero(self):
        self.assertEqual(self._run()["skip_count"], 0)

    def test_message_nonempty(self):
        self.assertTrue(self._run()["message"].strip())


class TestSweep1CoverageGapsFound(unittest.TestCase):
    """Some edges lack approved bindings — status should be 'gaps'."""

    _EDGES = [
        {
            "intent_key": "k1",
            "intent_name": "Check Inventory",
            "concept_key": "ck1",
            "concept_name": "INVENTORY_LEVEL",
            "weight": 1,
        },
        {
            "intent_key": "k2",
            "intent_name": "Supplier Lead Time",
            "concept_key": "ck2",
            "concept_name": "LEAD_TIME_DAYS",
            "weight": 1,
        },
    ]

    _BINDINGS = [
        {"concept_anchor": "INVENTORY_LEVEL", "file_path": "sql/inv.sql", "binding_key": "b1"},
    ]

    def _run(self):
        with _patch_bindings(self._BINDINGS):
            return get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory(self._EDGES),
            )

    def test_status_is_gaps(self):
        self.assertEqual(self._run()["status"], "gaps")

    def test_gap_concepts_not_empty(self):
        self.assertGreater(len(self._run()["gap_concepts"]), 0)

    def test_gap_concept_has_required_fields(self):
        gap = self._run()["gap_concepts"][0]
        for field in ("intent_name", "concept_name", "concept_anchor"):
            self.assertIn(field, gap, f"gap_concepts entry missing field: {field!r}")

    def test_pass_count_is_correct(self):
        self.assertEqual(self._run()["pass_count"], 1)

    def test_gap_count_is_correct(self):
        self.assertEqual(len(self._run()["gap_concepts"]), 1)

    def test_gap_anchor_is_uppercased(self):
        gaps = self._run()["gap_concepts"]
        for g in gaps:
            self.assertEqual(g["concept_anchor"], g["concept_anchor"].upper())

    def test_message_mentions_gap_count(self):
        result = self._run()
        self.assertIn("1", result["message"])

    def test_total_edges_matches(self):
        self.assertEqual(self._run()["total_edges"], len(self._EDGES))

    def test_empty_manifest_gives_all_gaps(self):
        with _patch_bindings([]):
            result = get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory(self._EDGES),
            )
        self.assertEqual(result["status"], "gaps")
        self.assertEqual(len(result["gap_concepts"]), len(self._EDGES))
        self.assertEqual(result["pass_count"], 0)


class TestSweep1CoverageGapsDanglingVertices(unittest.TestCase):
    """Edges with missing intent or concept labels are counted as skip_count."""

    _EDGES_WITH_DANGLING = [
        {
            "intent_key": "k1",
            "intent_name": "Check Inventory",
            "concept_key": "ck1",
            "concept_name": "INVENTORY_LEVEL",
            "weight": 1,
        },
        {
            "intent_key": None,
            "intent_name": None,
            "concept_key": "ck_dangling",
            "concept_name": "ORPHAN_CONCEPT",
            "weight": 1,
        },
        {
            "intent_key": "k3",
            "intent_name": "Reorder Check",
            "concept_key": None,
            "concept_name": None,
            "weight": 1,
        },
    ]

    _BINDINGS = [
        {"concept_anchor": "INVENTORY_LEVEL", "file_path": "sql/inv.sql", "binding_key": "b1"},
    ]

    def _run(self):
        with _patch_bindings(self._BINDINGS):
            return get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory(self._EDGES_WITH_DANGLING),
            )

    def test_skip_count_matches_dangling(self):
        self.assertEqual(self._run()["skip_count"], 2)

    def test_total_edges_counts_all(self):
        self.assertEqual(self._run()["total_edges"], 3)

    def test_pass_count_excludes_dangling(self):
        self.assertEqual(self._run()["pass_count"], 1)

    def test_dangling_do_not_appear_in_gap_concepts(self):
        gaps = self._run()["gap_concepts"]
        for g in gaps:
            self.assertTrue(g["intent_name"] and g["concept_name"])

    def test_status_ok_when_only_valid_edges_pass(self):
        result = self._run()
        self.assertEqual(result["status"], "ok")


class TestSweep1ConceptAnchorNormalization(unittest.TestCase):
    """concept:: prefix is stripped; anchor lookup is case-insensitive."""

    _EDGES = [
        {
            "intent_key": "k1",
            "intent_name": "Inventory Check",
            "concept_key": "ck1",
            "concept_name": "concept::inventory_level",
            "weight": 1,
        },
    ]

    _BINDINGS = [
        {"concept_anchor": "INVENTORY_LEVEL", "file_path": "sql/inv.sql", "binding_key": "b1"},
    ]

    def test_concept_prefix_stripped_and_matched(self):
        with _patch_bindings(self._BINDINGS):
            result = get_sweep1_coverage_gaps(
                _FAKE_MANIFEST,
                _arango_env_getter=_has_arango,
                _arango_factory=_make_factory(self._EDGES),
            )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["pass_count"], 1)
        self.assertEqual(result["gap_concepts"], [])


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in (
        TestSweep1CoverageGapsNoArango,
        TestSweep1CoverageGapsConnectionError,
        TestSweep1CoverageGapsNoEdges,
        TestSweep1CoverageGapsAllPassing,
        TestSweep1CoverageGapsFound,
        TestSweep1CoverageGapsDanglingVertices,
        TestSweep1ConceptAnchorNormalization,
    ):
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(
        f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
        f"{passed}/{result.testsRun} tests "
        f"({len(result.skipped)} skipped)"
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
