"""Format-lock tests for the semantic ``elevates`` scaffolding in the exporter.

These guard the locked semantic-edge grammar and the node-guard behaviour that
keeps the scaffolding at zero content until an SME elevates a real ERP column.
They do NOT touch ArangoDB or assert on live row counts.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "replit_integrations"))

import export_graph_metadata as ex  # noqa: E402


class SemanticEdgeGrammar(unittest.TestCase):
    def test_key_has_six_locked_slots(self):
        key = ex.semantic_edge_key("PAYABLE", "INVOICE_ID", "Payables", "PAY_ELE_PAY_INV_001")
        slots = key.split(ex.KEY_DELIMITER)
        self.assertEqual(len(slots), 6)
        self.assertEqual(slots[0], "PAYABLE")
        self.assertEqual(slots[1], "INVOICE_ID")
        self.assertEqual(slots[2], ex.FAMILY_SEMANTIC)
        self.assertEqual(slots[3], "Payables")
        self.assertEqual(slots[4], ex.EDGE_PREDICATE_ELEVATES)
        self.assertEqual(slots[5], "PAY_ELE_PAY_INV_001")

    def test_id_is_key_in_edge_collection(self):
        eid = ex.semantic_edge_id("PAYABLE", "INVOICE_ID", "Payables", "PAY_ELE_PAY_INV_001")
        key = ex.semantic_edge_key("PAYABLE", "INVOICE_ID", "Payables", "PAY_ELE_PAY_INV_001")
        self.assertEqual(eid, f"{ex.EDGE_COLLECTION}/{key}")

    def test_perspective_system_is_reserved(self):
        with self.assertRaises(ValueError):
            ex.semantic_edge_key("PAYABLE", "INVOICE_ID", ex.PERSPECTIVE_SYSTEM, "X")

    def test_delimiter_in_component_is_rejected(self):
        with self.assertRaises(ValueError):
            ex.semantic_edge_key("PAYABLE", "INVOICE_ID", "Pay:ables", "X")


class ElevatesBuilder(unittest.TestCase):
    """M2: ``elevates`` runs column -> concept node (no self-loop, no concept
    string on the edge); the uid is concept-aware and derived (not counted)."""

    def _integrity(self):
        return {"semantic_elevations_skipped": []}

    def test_column_not_a_node_is_skipped_not_emitted(self):
        rows = [{
            "table_name": "stg_manufacturing_flat", "column_name": "ncm_cost",
            "perspective": "Payables", "priority_weight": 3, "concept": "Cost",
            "relationship": "USES_DEFINITION",
        }]
        integ = self._integrity()
        edges = ex._build_elevates_edges(
            rows, node_index=set(), concept_index={"Cost"}, integrity=integ)
        self.assertEqual(edges, [])
        self.assertEqual(len(integ["semantic_elevations_skipped"]), 1)
        self.assertIn(
            "column not a canonical node", integ["semantic_elevations_skipped"][0])

    def test_concept_without_node_is_skipped_not_emitted(self):
        """M2 guards BOTH endpoints: a column that IS a node but whose concept has
        no concept node is skipped + recorded, never emitted as a dangling edge."""
        rows = [{
            "table_name": "PAYABLE", "column_name": "INVOICE_ID",
            "perspective": "Payables", "priority_weight": 3, "concept": "Invoice",
            "relationship": "USES_DEFINITION", "field_component": 1,
        }]
        integ = self._integrity()
        edges = ex._build_elevates_edges(
            rows, node_index={("PAYABLE", "INVOICE_ID")},
            concept_index=set(), integrity=integ)
        self.assertEqual(edges, [])
        self.assertEqual(len(integ["semantic_elevations_skipped"]), 1)
        self.assertIn(
            "concept not a canonical node", integ["semantic_elevations_skipped"][0])

    def test_canonical_column_emits_column_to_concept_edge(self):
        rows = [{
            "table_name": "PAYABLE", "column_name": "INVOICE_ID",
            "perspective": "Payables", "priority_weight": 3, "concept": "Invoice",
            "relationship": "USES_DEFINITION", "field_component": 1,
        }]
        integ = self._integrity()
        node_index = {("PAYABLE", "INVOICE_ID")}
        concept_index = {"Invoice"}
        edges = ex._build_elevates_edges(
            rows, node_index=node_index, concept_index=concept_index, integrity=integ)
        self.assertEqual(len(edges), 1)
        e = edges[0]
        # M2: column -> concept node, no longer a self-loop on the column
        self.assertNotEqual(e["_from"], e["_to"])
        self.assertEqual(e["_from"], ex.column_id("PAYABLE", "INVOICE_ID"))
        self.assertEqual(e["_to"], ex.concept_id("Invoice"))
        self.assertEqual(e["edge_family"], ex.FAMILY_SEMANTIC)
        self.assertEqual(e["edge_type"], ex.EDGE_PREDICATE_ELEVATES)
        self.assertEqual(e["perspective"], "Payables")
        # M2: the concept string is dropped from the edge entirely (lives on _to)
        self.assertNotIn("concept", e)
        # B3: weight is the binary gate normalized from priority_weight; raw kept
        self.assertEqual(e["weight"], 1)
        self.assertEqual(e["priority_weight"], 3)
        self.assertEqual(e["field_component"], 1)
        self.assertEqual(integ["semantic_elevations_skipped"], [])

    def test_weight_is_binary_gate_from_priority_weight(self):
        """B3: weight = 1 iff priority_weight > 0, else 0; priority_weight is kept
        verbatim as non-gating metadata."""
        rows = [
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "priority_weight": 5, "concept": "A",
             "relationship": "r", "field_component": 1},
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "priority_weight": 0, "concept": "B",
             "relationship": "r", "field_component": 1},
        ]
        edges = ex._build_elevates_edges(
            rows, node_index={("PAYABLE", "INVOICE_ID")},
            concept_index={"A", "B"}, integrity=self._integrity())
        by_to = {e["_to"]: e for e in edges}
        self.assertEqual(by_to[ex.concept_id("A")]["weight"], 1)
        self.assertEqual(by_to[ex.concept_id("A")]["priority_weight"], 5)
        self.assertEqual(by_to[ex.concept_id("B")]["weight"], 0)
        self.assertEqual(by_to[ex.concept_id("B")]["priority_weight"], 0)

    def test_field_component_defaults_to_one_when_absent(self):
        """A row without an explicit component_index still gets field_component 1
        (the primary definition), never None."""
        rows = [{
            "table_name": "PAYABLE", "column_name": "INVOICE_ID",
            "perspective": "Payables", "priority_weight": 3, "concept": "Invoice",
            "relationship": "USES_DEFINITION",
        }]
        edges = ex._build_elevates_edges(
            rows, node_index={("PAYABLE", "INVOICE_ID")},
            concept_index={"Invoice"}, integrity=self._integrity())
        self.assertEqual(edges[0]["field_component"], 1)

    def test_multiple_definitions_carry_their_component_index(self):
        """A column elevated to two concepts emits two edges, each pointing at its
        own concept node and carrying its own field_component (1 and 2)."""
        rows = [
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "priority_weight": 3, "concept": "InvoiceA",
             "relationship": "r", "field_component": 1},
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Receivables", "priority_weight": 2, "concept": "InvoiceB",
             "relationship": "r", "field_component": 2},
        ]
        edges = ex._build_elevates_edges(
            rows, node_index={("PAYABLE", "INVOICE_ID")},
            concept_index={"InvoiceA", "InvoiceB"}, integrity=self._integrity())
        self.assertEqual(len(edges), 2)
        by_to = {e["_to"]: e["field_component"] for e in edges}
        self.assertEqual(
            by_to, {ex.concept_id("InvoiceA"): 1, ex.concept_id("InvoiceB"): 2})

    def test_uid_is_concept_aware_and_stable_under_sibling_churn(self):
        """M2 invariant: two concepts on one column+perspective get distinct uids
        that share the readable prefix (differ only in the trailing content hash);
        removing a sibling does NOT renumber the survivor — uids are derived from
        the natural key, not counted."""
        rows = [
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "priority_weight": 3, "concept": "A",
             "relationship": "r", "field_component": 1},
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "priority_weight": 2, "concept": "B",
             "relationship": "r", "field_component": 1},
        ]
        node_index = {("PAYABLE", "INVOICE_ID")}
        both = ex._build_elevates_edges(
            rows, node_index=node_index, concept_index={"A", "B"},
            integrity=self._integrity())
        uids = {e["_to"]: e["unique_id"] for e in both}
        # distinct full uids, one shared readable prefix
        self.assertEqual(len(set(uids.values())), 2)
        self.assertEqual(len({u.rsplit("_", 1)[0] for u in uids.values()}), 1)
        # remove sibling B -> A keeps the EXACT same uid (no renumber)
        only_a = ex._build_elevates_edges(
            [rows[0]], node_index=node_index, concept_index={"A"},
            integrity=self._integrity())
        self.assertEqual(only_a[0]["unique_id"], uids[ex.concept_id("A")])


if __name__ == "__main__":
    unittest.main()
