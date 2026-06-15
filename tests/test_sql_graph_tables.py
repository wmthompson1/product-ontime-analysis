"""Tests for the SQLite graph source tables (sql_graph_nodes / sql_graph_edges).

These guard the contract that the exporter materializes the canonical graph into
SQLite and then serializes the JSON FROM those tables — so SQLite is a provable
source of truth for graph_metadata.json. They cover:

  * round-trip fidelity (materialize → read back == original dicts, exact fields)
  * emission ordering preserved via the ``ordinal`` column
  * idempotency (materializing twice yields identical rows)
  * the document built from the tables matches the document built directly
  * the committed manufacturing.db and graph_metadata.json are in parity
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "replit_integrations"))

import export_graph_metadata as ex  # noqa: E402
import sql_graph_parity_check as parity  # noqa: E402


def _sample_graph():
    """A small but representative slice mirroring the exporter's dict shapes."""
    table_nodes = [
        {
            "_id": f"{ex.NODE_COLLECTION}/CUSTOMER",
            "_key": "CUSTOMER",
            "node_type": "table",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_slot": ex.PLACEHOLDER_ENTITY,
            "predicate": "none",
            "unique_id": "none",
            "description": "Customer master",
        },
    ]
    column_nodes = [
        {
            "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "_key": "column::CUSTOMER.ID",
            "node_type": "column",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_name": "ID",
            "predicate": "none",
            "unique_id": "none",
            "column_type": "INTEGER",
            "notnull": True,
            "default_value": None,
            "primary_key": True,
            "foreign_key": False,
        },
        {
            "_id": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_key": "column::CUSTOMER.NAME",
            "node_type": "column",
            "node_family": ex.FAMILY_STRUCTURAL,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "table_name": "CUSTOMER",
            "column_name": "NAME",
            "predicate": "none",
            "unique_id": "none",
            "column_type": "TEXT",
            "notnull": False,
            "default_value": "'anon'",
            "primary_key": False,
            "foreign_key": False,
        },
    ]
    edges = [
        {
            "_id": f"{ex.EDGE_COLLECTION}/hc_CUSTOMER_ID",
            "_key": "hc_CUSTOMER_ID",
            "_from": f"{ex.NODE_COLLECTION}/CUSTOMER",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "edge_family": ex.FAMILY_STRUCTURAL,
            "edge_type": ex.EDGE_PREDICATE_HAS_COLUMN,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "unique_id": "CUS_HAS_ID_001",
        },
        {
            "_id": f"{ex.EDGE_COLLECTION}/ref_ORDER_CUSTOMER",
            "_key": "ref_ORDER_CUSTOMER",
            "_from": f"{ex.NODE_COLLECTION}/column::ORDER.CUSTOMER_ID",
            "_to": f"{ex.NODE_COLLECTION}/column::CUSTOMER.ID",
            "edge_family": ex.FAMILY_STRUCTURAL,
            "edge_type": ex.EDGE_PREDICATE_REFERENCES,
            "perspective": ex.PERSPECTIVE_SYSTEM,
            "unique_id": "none",
            "references_table": "CUSTOMER",
            "references_column": "ID",
        },
        {
            "_id": f"{ex.EDGE_COLLECTION}/res_CUSTOMER_NAME",
            "_key": "res_CUSTOMER_NAME",
            "_from": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_to": ex.concept_id("CustomerNameSales"),
            "edge_family": ex.FAMILY_SEMANTIC,
            "edge_type": ex.EDGE_PREDICATE_ELEVATES,
            "perspective": "Sales",
            "unique_id": "SAL_RES_CUS_NAM_1A2B3C4D",
            "weight": 1,
            "priority_weight": 3,
            "field_component": 1,
        },
    ]
    return table_nodes, column_nodes, edges


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_materialize_then_load_is_exact(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)

        loaded_nodes = ex._load_nodes_from_sqlite(self.conn)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)

        # Exact field set + values + ordering (table nodes precede column nodes).
        self.assertEqual(loaded_nodes, table_nodes + column_nodes)
        self.assertEqual(loaded_edges, edges)

    def test_row_counts_match_inputs(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        n_nodes = self.conn.execute(
            f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_NODES_TABLE}"
        ).fetchone()[0]
        n_edges = self.conn.execute(
            f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_EDGES_TABLE}"
        ).fetchone()[0]
        self.assertEqual(n_nodes, len(table_nodes) + len(column_nodes))
        self.assertEqual(n_edges, len(edges))

    def test_materialize_is_idempotent(self):
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        first_nodes = ex._load_nodes_from_sqlite(self.conn)
        first_edges = ex._load_edges_from_sqlite(self.conn)

        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        second_nodes = ex._load_nodes_from_sqlite(self.conn)
        second_edges = ex._load_edges_from_sqlite(self.conn)

        self.assertEqual(first_nodes, second_nodes)
        self.assertEqual(first_edges, second_edges)
        self.assertEqual(
            self.conn.execute(f"SELECT COUNT(*) FROM {ex.SQL_GRAPH_NODES_TABLE}").fetchone()[0],
            len(table_nodes) + len(column_nodes),
        )

    def test_field_component_round_trips_for_multiple_definitions(self):
        """A field with N definitions yields N resolves_to edges numbered 1..N, and
        ``field_component`` survives the materialize → read-back round trip."""
        table_nodes, column_nodes, edges = _sample_graph()
        # Give CUSTOMER.NAME a second meaning (component 2) under another
        # perspective — same source column, distinct definition.
        edges.append({
            "_id": f"{ex.EDGE_COLLECTION}/res_CUSTOMER_NAME_2",
            "_key": "res_CUSTOMER_NAME_2",
            "_from": f"{ex.NODE_COLLECTION}/column::CUSTOMER.NAME",
            "_to": ex.concept_id("CustomerNameMarketing"),
            "edge_family": ex.FAMILY_SEMANTIC,
            "edge_type": ex.EDGE_PREDICATE_ELEVATES,
            "perspective": "Marketing",
            "unique_id": "MAR_RES_CUS_NAM_5E6F7A8B",
            "weight": 1,
            "priority_weight": 3,
            "field_component": 2,
        })
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)
        self.assertEqual(loaded_edges, edges)

        resolves = [e for e in loaded_edges
                    if e["edge_type"] == ex.EDGE_PREDICATE_ELEVATES]
        self.assertEqual(
            sorted(e["field_component"] for e in resolves), [1, 2],
            "two definitions of one field must carry field_component 1 and 2",
        )

    def test_non_elevates_edges_omit_field_component(self):
        """field_component is a resolves_to-only attribute; structural edges never
        carry it (its column is NULL for them and absent from their dict)."""
        table_nodes, column_nodes, edges = _sample_graph()
        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        loaded_edges = ex._load_edges_from_sqlite(self.conn)
        for e in loaded_edges:
            if e["edge_type"] != ex.EDGE_PREDICATE_ELEVATES:
                self.assertNotIn("field_component", e)

    def test_document_from_tables_matches_direct(self):
        table_nodes, column_nodes, edges = _sample_graph()
        integrity = {
            "tables_without_columns": [],
            "foreign_keys_skipped": [],
            "semantic_elevations_skipped": [],
        }
        direct = ex._build_graph_document(table_nodes + column_nodes, edges, integrity)

        ex._materialize_to_sqlite(self.conn, table_nodes, column_nodes, edges)
        from_tables = ex._build_graph_document(
            ex._load_nodes_from_sqlite(self.conn),
            ex._load_edges_from_sqlite(self.conn),
            integrity,
        )

        # Ignore the volatile document timestamp; everything else must match.
        direct.pop("synced_at", None)
        from_tables.pop("synced_at", None)
        self.assertEqual(direct, from_tables)


class ConceptPayloadRoundTrip(unittest.TestCase):
    """M3: a concept node carries concept_type, domain, and authored JSON-array
    synonyms / tags alongside its description. All four survive the materialize ->
    read-back round trip; a concept with blank/empty metadata comes back as
    "" / [] (never None); authored synonym order is preserved (never re-sorted)."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def _concept(self, name, ctype, domain, synonyms, tags, desc):
        return {
            "_id": ex.concept_id(name),
            "_key": ex.concept_key(name),
            "node_type": "concept",
            "node_family": ex.FAMILY_SEMANTIC,
            "perspective": ex.PERSPECTIVE_CANONICAL,
            "concept_name": name,
            "concept_type": ctype,
            "domain": domain,
            "synonyms": synonyms,
            "tags": tags,
            "predicate": "none",
            "unique_id": "none",
            "description": desc,
        }

    def test_full_payload_round_trips(self):
        concept = self._concept(
            "ReorderPoint", "metric", "operations",
            ["ROP", "reorder level"], ["mrp", "inventory"],
            "Inventory level that triggers replenishment",
        )
        ex._materialize_to_sqlite(self.conn, [], [], [], [concept])
        self.assertEqual(ex._load_nodes_from_sqlite(self.conn), [concept])

    def test_empty_metadata_defaults_to_blank_and_empty_lists(self):
        # A glossary-only concept with no synonyms/tags and blank type/domain must
        # come back as "" / [] (never None), matching _fetch_concept_nodes.
        concept = self._concept("SafetyStock", "", "", [], [], "")
        ex._materialize_to_sqlite(self.conn, [], [], [], [concept])
        loaded = ex._load_nodes_from_sqlite(self.conn)
        self.assertEqual(loaded, [concept])
        self.assertEqual(loaded[0]["synonyms"], [])
        self.assertEqual(loaded[0]["tags"], [])

    def test_synonym_order_is_preserved(self):
        ordered = ["zeta", "alpha", "mike"]
        concept = self._concept(
            "LeadTime", "metric", "operations", ordered, ["mrp"], "lead time",
        )
        ex._materialize_to_sqlite(self.conn, [], [], [], [concept])
        self.assertEqual(
            ex._load_nodes_from_sqlite(self.conn)[0]["synonyms"], ordered,
            "authored synonym order must survive the round trip (never re-sorted)",
        )


# The sql_graph_nodes shape that predates the concept node type: node_type CHECK
# admits only table/column, table_name is NOT NULL, and there is no concept_name
# column. This is what an old manufacturing.db carries before M1.
_LEGACY_NODES_DDL = """
CREATE TABLE sql_graph_nodes (
    ordinal       INTEGER NOT NULL,
    _key          TEXT    NOT NULL PRIMARY KEY,
    _id           TEXT    NOT NULL,
    node_type     TEXT    NOT NULL CHECK(node_type IN ('table', 'column')),
    node_family   TEXT    NOT NULL,
    perspective   TEXT    NOT NULL,
    table_name    TEXT    NOT NULL,
    column_name   TEXT,
    column_slot   TEXT,
    predicate     TEXT    NOT NULL,
    unique_id     TEXT    NOT NULL,
    description   TEXT,
    column_type   TEXT,
    "notnull"     INTEGER,
    default_value TEXT,
    primary_key   INTEGER,
    foreign_key   INTEGER
);
"""


class LegacyDbMigration(unittest.TestCase):
    """The exporter must rebuild an old sql_graph_nodes even after app.py's boot
    guard has additively bolted on the concept_name column (which leaves the old
    CHECK + table_name NOT NULL intact). Keying the rebuild on the column alone
    would miss this half-migrated state and break concept inserts."""

    def _half_migrated_conn(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(_LEGACY_NODES_DDL)
        # Simulate app.py's additive boot guard adding only the new column.
        conn.execute("ALTER TABLE sql_graph_nodes ADD COLUMN concept_name TEXT")
        return conn

    def test_half_migrated_table_is_detected_stale(self):
        conn = self._half_migrated_conn()
        self.addCleanup(conn.close)
        self.assertTrue(
            ex._sql_graph_nodes_is_stale(conn),
            "old table with concept_name bolted on must still be seen as stale",
        )

    def test_fresh_modern_table_is_not_stale(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(ex.SQL_GRAPH_DDL)
        self.assertFalse(ex._sql_graph_nodes_is_stale(conn))

    def test_ensure_rebuilds_half_migrated_table_so_concept_inserts(self):
        conn = self._half_migrated_conn()
        self.addCleanup(conn.close)

        ex._ensure_sql_graph_tables(conn)

        # A concept row has table_name NULL and node_type 'concept' — both of
        # which the legacy shape rejected. After the rebuild it must insert.
        name = "CertificationType"
        key = ex.concept_key(name)
        conn.execute(
            f"INSERT INTO {ex.SQL_GRAPH_NODES_TABLE} "
            "(ordinal, _key, _id, node_type, node_family, perspective, "
            " table_name, concept_name, predicate, unique_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (1, key, ex.concept_id(name), "concept", ex.FAMILY_SEMANTIC,
             ex.PERSPECTIVE_CANONICAL, None, name, "none", "none"),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT node_type, table_name, concept_name FROM {ex.SQL_GRAPH_NODES_TABLE}"
        ).fetchone()
        self.assertEqual(row, ("concept", None, name))


class ElevatesRepoint(unittest.TestCase):
    """M2: a resolves_to edge runs column node -> concept node, carries a binary
    weight gate plus the raw priority_weight, drops the concept string, and gets
    a concept-stable uid that survives sibling churn."""

    def _rows(self, specs):
        # specs: list of (concept, priority_weight, field_component)
        return [
            {"table_name": "CUSTOMER", "column_name": "NAME",
             "perspective": "Sales", "concept": c,
             "priority_weight": pw, "field_component": fc}
            for (c, pw, fc) in specs
        ]

    def _integrity(self):
        return {"tables_without_columns": [], "foreign_keys_skipped": [],
                "semantic_elevations_skipped": []}

    def test_edge_points_from_column_to_concept_node(self):
        edges = ex._build_elevates_edges(
            self._rows([("OrderState", 3, 1)]),
            {("CUSTOMER", "NAME")}, {"OrderState"}, self._integrity())
        self.assertEqual(len(edges), 1)
        e = edges[0]
        self.assertEqual(e["_from"], ex.column_id("CUSTOMER", "NAME"))
        self.assertEqual(e["_to"], ex.concept_id("OrderState"))
        self.assertNotEqual(e["_from"], e["_to"])  # no self-loop
        self.assertNotIn("concept", e)             # concept string dropped

    def test_weight_is_normalized_to_binary_gate(self):
        edges = ex._build_elevates_edges(
            self._rows([("Hot", 5, 1), ("Cold", 0, 1)]),
            {("CUSTOMER", "NAME")}, {"Hot", "Cold"}, self._integrity())
        by_to = {e["_to"]: e for e in edges}
        hot = by_to[ex.concept_id("Hot")]
        cold = by_to[ex.concept_id("Cold")]
        self.assertEqual((hot["weight"], hot["priority_weight"]), (1, 5))
        self.assertEqual((cold["weight"], cold["priority_weight"]), (0, 0))

    def test_missing_concept_node_is_skipped_and_recorded(self):
        integ = self._integrity()
        edges = ex._build_elevates_edges(
            self._rows([("Ghost", 3, 1)]), {("CUSTOMER", "NAME")}, set(), integ)
        self.assertEqual(edges, [])
        self.assertEqual(len(integ["semantic_elevations_skipped"]), 1)
        msg = integ["semantic_elevations_skipped"][0]
        self.assertIn("Ghost", msg)
        self.assertIn("concept not a canonical node", msg)

    def test_missing_column_node_is_skipped_and_recorded(self):
        integ = self._integrity()
        edges = ex._build_elevates_edges(
            self._rows([("OrderState", 3, 1)]), set(), {"OrderState"}, integ)
        self.assertEqual(edges, [])
        self.assertEqual(len(integ["semantic_elevations_skipped"]), 1)
        self.assertIn("column not a canonical node",
                      integ["semantic_elevations_skipped"][0])

    def test_uid_is_deterministic_and_concept_aware(self):
        a = ex.semantic_uid_stable("Sales", "CUSTOMER", "NAME", "C1", 1)
        b = ex.semantic_uid_stable("Sales", "CUSTOMER", "NAME", "C1", 1)
        c = ex.semantic_uid_stable("Sales", "CUSTOMER", "NAME", "C2", 1)
        self.assertEqual(a, b)       # deterministic, not a counter
        self.assertNotEqual(a, c)    # derived from the concept

    def test_sibling_concept_churn_does_not_renumber_uids(self):
        node_index = {("CUSTOMER", "NAME")}
        both = ex._build_elevates_edges(
            self._rows([("Keep", 3, 1), ("Drop", 3, 1)]),
            node_index, {"Keep", "Drop"}, self._integrity())
        keep_before = {e["_to"]: e["unique_id"] for e in both}[ex.concept_id("Keep")]
        # Remove the sibling 'Drop'; 'Keep's uid (and thus _key) must not shift.
        one = ex._build_elevates_edges(
            self._rows([("Keep", 3, 1)]), node_index, {"Keep"}, self._integrity())
        self.assertEqual(keep_before, one[0]["unique_id"])


# The sql_graph_edges shape that predates the M2 resolves_to re-point: it carries the
# now-removed `concept` string and lacks `priority_weight`. This is what an old
# manufacturing.db (<= v13) carries before M2.
_LEGACY_EDGES_DDL = """
CREATE TABLE sql_graph_edges (
    ordinal           INTEGER NOT NULL,
    _key              TEXT    NOT NULL PRIMARY KEY,
    _id               TEXT    NOT NULL,
    _from             TEXT    NOT NULL,
    _to               TEXT    NOT NULL,
    edge_family       TEXT    NOT NULL,
    edge_type         TEXT    NOT NULL CHECK(edge_type IN ('has_column', 'references', 'elevates')),
    perspective       TEXT    NOT NULL,
    unique_id         TEXT    NOT NULL,
    references_table  TEXT,
    references_column TEXT,
    weight            INTEGER,
    concept           TEXT,
    field_component   INTEGER
);
"""


class LegacyEdgesMigration(unittest.TestCase):
    """The exporter must rebuild an old sql_graph_edges that predates M2: drop the
    `concept` string column and add `priority_weight`. app.py's additive boot
    guard can add priority_weight while leaving `concept` behind, so a lingering
    `concept` column alone must still keep the table stale."""

    def _legacy_conn(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(_LEGACY_EDGES_DDL)
        return conn

    def test_legacy_edges_with_concept_is_stale(self):
        conn = self._legacy_conn()
        self.addCleanup(conn.close)
        self.assertTrue(ex._sql_graph_edges_is_stale(conn))

    def test_half_migrated_edges_with_concept_and_priority_weight_is_stale(self):
        conn = self._legacy_conn()
        self.addCleanup(conn.close)
        conn.execute("ALTER TABLE sql_graph_edges ADD COLUMN priority_weight INTEGER")
        self.assertTrue(
            ex._sql_graph_edges_is_stale(conn),
            "a lingering concept column must keep the table stale even after "
            "priority_weight is bolted on by the app boot guard",
        )

    def test_fresh_modern_edges_is_not_stale(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript(ex.SQL_GRAPH_DDL)
        self.assertFalse(ex._sql_graph_edges_is_stale(conn))

    def test_ensure_rebuilds_legacy_edges_drops_concept_adds_priority_weight(self):
        conn = self._legacy_conn()
        self.addCleanup(conn.close)

        ex._ensure_sql_graph_tables(conn)

        cols = {row[1] for row in conn.execute("PRAGMA table_info(sql_graph_edges)")}
        self.assertNotIn("concept", cols)
        self.assertIn("priority_weight", cols)
        # A re-pointed resolves_to row (priority_weight set, no concept, _to=concept)
        # must insert into the rebuilt table.
        conn.execute(
            f"INSERT INTO {ex.SQL_GRAPH_EDGES_TABLE} "
            "(ordinal, _key, _id, _from, _to, edge_family, edge_type, "
            " perspective, unique_id, weight, priority_weight, field_component) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (1, "k", "i", ex.column_id("CUSTOMER", "NAME"),
             ex.concept_id("OrderState"), ex.FAMILY_SEMANTIC,
             ex.EDGE_PREDICATE_ELEVATES, "Sales", "SAL_RES_CUS_NAM_DEADBEEF",
             1, 7, 1),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT _to, weight, priority_weight FROM {ex.SQL_GRAPH_EDGES_TABLE}"
        ).fetchone()
        self.assertEqual(row, (ex.concept_id("OrderState"), 1, 7))


class CommittedParity(unittest.TestCase):
    def test_committed_db_matches_committed_json(self):
        if not (os.path.exists(ex.DB_PATH) and os.path.exists(ex.JSON_PATH)):
            self.skipTest("committed manufacturing.db or graph_metadata.json not present")
        # If the tables have not been materialized yet, treat as a skip rather
        # than a failure (the post-merge gate uses the strict, non-skip mode).
        rc = parity.check_parity(ex.DB_PATH, ex.JSON_PATH, skip_on_missing=True)
        self.assertEqual(rc, 0, "committed graph_metadata.json is not in parity with the SQLite graph tables")


if __name__ == "__main__":
    unittest.main()
