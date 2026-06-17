"""Tests for the SQL vs AQL parity check (sql_aql_parity_check.py).

These prove the SQLite graph tables can be compared field-for-field against the
*live* ArangoDB graph using AQL, without needing a real ArangoDB: a fake ``db``
is injected whose ``aql.execute`` replays the SQLite-sourced documents (with a
volatile ``_rev`` added, to prove it is stripped) in shuffled order (to prove the
check is order-independent).

Covered:
  * parity passes when the live graph mirrors SQLite (server _rev ignored)
  * the check is order-independent (AQL returns documents unordered)
  * a single drifted field is caught
  * an extra / missing document is caught
  * an unreachable or unconfigured ArangoDB is a skip (exit 0), unless required
"""
import os
import random
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "replit_integrations"))

import export_graph_metadata as ex  # noqa: E402
import sql_aql_parity_check as aqlp  # noqa: E402


def _sample_graph():
    table_nodes = [{
        "_id": f"{ex.NODE_COLLECTION}/CUSTOMER", "_key": "CUSTOMER",
        "node_type": "table", "node_family": ex.FAMILY_STRUCTURAL,
        "perspective": ex.PERSPECTIVE_SYSTEM, "table_name": "CUSTOMER",
        "column_slot": ex.PLACEHOLDER_ENTITY, "predicate": "none",
        "unique_id": "none", "description": "Customer master",
    }]
    column_nodes = [{
        "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID", "_key": "column::CUSTOMER.ID",
        "node_type": "column", "node_family": ex.FAMILY_STRUCTURAL,
        "perspective": ex.PERSPECTIVE_SYSTEM, "table_name": "CUSTOMER",
        "column_name": "ID", "predicate": "none", "unique_id": "none",
        "column_type": "INTEGER", "notnull": True, "default_value": None,
        "primary_key": True, "foreign_key": False,
    }, {
        "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME", "_key": "column::CUSTOMER.NAME",
        "node_type": "column", "node_family": ex.FAMILY_STRUCTURAL,
        "perspective": ex.PERSPECTIVE_SYSTEM, "table_name": "CUSTOMER",
        "column_name": "NAME", "predicate": "none", "unique_id": "none",
        "column_type": "TEXT", "notnull": False, "default_value": None,
        "primary_key": False, "foreign_key": False,
    }]
    concept_nodes = [{
        "_id": ex.concept_id("CustomerNameSales"),
        "_key": ex.concept_key("CustomerNameSales"),
        "node_type": "concept", "node_family": ex.FAMILY_SEMANTIC,
        "perspective": ex.PERSPECTIVE_CANONICAL, "concept_name": "CustomerNameSales",
        # M3: the richer concept payload (type / domain / synonyms / tags) must
        # round-trip field-for-field through the live-AQL parity flattener too.
        "concept_type": "classification", "domain": "customer",
        "synonyms": ["account name", "client name"], "tags": ["sales", "crm"],
        # M4: a non-metric concept stores no computation_template; it must still
        # round-trip field-for-field (as None) through the live-AQL flattener.
        "computation_template": None,
        "predicate": "none", "unique_id": "none",
        "description": "Customer name under the Sales lens",
    }]
    edges = [{
        "_id": f"{ex.EDGE_COLLECTION}/hc_CUSTOMER_ID", "_key": "hc_CUSTOMER_ID",
        "_from": f"{ex.NODE_COLLECTION}/CUSTOMER",
        "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
        "edge_family": ex.FAMILY_STRUCTURAL, "edge_type": ex.EDGE_PREDICATE_HAS_COLUMN,
        "perspective": ex.PERSPECTIVE_SYSTEM, "unique_id": "CUS_HAS_ID_001",
    }, {
        # M2: a re-pointed resolves_to edge (column -> concept node, no concept string,
        # binary weight + raw priority_weight) must round-trip field-for-field
        # through the live-AQL parity flattener too.
        "_id": f"{ex.EDGE_COLLECTION}/res_CUSTOMER_NAME", "_key": "res_CUSTOMER_NAME",
        "_from": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
        "_to": ex.concept_id("CustomerNameSales"),
        "edge_family": ex.FAMILY_SEMANTIC, "edge_type": ex.EDGE_PREDICATE_ELEVATES,
        "perspective": "Sales", "unique_id": "SAL_RES_CUS_NAM_1A2B3C4D",
        "weight": 1, "priority_weight": 3, "field_component": 1,
        # M4: a categorical elevation names no template {variable}; it must still
        # round-trip field-for-field (as None) through the live-AQL flattener.
        "variable_name": None,
    }]
    return table_nodes, column_nodes, concept_nodes, edges


class FakeAql:
    """Replays per-collection documents for a ``FOR d IN <col> RETURN d`` query."""

    def __init__(self, data: dict):
        self._data = data

    def execute(self, query: str, **_kw):
        for col, rows in self._data.items():
            if f" IN {col} " in f" {query} ":
                shuffled = list(rows)
                random.Random(7).shuffle(shuffled)
                return iter(shuffled)
        return iter(())


class FakeDb:
    def __init__(self, nodes, edges):
        # Add a server-only _rev to every doc to prove flatten() strips it.
        def with_rev(rows):
            return [dict(r, _rev=f"_rev_{i}") for i, r in enumerate(rows)]
        self.aql = FakeAql({
            ex.NODE_COLLECTION: with_rev(nodes),
            ex.EDGE_COLLECTION: with_rev(edges),
        })


class SqlAqlParity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        table_nodes, column_nodes, concept_nodes, edges = _sample_graph()
        conn = sqlite3.connect(self.db_path)
        try:
            ex._materialize_to_sqlite(conn, table_nodes, column_nodes, edges, concept_nodes)
            conn.commit()
        finally:
            conn.close()
        # The canonical docs the live graph should mirror.
        self.exp_nodes = table_nodes + column_nodes + concept_nodes
        self.exp_edges = edges

    def tearDown(self):
        os.unlink(self.db_path)

    def test_parity_passes_ignoring_rev_and_order(self):
        rc = aqlp.check_sql_aql_parity(
            self.db_path,
            arango_factory=lambda: FakeDb(self.exp_nodes, self.exp_edges),
            env_get=lambda k: "set",
        )
        self.assertEqual(rc, 0)

    def test_field_drift_is_caught(self):
        bad_nodes = [dict(n) for n in self.exp_nodes]
        bad_nodes[0] = dict(bad_nodes[0], description="TAMPERED")
        rc = aqlp.check_sql_aql_parity(
            self.db_path,
            arango_factory=lambda: FakeDb(bad_nodes, self.exp_edges),
            env_get=lambda k: "set",
        )
        self.assertEqual(rc, 1)

    def test_extra_document_is_caught(self):
        extra = dict(self.exp_nodes[0], _id=f"{ex.NODE_COLLECTION}/GHOST", _key="GHOST")
        rc = aqlp.check_sql_aql_parity(
            self.db_path,
            arango_factory=lambda: FakeDb(self.exp_nodes + [extra], self.exp_edges),
            env_get=lambda k: "set",
        )
        self.assertEqual(rc, 1)

    def test_missing_document_is_caught(self):
        rc = aqlp.check_sql_aql_parity(
            self.db_path,
            arango_factory=lambda: FakeDb(self.exp_nodes, []),
            env_get=lambda k: "set",
        )
        self.assertEqual(rc, 1)

    def test_unconfigured_arango_is_skip(self):
        rc = aqlp.check_sql_aql_parity(self.db_path, env_get=lambda k: None)
        self.assertEqual(rc, 0)

    def test_unconfigured_arango_is_failure_when_required(self):
        rc = aqlp.check_sql_aql_parity(
            self.db_path, env_get=lambda k: None, require_arango=True
        )
        self.assertEqual(rc, 1)

    def test_connection_failure_is_skip(self):
        def boom():
            raise RuntimeError("no route to host")
        rc = aqlp.check_sql_aql_parity(
            self.db_path, arango_factory=boom, env_get=lambda k: "set"
        )
        self.assertEqual(rc, 0)

    def test_missing_sqlite_is_error_without_skip(self):
        rc = aqlp.check_sql_aql_parity(
            "/nonexistent/manufacturing.db", env_get=lambda k: "set"
        )
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
