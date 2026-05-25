"""Tests that resolve_semantic_path covers all three disambiguation states.

Resolution states (#75):
  1. Resolved   — single valid concept found via bridge rows
  2. Unresolved — no Perspective_Intents or Perspective_Concepts bridge row
  3. Ambiguous  — multiple concepts for the same intent+perspective (modeling error)

Each state is tested against both the function return value and the
explanation string so the UI can display the right message.

Run: python hf-space-inventory-sqlgen/tests/test_disambiguation_states.py
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


def _make_engine(db_path: str):
    from sqlalchemy import create_engine
    return create_engine(f"sqlite:///{db_path}")


def _setup_minimal_schema(conn: sqlite3.Connection) -> None:
    """Create the minimum bridge tables needed for resolve_field_meaning."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_intents (
            intent_id INTEGER PRIMARY KEY,
            intent_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS schema_perspectives (
            perspective_id INTEGER PRIMARY KEY,
            perspective_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS schema_concepts (
            concept_id INTEGER PRIMARY KEY,
            concept_name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS schema_fields (
            field_id INTEGER PRIMARY KEY,
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            concept_id INTEGER,
            UNIQUE(table_name, field_name)
        );
        CREATE TABLE IF NOT EXISTS schema_concept_fields (
            id INTEGER PRIMARY KEY,
            concept_id INTEGER NOT NULL,
            table_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            UNIQUE(concept_id, table_name, field_name)
        );
        CREATE TABLE IF NOT EXISTS schema_intent_concepts (
            id INTEGER PRIMARY KEY,
            intent_id INTEGER NOT NULL,
            concept_id INTEGER NOT NULL,
            intent_factor_weight REAL DEFAULT 1,
            UNIQUE(intent_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS schema_intent_perspectives (
            id INTEGER PRIMARY KEY,
            intent_id INTEGER NOT NULL,
            perspective_id INTEGER NOT NULL,
            intent_factor_weight REAL DEFAULT 1,
            explanation TEXT,
            UNIQUE(intent_id, perspective_id)
        );
        CREATE TABLE IF NOT EXISTS schema_perspective_concepts (
            id INTEGER PRIMARY KEY,
            perspective_id INTEGER NOT NULL,
            concept_id INTEGER NOT NULL,
            UNIQUE(perspective_id, concept_id)
        );
    """)
    conn.commit()


def _insert_intent(conn, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO schema_intents (intent_name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT intent_id FROM schema_intents WHERE intent_name = ?", (name,)).fetchone()[0]


def _insert_perspective(conn, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO schema_perspectives (perspective_name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?", (name,)).fetchone()[0]


def _insert_concept(conn, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO schema_concepts (concept_name) VALUES (?)", (name,))
    conn.commit()
    return conn.execute("SELECT concept_id FROM schema_concepts WHERE concept_name = ?", (name,)).fetchone()[0]


def _link_ip(conn, intent_id: int, perspective_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_intent_perspectives (intent_id, perspective_id) VALUES (?, ?)",
        (intent_id, perspective_id),
    )
    conn.commit()


def _link_pc(conn, perspective_id: int, concept_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_perspective_concepts (perspective_id, concept_id) VALUES (?, ?)",
        (perspective_id, concept_id),
    )
    conn.commit()


def _insert_field(conn, table_name: str, field_name: str, concept_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_fields (table_name, field_name, concept_id) VALUES (?, ?, ?)",
        (table_name, field_name, concept_id),
    )
    # Also insert into schema_concept_fields which resolve_field_meaning JOINs on.
    conn.execute(
        "INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name) VALUES (?, ?, ?)",
        (concept_id, table_name, field_name),
    )
    conn.commit()


class TestDisambiguationStates(unittest.TestCase):

    def setUp(self):
        try:
            from semantic_reasoning import resolve_field_meaning
            self.resolve = resolve_field_meaning
        except ImportError as exc:
            self.skipTest(f"semantic_reasoning not importable: {exc}")

        self.tmp = tempfile.mktemp(suffix=".db")
        self.conn = sqlite3.connect(self.tmp)
        _setup_minimal_schema(self.conn)
        self.engine = _make_engine(self.tmp)

    def tearDown(self):
        self.conn.close()
        self.engine.dispose()
        try:
            os.unlink(self.tmp)
        except OSError:
            pass

    def test_state_resolved_single_concept(self):
        """State 1: single valid bridge path → resolved with explanation."""
        iid = _insert_intent(self.conn, "Quality")
        pid = _insert_perspective(self.conn, "Defect")
        cid = _insert_concept(self.conn, "defect_cost")
        _link_ip(self.conn, iid, pid)
        _link_pc(self.conn, pid, cid)
        _insert_field(self.conn, "quality_events", "cost", cid)

        result = self.resolve(self.engine, "Quality", "quality_events", "cost")
        self.assertIsNotNone(result, "resolve_semantic_path returned None for resolved path")
        exp = getattr(result, "explanation", "")
        self.assertTrue(
            exp.strip(),
            "Resolved path must have a non-empty explanation"
        )
        # State must NOT be "no valid path" or "MODELING ERROR"
        self.assertNotIn("No valid path", exp, f"Resolved path should not say 'No valid path': {exp!r}")
        self.assertNotIn("MODELING ERROR", exp, f"Resolved path should not say 'MODELING ERROR': {exp!r}")

    def test_state_unresolved_no_bridge_rows(self):
        """State 2: no Perspective_Intents rows → unresolved explanation."""
        _insert_intent(self.conn, "Quality")
        _insert_field(self.conn, "quality_events", "cost",
                      _insert_concept(self.conn, "defect_cost"))

        result = self.resolve(self.engine, "Quality", "quality_events", "cost")
        self.assertIsNotNone(result)
        exp = getattr(result, "explanation", "")
        unresolved_signals = ["No valid path", "no Perspective_Intents", "Unresolved", "no bridge row"]
        self.assertTrue(
            any(s.lower() in exp.lower() for s in unresolved_signals),
            f"Unresolved path explanation should mention missing bridge rows; got: {exp!r}"
        )

    def test_state_ambiguous_multiple_concepts(self):
        """State 3: multiple concepts both CAN_MEAN the same field → ambiguous / modeling error.

        For the ambiguous state to fire, BOTH concepts must be reachable through the
        bridge-row path AND both must appear in schema_concept_fields for the same
        (table_name, field_name) pair so that the final JOIN doesn't filter one out.
        """
        iid = _insert_intent(self.conn, "Quality")
        pid = _insert_perspective(self.conn, "Defect")
        cid1 = _insert_concept(self.conn, "defect_cost")
        cid2 = _insert_concept(self.conn, "defect_severity")
        _link_ip(self.conn, iid, pid)
        _link_pc(self.conn, pid, cid1)
        _link_pc(self.conn, pid, cid2)
        # Both concepts CAN_MEAN the same field → ambiguous resolution
        _insert_field(self.conn, "quality_events", "cost", cid1)
        # Insert concept_field entry for cid2 too so the JOIN doesn't filter it out
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_concept_fields (concept_id, table_name, field_name) VALUES (?, ?, ?)",
            (cid2, "quality_events", "cost"),
        )
        self.conn.commit()

        result = self.resolve(self.engine, "Quality", "quality_events", "cost")
        self.assertIsNotNone(result)
        exp = getattr(result, "explanation", "")
        ambiguous_signals = ["MODELING ERROR", "Ambiguous", "multiple concept", "2 concepts"]
        self.assertTrue(
            any(s.lower() in exp.lower() for s in ambiguous_signals),
            f"Ambiguous path explanation should mention modeling error; got: {exp!r}"
        )

    def test_all_three_states_have_non_empty_explanation(self):
        """All three resolution states must return a non-empty explanation."""
        iid = _insert_intent(self.conn, "TestIntent")
        pid = _insert_perspective(self.conn, "TestPerspective")

        # State 2: no bridge rows
        r_unresolved = self.resolve(self.engine, "TestIntent", "t", "f")
        self.assertTrue(getattr(r_unresolved, "explanation", "").strip(),
                        "Unresolved state must have explanation")

        # State 1: single concept
        cid = _insert_concept(self.conn, "test_concept")
        _link_ip(self.conn, iid, pid)
        _link_pc(self.conn, pid, cid)
        r_resolved = self.resolve(self.engine, "TestIntent", "t", "f")
        self.assertTrue(getattr(r_resolved, "explanation", "").strip(),
                        "Resolved state must have explanation")

        # State 3: two concepts
        cid2 = _insert_concept(self.conn, "test_concept_2")
        _link_pc(self.conn, pid, cid2)
        r_ambiguous = self.resolve(self.engine, "TestIntent", "t", "f")
        self.assertTrue(getattr(r_ambiguous, "explanation", "").strip(),
                        "Ambiguous state must have explanation")


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDisambiguationStates)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
