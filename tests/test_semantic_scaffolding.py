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
    def _integrity(self):
        return {"semantic_elevations_skipped": []}

    def test_noncanonical_column_is_skipped_not_emitted(self):
        rows = [{
            "table_name": "stg_manufacturing_flat", "column_name": "ncm_cost",
            "perspective": "Payables", "weight": 3, "concept": "Cost",
            "relationship": "USES_DEFINITION",
        }]
        integ = self._integrity()
        edges = ex._build_elevates_edges(rows, node_index=set(), integrity=integ)
        self.assertEqual(edges, [])
        self.assertEqual(len(integ["semantic_elevations_skipped"]), 1)

    def test_canonical_column_emits_self_loop_edge(self):
        rows = [{
            "table_name": "PAYABLE", "column_name": "INVOICE_ID",
            "perspective": "Payables", "weight": 3, "concept": "Invoice",
            "relationship": "USES_DEFINITION", "field_component": 1,
        }]
        integ = self._integrity()
        node_index = {("PAYABLE", "INVOICE_ID")}
        edges = ex._build_elevates_edges(rows, node_index=node_index, integrity=integ)
        self.assertEqual(len(edges), 1)
        e = edges[0]
        self.assertEqual(e["_from"], e["_to"])
        self.assertEqual(e["_from"], ex.column_id("PAYABLE", "INVOICE_ID"))
        self.assertEqual(e["edge_family"], ex.FAMILY_SEMANTIC)
        self.assertEqual(e["edge_type"], ex.EDGE_PREDICATE_ELEVATES)
        self.assertEqual(e["perspective"], "Payables")
        self.assertEqual(e["weight"], 3)
        self.assertEqual(e["concept"], "Invoice")
        self.assertEqual(e["field_component"], 1)
        self.assertEqual(integ["semantic_elevations_skipped"], [])

    def test_field_component_defaults_to_one_when_absent(self):
        """A row without an explicit component_index still gets field_component 1
        (the primary definition), never None."""
        rows = [{
            "table_name": "PAYABLE", "column_name": "INVOICE_ID",
            "perspective": "Payables", "weight": 3, "concept": "Invoice",
            "relationship": "USES_DEFINITION",
        }]
        integ = self._integrity()
        node_index = {("PAYABLE", "INVOICE_ID")}
        edges = ex._build_elevates_edges(rows, node_index=node_index, integrity=integ)
        self.assertEqual(edges[0]["field_component"], 1)

    def test_multiple_definitions_carry_their_component_index(self):
        """A field with two definitions emits two elevates edges, each carrying
        its own field_component (1 and 2)."""
        rows = [
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "weight": 3, "concept": "InvoiceA",
             "relationship": "r", "field_component": 1},
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Receivables", "weight": 2, "concept": "InvoiceB",
             "relationship": "r", "field_component": 2},
        ]
        integ = self._integrity()
        node_index = {("PAYABLE", "INVOICE_ID")}
        edges = ex._build_elevates_edges(rows, node_index=node_index, integrity=integ)
        self.assertEqual(len(edges), 2)
        by_concept = {e["concept"]: e["field_component"] for e in edges}
        self.assertEqual(by_concept, {"InvoiceA": 1, "InvoiceB": 2})

    def test_uniqifier_increments_for_colliding_prefix(self):
        rows = [
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "weight": 3, "concept": "A",
             "relationship": "r"},
            {"table_name": "PAYABLE", "column_name": "INVOICE_ID",
             "perspective": "Payables", "weight": 2, "concept": "B",
             "relationship": "r"},
        ]
        integ = self._integrity()
        node_index = {("PAYABLE", "INVOICE_ID")}
        edges = ex._build_elevates_edges(rows, node_index=node_index, integrity=integ)
        uids = sorted(e["unique_id"] for e in edges)
        self.assertEqual(len(uids), 2)
        self.assertEqual(len({u.rsplit("_", 1)[0] for u in uids}), 1)  # same prefix
        self.assertTrue(uids[0].endswith("_001") and uids[1].endswith("_002"))


if __name__ == "__main__":
    unittest.main()
