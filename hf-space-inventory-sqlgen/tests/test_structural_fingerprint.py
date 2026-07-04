"""Tests for living-manifest structural fingerprints (Task #242).

A snippet's structural fingerprint is the SET of base tables it touches — style
(CTE names, join order, windowing/bucketing) is deliberately ignored. These
tests lock in:

  * the shared extractor (raw_base_tables / base_table_set): CTE names excluded,
    lowercased, sorted+deduped, strict parse-fail raises,
  * validate_fingerprint: accepts a full stylistic rewrite over the SAME base
    tables, rejects an added/removed table, fails closed on a parse error, and
    treats a missing approved fingerprint as "serve with a warning",
  * SolderEngine.resolve_by_binding_key fail-closed conditions
    (1 missing key, 2 missing snippet, 4 fingerprint mismatch / parse fail),
  * the backfill migration (every APPROVED snippet fingerprinted; idempotent),
  * the canonical graph wiring (binding nodes + binds_table edges present,
    counts consistent, round-trip stable, coverage still 231/231),
  * the registration flow (extract + assign/reuse key + APPROVED entry;
    parse-fail rejected; idempotent by natural key).

Run: python hf-space-inventory-sqlgen/tests/test_structural_fingerprint.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, REPO_ROOT)

import structural_fingerprint as sfp  # noqa: E402
import register_snippet as rs  # noqa: E402
from solder_engine import SolderEngine  # noqa: E402

MANIFEST_PATH = os.path.join(HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")

_passed = 0
_failed = 0


def check(cond, label):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS: {label}")
    else:
        _failed += 1
        print(f"  FAIL: {label}")


# ---------------------------------------------------------------------------
# 1. Shared extractor
# ---------------------------------------------------------------------------
def test_extractor():
    print("test_extractor")
    sql = "SELECT p.part_id FROM part p JOIN work_order w ON w.part_id = p.part_id"
    check(sfp.base_table_set(sql) == ["part", "work_order"], "base tables sorted+lowercased")

    dup = "SELECT * FROM part UNION SELECT * FROM part"
    check(sfp.base_table_set(dup) == ["part"], "duplicates de-duplicated")

    cte = ("WITH agg AS (SELECT part_id, SUM(qty) q FROM inventory_transaction "
           "GROUP BY part_id) SELECT * FROM agg JOIN part USING (part_id)")
    fp = sfp.base_table_set(cte)
    check("agg" not in fp, "CTE alias excluded from fingerprint")
    check(fp == ["inventory_transaction", "part"], "CTE base tables retained")

    check(sfp.EXTRACTOR_ID == "sqlglot-sqlite-base-tables-v1", "extractor id stable")
    check(sfp.FINGERPRINT_DIALECT == "sqlite", "fingerprint dialect sqlite")

    raised = False
    try:
        sfp.base_table_set("SELECT FROM WHERE (", strict=True)
    except sfp.FingerprintParseError:
        raised = True
    check(raised, "strict parse-fail raises FingerprintParseError")
    check(sfp.base_table_set("SELECT FROM WHERE (", strict=False) == [],
          "non-strict parse-fail degrades to empty")


# ---------------------------------------------------------------------------
# 2. validate_fingerprint — structure not style
# ---------------------------------------------------------------------------
def test_validate_fingerprint():
    print("test_validate_fingerprint")
    approved = ["part", "work_order"]

    # Full stylistic rewrite (renamed CTE, reordered join, windowing) over the
    # SAME base tables must pass.
    rewrite = (
        "WITH ranked AS (SELECT p.part_id, ROW_NUMBER() OVER "
        "(PARTITION BY p.part_id ORDER BY w.close_date) rn "
        "FROM work_order w JOIN part p ON p.part_id = w.part_id) "
        "SELECT * FROM ranked WHERE rn = 1"
    )
    ok, reason = sfp.validate_fingerprint(rewrite, approved)
    check(ok and reason is None, "stylistic rewrite over same base tables accepted")

    # Added table -> reject.
    added = ("SELECT p.part_id FROM part p JOIN work_order w ON w.part_id=p.part_id "
             "JOIN customer_order c ON c.part_id = p.part_id")
    ok2, reason2 = sfp.validate_fingerprint(added, approved)
    check(not ok2 and "customer_order" in reason2, "added base table rejected")

    # Removed table -> reject.
    removed = "SELECT part_id FROM part"
    ok3, reason3 = sfp.validate_fingerprint(removed, approved)
    check(not ok3 and "work_order" in reason3, "removed base table rejected")

    # Parse fail -> reject.
    ok4, reason4 = sfp.validate_fingerprint("SELECT FROM (", approved)
    check(not ok4 and "parse" in reason4.lower(), "parse fail rejected")

    # No approved fingerprint -> accept (caller warns).
    ok5, reason5 = sfp.validate_fingerprint("SELECT part_id FROM part", [])
    check(ok5 and reason5 is None, "empty approved fingerprint serves (no failure)")

    # Case-insensitive match.
    ok6, _ = sfp.validate_fingerprint("SELECT * FROM PART p JOIN Work_Order w ON 1=1",
                                      approved)
    check(ok6, "base-table match is case-insensitive")


# ---------------------------------------------------------------------------
# 3. Engine fail-closed conditions
# ---------------------------------------------------------------------------
def test_engine_fail_closed():
    print("test_engine_fail_closed")
    eng = SolderEngine()

    # Condition 1: missing binding key.
    r1 = eng.resolve_by_binding_key("no_such_key_xyz")
    check(r1.get("fail_closed") and r1.get("fail_condition") == "missing_binding_key",
          "condition 1: missing binding key fails closed")
    check(r1["sql"] == "", "condition 1: no SQL served")

    # A real APPROVED binding serves cleanly (fingerprint passes).
    bindings = eng.load_approved_bindings()
    check(len(bindings) > 0, "approved bindings load")
    sample = bindings[0]
    r_ok = eng.resolve_by_binding_key(sample.binding_key)
    check(not r_ok.get("fail_closed") and r_ok["sql"], "real binding serves SQL")
    check(sample.base_tables == sfp.base_table_set(sample.sql_text),
          "loaded binding base_tables match its snippet fingerprint")

    # Condition 3: when a perspective is requested and no snippet matches it,
    # resolution must NOT fall back to a different perspective (fail closed).
    real_persp = sample.perspective
    bogus_persp = "NoSuchPerspective_zzz"
    concept = sample.concept_anchor
    same = eng.find_binding_for_concept(concept, real_persp)
    check(same is not None and same.perspective.lower() == real_persp.lower(),
          "condition 3: exact perspective resolves")
    cross = eng.find_binding_for_concept(concept, bogus_persp)
    check(cross is None,
          "condition 3: unmatched perspective does NOT fall back (find_binding)")
    cross2 = eng.resolve_concept_snippet(bogus_persp, concept)
    check(cross2 is None,
          "condition 3: unmatched perspective does NOT fall back (resolve_concept)")
    # No perspective requested -> perspective-agnostic resolution still works.
    agnostic = eng.find_binding_for_concept(concept, None)
    check(agnostic is not None, "no-perspective resolution still serves")

    # Condition 3 must be SURFACED by assemble_query, not silently skipped.
    fc = eng.assemble_query(
        intent=None, perspective=bogus_persp, concepts=[concept],
        base_table="stg_manufacturing_flat", target_dialect="sqlite",
    )
    check(fc.get("fail_closed") is True, "assemble_query flags fail_closed")
    check(concept in fc.get("fail_closed_concepts", []),
          "assemble_query names the fail-closed concept")
    check(fc.get("fail_closed_condition") == "no_perspective_compatible_snippet",
          "assemble_query reports the condition-3 code")
    check(any("FAIL-CLOSED" in line for line in fc.get("report", [])),
          "assemble_query report surfaces FAIL-CLOSED line")
    check(any(concept in w for w in fc.get("warnings", [])),
          "assemble_query warning names the concept")

    # A genuinely unknown concept is NOT a perspective fail-closed (plain skip).
    unknown = eng.assemble_query(
        intent=None, perspective=real_persp, concepts=["ZZZ_NOT_A_CONCEPT"],
        base_table="stg_manufacturing_flat", target_dialect="sqlite",
    )
    check(not unknown.get("fail_closed"), "unknown concept is not a perspective fail-closed")

    # assemble_query must also fail closed on condition (4): parse failure and
    # structural-fingerprint drift — never serving unvalidated SQL. We inject a
    # crafted binding so the check does not depend on manifest contents.
    from solder_engine import SolderBinding

    def _fake_binding(sql_text, base_tables):
        return SolderBinding(
            binding_key="FAKE_KEY", perspective="Operations",
            concept_anchor="FAKE_CONCEPT", logic_type="AGGREGATE",
            sql_snippet_path="fake.sql", sme_justification="test",
            validation_status="APPROVED", sql_text=sql_text,
            base_tables=base_tables,
        )

    orig_resolve = eng.resolve_concept_snippet
    try:
        eng.resolve_concept_snippet = lambda p, c, i=None: _fake_binding("SELECT FROM (", [])
        parse_fc = eng.assemble_query(
            intent=None, perspective="Operations", concepts=["FAKE_CONCEPT"],
            base_table="stg_manufacturing_flat", target_dialect="sqlite",
        )
        check(parse_fc.get("fail_closed") is True, "assemble_query fails closed on parse error")
        check(parse_fc.get("fail_closed_condition") == "fingerprint_validation_failed",
              "parse error reported as condition (4)")
        check(parse_fc.get("sql", "").strip().startswith("--"),
              "parse-error assembly serves no real SQL")

        eng.resolve_concept_snippet = lambda p, c, i=None: _fake_binding(
            "SELECT p.part_id FROM part p JOIN work_order w ON w.part_id=p.part_id",
            ["part"],  # approved fingerprint omits work_order -> drift
        )
        fp_fc = eng.assemble_query(
            intent=None, perspective="Operations", concepts=["FAKE_CONCEPT"],
            base_table="stg_manufacturing_flat", target_dialect="sqlite",
        )
        check(fp_fc.get("fail_closed") is True, "assemble_query fails closed on fingerprint drift")
        check(fp_fc.get("fail_closed_condition") == "fingerprint_validation_failed",
              "fingerprint drift reported as condition (4)")
        check(fp_fc.get("sql", "").strip().startswith("--"),
              "fingerprint-drift assembly serves no real SQL")
    finally:
        eng.resolve_concept_snippet = orig_resolve


# ---------------------------------------------------------------------------
# 3b. Dispatcher must not fall back to assembly when the binding-key path
#     fails closed (no silent cross-path SQL).
# ---------------------------------------------------------------------------
def test_dispatcher_fail_closed_no_fallback():
    print("test_dispatcher_fail_closed_no_fallback")
    from production_dispatcher import ProductionDispatcher

    disp = ProductionDispatcher(use_live_api=False)
    disp.intent_binding_map = {"FAKE_INTENT": "FAKE_KEY"}
    disp.extract_via_mock = lambda q: {
        "intent": "FAKE_INTENT", "concepts": ["X"], "perspective": "Operations",
        "confidence": "high",
    }
    disp.solder.resolve_by_binding_key = lambda k, target_dialect="sqlite": {
        "sql": "", "report": ["boom"], "warnings": ["boom"],
        "fail_closed": True, "fail_condition": "fingerprint_validation_failed",
    }
    called = {"assemble": False}
    orig_assemble = disp.solder.assemble_query
    disp.solder.assemble_query = lambda **kw: (called.__setitem__("assemble", True) or orig_assemble(**kw))

    res = disp.dispatch("some question", force_mock=True)
    check(res.fail_closed is True, "dispatcher surfaces binding-key fail-closed")
    check(res.fail_closed_condition == "fingerprint_validation_failed",
          "dispatcher carries the fail-closed condition code")
    check(not res.assembled_sql, "dispatcher serves no SQL when binding-key fails closed")
    check(called["assemble"] is False, "dispatcher does NOT fall back to assemble_query")


# ---------------------------------------------------------------------------
# 4. Backfill migration — coverage + idempotency
# ---------------------------------------------------------------------------
def test_backfill_idempotent():
    print("test_backfill_idempotent")
    from migrations import backfill_structural_fingerprints as bf

    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    approved = [k for k, v in manifest["approved_snippets"].items()
                if v.get("validation_status") == "APPROVED"]

    # Every APPROVED entry already carries a fingerprint (backfill ran).
    missing = [k for k in approved
               if not (manifest["approved_snippets"][k].get("structural_fingerprint")
                       or {}).get("base_tables")]
    check(not missing, f"every APPROVED entry fingerprinted ({len(approved)} entries)")

    # A dry-run backfill reports no additions and no drift (idempotent).
    summary = bf.backfill(MANIFEST_PATH, dry_run=True)
    check(not summary["added"], "dry-run backfill adds nothing")
    check(not summary["drift"], "dry-run backfill reports no drift")
    check(not summary["parse_error"], "dry-run backfill reports no parse errors")
    check(len(summary["unchanged"]) == len(approved),
          "dry-run backfill: all approved entries unchanged")


# ---------------------------------------------------------------------------
# 5. Canonical graph wiring
# ---------------------------------------------------------------------------
def test_graph_wiring():
    print("test_graph_wiring")
    json_path = os.path.join(REPO_ROOT, "replit_integrations", "graph_metadata.json")
    with open(json_path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)

    nodes = doc["nodes"]
    edges = doc["edges"]
    binding_nodes = [n for n in nodes if n["node_type"] == "binding"]
    binds_edges = [e for e in edges if e["edge_type"] == "binds_table"]
    column_nodes = [n for n in nodes if n["node_type"] == "column"]

    check(len(binding_nodes) > 0, "binding nodes present in graph")
    check(len(binds_edges) > 0, "binds_table edges present in graph")
    check(doc["counts"]["nodes_by_type"]["binding"] == len(binding_nodes),
          "binding count matches nodes_by_type")

    # Binding nodes are NOT column nodes -> field-description coverage unaffected.
    check(len(column_nodes) == 231, "column node count still 231 (coverage intact)")

    # Every binding node carries binding_key + manifest family; slots 4-5 none.
    ok_shape = all(
        n["node_family"] == "manifest" and n.get("binding_key")
        and n["predicate"] == "none" and n["unique_id"] == "none"
        for n in binding_nodes
    )
    check(ok_shape, "binding nodes: manifest family, binding_key, node markers")

    # Every binds_table edge: _from a binding node, _to a table node, manifest fam.
    binding_ids = {n["_id"] for n in binding_nodes}
    table_ids = {n["_id"] for n in nodes if n["node_type"] == "table"}
    ok_edges = all(
        e["_from"] in binding_ids and e["_to"] in table_ids
        and e["edge_family"] == "manifest"
        for e in binds_edges
    )
    check(ok_edges, "binds_table edges: binding -> table, manifest family")

    # One binds_table edge per (binding, base table) in the fingerprint.
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    expected_edges = 0
    table_names_lower = {n["table_name"].lower() for n in nodes if n["node_type"] == "table"}
    for k, v in manifest["approved_snippets"].items():
        if v.get("validation_status") != "APPROVED":
            continue
        bt = (v.get("structural_fingerprint") or {}).get("base_tables") or []
        expected_edges += sum(1 for t in bt if t.lower() in table_names_lower)
    check(len(binds_edges) == expected_edges,
          f"binds_table edge count == in-graph fingerprint tables ({expected_edges})")


# ---------------------------------------------------------------------------
# 6. Registration flow
# ---------------------------------------------------------------------------
def test_registration_flow():
    print("test_registration_flow")
    # Work on a temp copy of the manifest so we never mutate the committed one.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_manifest = os.path.join(tmp, "reviewer_manifest.json")
        tmp_snips = os.path.join(tmp, "sql_snippets")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
            base = json.load(fh)
        with open(tmp_manifest, "w", encoding="utf-8") as fh:
            json.dump(base, fh, indent=2)

        # Register a brand-new snippet.
        r = rs.register_snippet(
            sql_text="SELECT part_id, reorder_point FROM part",
            perspective="Operations", concept_anchor="TESTMETRIC_UNIQUE",
            sme_justification="unit test", signed_off_by="tester",
            manifest_path=tmp_manifest, snippets_dir=tmp_snips,
        )
        check(r["base_tables"] == ["part"], "registered snippet fingerprint extracted")
        check(not r["reused_existing"], "new concept mints a fresh key")
        check(os.path.exists(os.path.join(tmp_snips, f"{r['binding_key']}.sql")),
              "snippet file written")

        with open(tmp_manifest, "r", encoding="utf-8") as fh:
            after = json.load(fh)
        entry = after["approved_snippets"][r["binding_key"]]
        check(entry["validation_status"] == "APPROVED", "entry APPROVED")
        check(entry["structural_fingerprint"]["base_tables"] == ["part"],
              "entry carries fingerprint")
        check(entry["approved_by"] == "tester", "audit trail recorded")

        # Idempotent re-register (same perspective+concept) reuses the key.
        r2 = rs.register_snippet(
            sql_text="SELECT part_id, reorder_point, on_hand_qty FROM part",
            perspective="Operations", concept_anchor="TESTMETRIC_UNIQUE",
            signed_off_by="tester",
            manifest_path=tmp_manifest, snippets_dir=tmp_snips,
        )
        check(r2["binding_key"] == r["binding_key"], "re-register reuses key")
        check(r2["reused_existing"], "re-register flagged as reused")
        with open(tmp_manifest, "r", encoding="utf-8") as fh:
            after2 = json.load(fh)
        n_test = sum(1 for v in after2["approved_snippets"].values()
                     if v.get("concept_anchor") == "TESTMETRIC_UNIQUE")
        check(n_test == 1, "no duplicate entry created on re-register")

        # Parse-fail rejected (fail closed, no write).
        raised = False
        try:
            rs.register_snippet(
                sql_text="SELECT FROM WHERE (", perspective="Operations",
                concept_anchor="BAD", manifest_path=tmp_manifest,
                snippets_dir=tmp_snips,
            )
        except rs.RegistrationError:
            raised = True
        check(raised, "parse-fail registration rejected (fail closed)")


if __name__ == "__main__":
    test_extractor()
    test_validate_fingerprint()
    test_engine_fail_closed()
    test_dispatcher_fail_closed_no_fallback()
    test_backfill_idempotent()
    test_graph_wiring()
    test_registration_flow()
    print(f"\n{_passed} passed, {_failed} failed")
    sys.exit(1 if _failed else 0)
