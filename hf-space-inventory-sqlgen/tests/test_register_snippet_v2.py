"""Registration must write graph-aware (v2) fingerprints.

The runtime only enforces join drift / graph recognition for bindings whose
fingerprint is join-aware (``extractor == EXTRACTOR_ID_V2``). If registration
ever reverts to a v1 (base-tables-only) fingerprint, every newly registered
snippet would silently bypass join validation — defeating the hard cutover.
These tests lock the write side to v2.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import register_snippet as rs  # noqa: E402
import structural_fingerprint as sfp  # noqa: E402


class RegisterSnippetV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manifest_path = os.path.join(self.tmp.name, "reviewer_manifest.json")
        self.snippets_dir = os.path.join(self.tmp.name, "snippets")

    def tearDown(self):
        self.tmp.cleanup()

    def _register(self, sql, concept):
        return rs.register_snippet(
            sql_text=sql,
            perspective="Test",
            concept_anchor=concept,
            signed_off_by="unittest",
            manifest_path=self.manifest_path,
            snippets_dir=self.snippets_dir,
            write=True,
        )

    def _fingerprint(self, binding_key):
        with open(self.manifest_path) as fh:
            manifest = json.load(fh)
        return manifest["approved_snippets"][binding_key]["structural_fingerprint"]

    def test_joined_snippet_is_v2_with_join_edges(self):
        sql = (
            "SELECT po.po_id, r.receipt_id\n"
            "FROM purchase_order po\n"
            "JOIN receiving r ON po.po_id = r.po_id"
        )
        res = self._register(sql, "PO_RECEIPT")
        fp = self._fingerprint(res["binding_key"])
        self.assertEqual(fp["extractor"], sfp.EXTRACTOR_ID_V2)
        self.assertIn("join_edges", fp)
        self.assertIn("unresolved_joins", fp)
        self.assertEqual(len(fp["join_edges"]), 1)
        edge = fp["join_edges"][0]
        self.assertEqual(edge["join_type"], "INNER")
        # canonical: endpoints sorted, so purchase_order precedes receiving
        self.assertEqual(edge["table_a"], "purchase_order")
        self.assertEqual(edge["table_b"], "receiving")

    def test_no_join_snippet_is_v2_with_empty_join_edges(self):
        sql = "SELECT part_id FROM part"
        res = self._register(sql, "PART_ONLY")
        fp = self._fingerprint(res["binding_key"])
        self.assertEqual(fp["extractor"], sfp.EXTRACTOR_ID_V2)
        self.assertEqual(fp["join_edges"], [])

    def test_registered_fingerprint_survives_validate_join_edges(self):
        """A freshly registered snippet's own SQL must pass drift validation
        against the join edges just written (no false fail-closed)."""
        sql = (
            "SELECT po.po_id, r.receipt_id\n"
            "FROM purchase_order po\n"
            "JOIN receiving r ON po.po_id = r.po_id"
        )
        res = self._register(sql, "PO_RECEIPT2")
        fp = self._fingerprint(res["binding_key"])
        # graph recognition skipped (None) — this asserts drift, not recognition.
        ok, reason, _ = sfp.validate_join_edges(sql, fp["join_edges"], None)
        self.assertTrue(ok, reason)

    def test_unparseable_snippet_fails_closed(self):
        with self.assertRaises(rs.RegistrationError):
            self._register("SELECT FROM WHERE JOIN", "BROKEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
