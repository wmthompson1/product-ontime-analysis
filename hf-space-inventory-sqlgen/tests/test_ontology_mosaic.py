"""Tests for the Ontology Mosaic — cascading selector + semantic ontology reader.

Covers:
  * category normalization (near-duplicate raw labels merge, display-only)
  * cascade filtering: category -> anchor -> query
  * single-match auto-resolution (Selection.auto_resolved)
  * explicit binding_key wins when still valid; invalid picks drop out
  * flat-selector fallback signal when no entry carries a category
  * the extension seam: a second CascadeFilter plugs in without rewiring
  * semantic ontology reader: concept node + resolves_to lineage from
    temp sql_graph_* tables, metric duck-typing, graceful degradation

Pure metadata — nothing here touches the real app DB or the manifest.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ground_truth_selector import (  # noqa: E402
    CascadeFilter,
    SelectorCascade,
    anchor_label,
    category_filter,
    category_label,
    has_categories,
    normalize_category,
    selector_choices,
    slot_label,
)
from semantic_ontology import (  # noqa: E402
    get_semantic_ontology,
    render_semantic_ontology_markdown,
)


def _entry(bk, anchor, category, tables=None, perspective="Inventory_Transactions",
           logic="DIRECT", time_phased=None):
    return {
        "binding_key": bk,
        "concept_anchor": anchor,
        "perspective": perspective,
        "category": category,
        "logic_type": logic,
        "base_tables": tables or [],
        "file_path": f"app_schema/ground_truth/sql_snippets/{bk}.sql",
        "sme_justification": "test",
        "time_phased": time_phased,
    }


ENTRIES = [
    _entry("q_safety", "SAFETYSTOCK", "inventory_management", ["part", "work_order"]),
    _entry("q_onhand", "ONHANDQUANTITY", "inventory_management", ["part"]),
    _entry("q_defect_a", "DEFECTSEVERITYQUALITY", "Quality", ["ncm"], perspective="Quality"),
    _entry("q_defect_b", "DEFECTSEVERITYQUALITY", "quality_control", ["ncm", "part"],
           perspective="Manufacturing"),
    _entry("q_score", "SUPPLIERSCORECARD", "supplier_performance", ["suppliers"],
           perspective="Payables"),
]


class TestCategoryNormalization(unittest.TestCase):
    def test_near_duplicates_merge(self):
        self.assertEqual(normalize_category("Quality"), "quality_control")
        self.assertEqual(normalize_category("quality_control"), "quality_control")

    def test_plain_labels_normalize(self):
        self.assertEqual(normalize_category("inventory_management"), "inventory_management")
        self.assertEqual(normalize_category("Inventory Management"), "inventory_management")

    def test_empty_stays_empty(self):
        self.assertEqual(normalize_category(""), "")
        self.assertEqual(normalize_category(None), "")

    def test_display_labels(self):
        self.assertEqual(category_label("quality_control"), "Quality Control")
        self.assertEqual(category_label("inventory_management"), "Inventory Management")
        self.assertEqual(category_label(""), "(uncategorized)")


class TestCascade(unittest.TestCase):
    def setUp(self):
        self.cascade = SelectorCascade(ENTRIES)

    def test_category_choices_merge_near_duplicates(self):
        choices = self.cascade.filter_choices("category")
        keys = [v for _, v in choices]
        self.assertIn("quality_control", keys)
        # 'Quality' and 'quality_control' folded into ONE choice
        self.assertEqual(keys.count("quality_control"), 1)
        self.assertEqual(
            set(keys),
            {"inventory_management", "quality_control", "supplier_performance"},
        )

    def test_anchor_filtering_by_category(self):
        anchors = self.cascade.anchor_choices({"category": "inventory_management"})
        values = [v for _, v in anchors]
        self.assertEqual(values, ["ONHANDQUANTITY", "SAFETYSTOCK"])

    def test_merged_category_pools_both_raw_labels(self):
        queries = self.cascade.query_choices(
            {"category": "quality_control"}, "DEFECTSEVERITYQUALITY"
        )
        self.assertEqual({bk for _, bk in queries}, {"q_defect_a", "q_defect_b"})

    def test_anchor_label_style(self):
        pool = self.cascade.narrow({"category": "inventory_management"})
        self.assertEqual(anchor_label("SAFETYSTOCK", pool), "SAFETYSTOCK  [part, work_order]")

    def test_single_match_auto_resolves(self):
        sel = self.cascade.resolve({"category": "inventory_management"}, "SAFETYSTOCK")
        self.assertEqual(sel.binding_key, "q_safety")
        self.assertTrue(sel.auto_resolved)

    def test_multi_match_needs_explicit_pick(self):
        sel = self.cascade.resolve({"category": "quality_control"}, "DEFECTSEVERITYQUALITY")
        self.assertIsNone(sel.binding_key)
        self.assertFalse(sel.auto_resolved)

    def test_explicit_pick_wins_when_valid(self):
        sel = self.cascade.resolve(
            {"category": "quality_control"}, "DEFECTSEVERITYQUALITY", "q_defect_b"
        )
        self.assertEqual(sel.binding_key, "q_defect_b")
        self.assertFalse(sel.auto_resolved)

    def test_stale_pick_from_other_category_is_dropped(self):
        sel = self.cascade.resolve(
            {"category": "inventory_management"}, "ONHANDQUANTITY", "q_defect_a"
        )
        # invalid explicit pick falls back to the single-match auto-resolution
        self.assertEqual(sel.binding_key, "q_onhand")
        self.assertTrue(sel.auto_resolved)

    def test_query_labels_keep_six_slot_scheme(self):
        queries = self.cascade.query_choices({"category": "inventory_management"}, "SAFETYSTOCK")
        label = queries[0][0]
        self.assertEqual(label, slot_label(ENTRIES[0]))
        self.assertEqual(label.count(":"), 5)

    def test_no_filter_narrow_returns_all(self):
        self.assertEqual(len(self.cascade.narrow()), len(ENTRIES))

    def test_unknown_filter_raises(self):
        with self.assertRaises(KeyError):
            self.cascade.filter_choices("nope")


class TestFlatFallback(unittest.TestCase):
    def test_has_categories_false_when_manifest_lacks_them(self):
        flat = [_entry("q1", "A", ""), _entry("q2", "B", "  ")]
        self.assertFalse(has_categories(flat))
        # flat selector still serves all entries
        self.assertEqual(len(selector_choices(flat)), 2)

    def test_has_categories_true_with_any_category(self):
        self.assertTrue(has_categories(ENTRIES))


class TestExtensionSeam(unittest.TestCase):
    """A second filter plugs in via default_filters()-style composition —
    no changes to choice/resolve consumers required."""

    def test_second_filter_composes(self):
        perspective_filter = CascadeFilter(
            name="perspective",
            choices=lambda es: sorted(
                {(e["perspective"], e["perspective"]) for e in es}
            ),
            apply=lambda es, v: [e for e in es if v is None or e["perspective"] == v],
        )
        cascade = SelectorCascade(
            ENTRIES, filters=[category_filter(), perspective_filter]
        )
        # second filter's choices are narrowed by the first filter's pick
        persp = cascade.filter_choices(
            "perspective", {"category": "quality_control"}
        )
        self.assertEqual(
            {v for _, v in persp}, {"Quality", "Manufacturing"}
        )
        sel = cascade.resolve(
            {"category": "quality_control", "perspective": "Manufacturing"},
            "DEFECTSEVERITYQUALITY",
        )
        self.assertEqual(sel.binding_key, "q_defect_b")
        self.assertTrue(sel.auto_resolved)


class TestSemanticOntology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(cls.db_path)
        conn.executescript(
            """
            CREATE TABLE sql_graph_nodes (
                _key TEXT, _id TEXT, node_type TEXT, concept_name TEXT,
                description TEXT, domain TEXT, perspective TEXT,
                computation_template TEXT, table_name TEXT, column_name TEXT
            );
            CREATE TABLE sql_graph_edges (
                _from TEXT, _to TEXT, edge_type TEXT, variable_name TEXT,
                weight INTEGER, field_component INTEGER
            );
            """
        )
        conn.executemany(
            "INSERT INTO sql_graph_nodes VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    "SafetyStock:entity:semantic:canonical:none:none",
                    "gn/SafetyStock:entity:semantic:canonical:none:none",
                    "concept", "SafetyStock", "Buffer stock", "operations",
                    "canonical", "", None, None,
                ),
                (
                    "OEEStrategic:entity:semantic:canonical:none:none",
                    "gn/OEEStrategic:entity:semantic:canonical:none:none",
                    "concept", "OEEStrategic", "OEE for investment", "finance",
                    "canonical", "SUM({a}) / SUM({b})", None, None,
                ),
                (
                    "part:safety_stock:structural:system:none:none",
                    "gn/part:safety_stock:structural:system:none:none",
                    "column", None, "Safety stock level", None,
                    None, None, "part", "safety_stock",
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO sql_graph_edges VALUES (?,?,?,?,?,?)",
            [
                (
                    "gn/part:safety_stock:structural:system:none:none",
                    "gn/SafetyStock:entity:semantic:canonical:none:none",
                    "resolves_to", "", 1, 1,
                ),
                (
                    "gn/operation:act_run_hrs:structural:system:none:none",
                    "gn/OEEStrategic:entity:semantic:canonical:none:none",
                    "resolves_to", "a", 1, 1,
                ),
                (
                    "gn/operation:est_run_hrs:structural:system:none:none",
                    "gn/OEEStrategic:entity:semantic:canonical:none:none",
                    "resolves_to", "b", 1, 2,
                ),
            ],
        )
        conn.commit()
        conn.close()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.db_path)

    def test_anchor_matches_case_insensitively(self):
        onto = get_semantic_ontology(self.db_path, "SAFETYSTOCK")
        self.assertIsNotNone(onto)
        self.assertEqual(onto["concept_name"], "SafetyStock")
        self.assertFalse(onto["is_metric"])

    def test_lineage_with_column_description(self):
        onto = get_semantic_ontology(self.db_path, "SAFETYSTOCK")
        self.assertEqual(len(onto["lineage"]), 1)
        b = onto["lineage"][0]
        self.assertEqual((b["table"], b["column"]), ("part", "safety_stock"))
        self.assertEqual(b["column_description"], "Safety stock level")

    def test_metric_duck_typing_and_variables(self):
        onto = get_semantic_ontology(self.db_path, "OEESTRATEGIC")
        self.assertTrue(onto["is_metric"])
        self.assertEqual(onto["computation_template"], "SUM({a}) / SUM({b})")
        self.assertEqual(
            [b["variable"] for b in onto["lineage"]], ["a", "b"]
        )

    def test_missing_concept_returns_none(self):
        self.assertIsNone(get_semantic_ontology(self.db_path, "NOSUCHCONCEPT"))

    def test_missing_db_degrades(self):
        self.assertIsNone(get_semantic_ontology("/nonexistent/x.db", "SAFETYSTOCK"))

    def test_render_graceful_message_for_absent_concept(self):
        md = render_semantic_ontology_markdown(None, "NOSUCHCONCEPT")
        self.assertIn("no semantic-layer presence", md)

    def test_render_metric_markdown(self):
        onto = get_semantic_ontology(self.db_path, "OEESTRATEGIC")
        md = render_semantic_ontology_markdown(onto, "OEESTRATEGIC")
        self.assertIn("Computation template", md)
        self.assertIn("SUM({a}) / SUM({b})", md)
        self.assertIn("`resolves_to` lineage", md)
        self.assertIn("`operation`", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
