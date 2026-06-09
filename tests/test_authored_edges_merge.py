"""Tests for SME-authored edge merging in the canonical graph exporter.

The Define Relationship UI writes canonical edges to ``sql_graph_authored_edges``
(SQLite source of truth). The exporter MERGES those rows into its derived
foreign-key / elevation feeds every run, so authored relationships survive the
delete+reinsert of ``sql_graph_edges`` and flow through export -> sync.

These guard the merge contract directly (no live ArangoDB required):

  * references authored rows with both columns fold into the FK feed
  * column-less references rows are skipped (cannot form a column->column edge)
  * elevates authored rows with a column fold into the elevation feed
  * column-less elevates rows are skipped
  * has_column authored rows are a no-op (derived backbone already covers them)
  * de-duplication against rows the derived feeds already contain
  * _fetch_authored_edges tolerates an older DB that lacks the table
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "replit_integrations"))

import export_graph_metadata as ex  # noqa: E402


def _authored(edge_type, from_table, to_table, from_column="", to_column="",
              perspective="system", weight=None, concept=None):
    return {
        "edge_type": edge_type,
        "from_table": from_table,
        "from_column": from_column,
        "to_table": to_table,
        "to_column": to_column,
        "perspective": perspective,
        "weight": weight,
        "concept": concept,
    }


class TestMergeReferences(unittest.TestCase):
    def test_references_with_columns_folds_into_fk_feed(self):
        authored = [_authored("references", "orders", "part",
                              from_column="part_ref", to_column="part_id")]
        fks, elevs = ex._merge_authored_into_sources(authored, [], [])
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0], {
            "child_table": "orders", "child_column": "part_ref",
            "parent_table": "part", "parent_column": "part_id",
        })
        self.assertEqual(elevs, [])

    def test_column_less_references_skipped(self):
        authored = [_authored("references", "orders", "part")]
        fks, _ = ex._merge_authored_into_sources(authored, [], [])
        self.assertEqual(fks, [])

    def test_references_deduped_against_existing(self):
        existing = [{
            "child_table": "orders", "child_column": "part_ref",
            "parent_table": "part", "parent_column": "part_id",
        }]
        authored = [_authored("references", "orders", "part",
                              from_column="part_ref", to_column="part_id")]
        fks, _ = ex._merge_authored_into_sources(authored, existing, [])
        self.assertEqual(len(fks), 1)


class TestMergeElevates(unittest.TestCase):
    def test_elevates_with_column_folds_into_elevation_feed(self):
        authored = [_authored("elevates", "part", "part",
                              from_column="part_id", to_column="part_id",
                              perspective="quality", weight=1, concept="defects")]
        fks, elevs = ex._merge_authored_into_sources(authored, [], [])
        self.assertEqual(fks, [])
        self.assertEqual(len(elevs), 1)
        self.assertEqual(elevs[0]["table_name"], "part")
        self.assertEqual(elevs[0]["column_name"], "part_id")
        self.assertEqual(elevs[0]["perspective"], "quality")
        self.assertEqual(elevs[0]["weight"], 1)
        self.assertEqual(elevs[0]["concept"], "defects")

    def test_column_less_elevates_skipped(self):
        authored = [_authored("elevates", "part", "part", perspective="quality")]
        _, elevs = ex._merge_authored_into_sources(authored, [], [])
        self.assertEqual(elevs, [])

    def test_elevates_deduped_against_existing(self):
        existing = [{
            "table_name": "part", "column_name": "part_id",
            "perspective": "quality", "weight": 1, "concept": "defects",
        }]
        authored = [_authored("elevates", "part", "part",
                              from_column="part_id", to_column="part_id",
                              perspective="quality", weight=0, concept="defects")]
        _, elevs = ex._merge_authored_into_sources(authored, [], existing)
        self.assertEqual(len(elevs), 1)


class TestMergeHasColumn(unittest.TestCase):
    def test_has_column_is_noop(self):
        authored = [_authored("has_column", "part", "part", to_column="part_id")]
        fks, elevs = ex._merge_authored_into_sources(authored, [], [])
        self.assertEqual(fks, [])
        self.assertEqual(elevs, [])


class TestFetchAuthoredEdges(unittest.TestCase):
    def test_missing_table_returns_empty(self):
        conn = sqlite3.connect(":memory:")
        try:
            self.assertEqual(ex._fetch_authored_edges(conn), [])
        finally:
            conn.close()

    def test_reads_rows_in_order(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                f"""CREATE TABLE {ex.AUTHORED_EDGES_TABLE} (
                    authored_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    edge_type TEXT, from_table TEXT, from_column TEXT DEFAULT '',
                    to_table TEXT, to_column TEXT DEFAULT '',
                    perspective TEXT DEFAULT 'system', weight INTEGER, concept TEXT)"""
            )
            conn.execute(
                f"INSERT INTO {ex.AUTHORED_EDGES_TABLE} "
                "(edge_type, from_table, from_column, to_table, to_column, perspective) "
                "VALUES ('references','orders','part_ref','part','part_id','system')"
            )
            conn.commit()
            rows = ex._fetch_authored_edges(conn)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["edge_type"], "references")
            self.assertEqual(rows[0]["from_column"], "part_ref")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
