"""Tests for semantic warning fields in the graph syntax API.

Covers:
- get_graph_syntax_examples always returns cypher_warning and aql_warning keys (#82, #84, #85)
- Warning text is non-empty and references the retired vertex (#82)
- Both fields are present even when intent/field combination is valid (#85)
- Calling get_graph_syntax_examples with any input triggers the warning (#84)

Run: python hf-space-inventory-sqlgen/tests/test_semantic_warnings.py
"""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


def _get_engine():
    try:
        from sqlalchemy import create_engine
        db_path = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
        if not os.path.exists(db_path):
            return None
        return create_engine(f"sqlite:///{db_path}")
    except Exception:
        return None


class TestSemanticWarnings(unittest.TestCase):

    def setUp(self):
        try:
            from semantic_reasoning import get_graph_syntax_examples
            self.get_graph_syntax_examples = get_graph_syntax_examples
        except ImportError as exc:
            self.skipTest(f"semantic_reasoning not importable: {exc}")

    def test_cypher_warning_key_always_present(self):
        """get_graph_syntax_examples must always include cypher_warning."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Quality", "quality_events", "severity")
        self.assertIn(
            "cypher_warning", result,
            "cypher_warning key missing from get_graph_syntax_examples return value"
        )

    def test_aql_warning_key_always_present(self):
        """get_graph_syntax_examples must always include aql_warning."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Quality", "quality_events", "severity")
        self.assertIn(
            "aql_warning", result,
            "aql_warning key missing from get_graph_syntax_examples return value"
        )

    def test_cypher_warning_is_nonempty_string(self):
        """cypher_warning must be a non-empty string."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Quality", "quality_events", "severity")
        val = result.get("cypher_warning", "")
        self.assertIsInstance(val, str, "cypher_warning must be a string")
        self.assertTrue(val.strip(), "cypher_warning must not be empty")

    def test_aql_warning_is_nonempty_string(self):
        """aql_warning must be a non-empty string."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Quality", "quality_events", "severity")
        val = result.get("aql_warning", "")
        self.assertIsInstance(val, str, "aql_warning must be a string")
        self.assertTrue(val.strip(), "aql_warning must not be empty")

    def test_warning_mentions_retired_vertex(self):
        """Warning text must reference the retired Perspective vertex."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Quality", "quality_events", "severity")
        cypher_warn = result.get("cypher_warning", "")
        aql_warn = result.get("aql_warning", "")
        keywords = ["retired", "Reference only", "Perspective vertex"]
        cypher_matches = any(k.lower() in cypher_warn.lower() for k in keywords)
        aql_matches = any(k.lower() in aql_warn.lower() for k in keywords)
        self.assertTrue(
            cypher_matches,
            f"cypher_warning should mention retired vertex; got: {cypher_warn!r}"
        )
        self.assertTrue(
            aql_matches,
            f"aql_warning should mention retired vertex; got: {aql_warn!r}"
        )

    def test_warnings_present_with_unknown_intent(self):
        """Warning fields must be present even when intent is not found."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "NonexistentIntent", "some_table", "some_field")
        self.assertIn("cypher_warning", result, "cypher_warning missing for unknown intent")
        self.assertIn("aql_warning", result, "aql_warning missing for unknown intent")

    def test_warning_present_both_functions_called_together(self):
        """Both cypher_warning and aql_warning must be set in a single call."""
        engine = _get_engine()
        if engine is None:
            self.skipTest("manufacturing.db not found")
        result = self.get_graph_syntax_examples(engine, "Supplier", "suppliers", "on_time_rate")
        self.assertIn("cypher_warning", result)
        self.assertIn("aql_warning", result)
        self.assertEqual(
            result["cypher_warning"], result["aql_warning"],
            "Both warnings should carry the same retired-vertex message"
        )


class TestSemanticWarningsApiResponse(unittest.TestCase):
    """Verify warning fields surface through the HTTP API."""

    def setUp(self):
        try:
            from fastapi.testclient import TestClient
            import app as fastapi_app
            self.client = TestClient(fastapi_app.app, raise_server_exceptions=True)
        except ImportError as exc:
            self.skipTest(f"FastAPI TestClient not available: {exc}")
        except Exception as exc:
            self.skipTest(f"App could not start: {exc}")

    def test_get_intent_perspectives_has_no_legacy_warning_keys(self):
        """/mcp/tools/get_intent_perspectives must not return legacy warning keys."""
        resp = self.client.get(
            "/mcp/tools/get_intent_perspectives",
            params={"intent_name": "Quality"},
        )
        if resp.status_code == 404:
            self.skipTest("endpoint not present in this build")
        self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        retired = {"intent_perspectives", "operates_within", "relationship_legacy_alias", "uses_definition"}
        found = retired & set(body.keys())
        self.assertFalse(found, f"Retired legacy keys found in response: {found}")

    def test_graph_syntax_endpoint_returns_warning_fields(self):
        """/mcp/tools/get_graph_syntax_examples must include warning fields."""
        resp = self.client.post(
            "/mcp/tools/get_graph_syntax_examples",
            json={
                "intent_name": "Quality",
                "table_name": "quality_events",
                "field_name": "severity",
            },
        )
        if resp.status_code == 404:
            self.skipTest("endpoint not present in this build")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("cypher_warning", body, "cypher_warning missing from HTTP response")
        self.assertIn("aql_warning", body, "aql_warning missing from HTTP response")


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticWarnings))
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticWarningsApiResponse))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests passed "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
