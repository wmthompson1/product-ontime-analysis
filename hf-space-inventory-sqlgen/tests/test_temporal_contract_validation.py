"""
test_temporal_contract_validation.py
====================================
Tests for SolderEngine.validate_temporal_contract — the passive, fail-closed
check that every tokenized (:named) parameter baked into a served snippet is a
recognized member of its machine-readable Temporal Parameter Contract (the
contract produced by view_ontology_extractor). Nothing is executed and no value
is ever bound; a snippet with an unrecognized placeholder is drift and is never
served.

Tests:
  1. test_no_placeholders_passes
       A snippet with no :named parameters passes trivially.
  2. test_real_parameterized_snippet_passes
       The one approved snippet that carries :named parameters
       (payables_uninvoicedreceipts) — every placeholder sits in a guarded,
       column-bound comparison — passes.
  3. test_unrecognized_placeholder_fails_closed
       A placeholder used outside a classifiable comparison (LIMIT, function
       call) is not in the contract, so validation fails closed.
  4. test_owl_complement_zero_weight_rule_present
       The inventory-transactions ontology carries the owl:complementOf rule
       that formally flags lot_id as a zero-semantic-weight (unelevated) context.
  5. test_zero_weight_fields_have_no_resolves_to_edge
       ENFORCEMENT gate: reads the complementOf-flagged (zero-weight) contexts
       from the ontology and asserts none of them has a resolves_to edge in the
       governed graph (committed graph_metadata.json AND, when present, the
       SQLite sql_graph_edges source of truth). Fails closed if a zero-weight
       field is ever silently elevated.

Run directly:
    python hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py
"""

from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
if HF_DIR not in sys.path:
    sys.path.insert(0, HF_DIR)

import solder_engine as se  # noqa: E402

_ENGINE = se.SolderEngine()

TTL_PATH = os.path.join(
    REPO_ROOT, "poc", "ontop-ontology-poc", "ontology", "inventory_transactions.ttl"
)

# The governed graph, in two forms: the committed serialization (always present)
# and the SQLite source of truth (present when a built DB exists).
GRAPH_METADATA_JSON = os.path.join(
    REPO_ROOT, "replit_integrations", "graph_metadata.json"
)
APP_DB = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

_NODE_COLLECTION = "manufacturing_graph_node"

# The physical `table.column` referenced by a wgt: zero-weight context — captured
# from the machine-readable wgt:physicalColumn annotation, falling back to the
# `(table.column)` prose in the rdfs:comment for older ontology revisions.
_PHYS_COL_ANNOTATION_RE = re.compile(
    r"wgt:physicalColumn\s+\"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\""
)
_PHYS_COL_PROSE_RE = re.compile(
    r"\(([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\)"
)

# A wgt: subject typed as the zero-weight (owl:complementOf) context, with the
# block of predicates that follow it up to the terminating `.`.
_ZERO_WEIGHT_BLOCK_RE = re.compile(
    r"^(wgt:[A-Za-z_][A-Za-z0-9_]*)\s+((?:.|\n)*?)\s*\.\s*$",
    re.MULTILINE,
)


def _column_node_key(table: str, column: str) -> str:
    """The canonical structural column-node key for a physical table.column."""
    return f"{table}:{column}:structural:system:none:none"


def _read_zero_weight_contexts() -> dict:
    """Read the owl:complementOf-flagged (zero-weight) contexts from the ontology.

    Returns {wgt_term: column_node_key}. Fails loudly (empty dict is asserted by
    the caller) if the flag exists but no physical column can be resolved — a
    zero-weight flag with no resolvable field would silently disable the gate.
    """
    ttl = open(TTL_PATH, encoding="utf-8").read()
    contexts: dict = {}
    for block in _ZERO_WEIGHT_BLOCK_RE.finditer(ttl):
        subject, body = block.group(1), block.group(2)
        # Only subjects declared to BE a zero-weight context (not the class /
        # annotation-property declarations themselves).
        if "a wgt:ZeroSemanticWeightContext" not in body:
            continue
        m = _PHYS_COL_ANNOTATION_RE.search(body) or _PHYS_COL_PROSE_RE.search(body)
        assert m, (
            f"zero-weight context {subject} has no resolvable physical column "
            "(neither a wgt:physicalColumn annotation nor a (table.column) hint) "
            "— the enforcement gate cannot verify it and must fail closed"
        )
        contexts[subject] = _column_node_key(m.group(1), m.group(2))
    return contexts


def _resolves_to_from_keys_json() -> set:
    """`_from` node keys of every resolves_to edge in the committed graph JSON."""
    if not os.path.exists(GRAPH_METADATA_JSON):
        return set()
    data = json.load(open(GRAPH_METADATA_JSON, encoding="utf-8"))
    keys = set()
    for edge in data.get("edges", []):
        if edge.get("edge_type") != "resolves_to":
            continue
        frm = edge.get("_from", "")
        keys.add(frm.split("/", 1)[1] if "/" in frm else frm)
    return keys


def _resolves_to_from_keys_sqlite() -> set:
    """`_from` node keys of every resolves_to edge in SQLite (source of truth).

    Returns an empty set when no built DB is present (fresh clone / CI without a
    bootstrapped DB); the committed-JSON check still enforces the invariant.
    """
    if not os.path.exists(APP_DB):
        return set()
    keys = set()
    conn = sqlite3.connect(f"file:{APP_DB}?mode=ro", uri=True)
    try:
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sql_graph_edges'"
        ).fetchone()
        if not has_table:
            return set()
        for (frm,) in conn.execute(
            "SELECT _from FROM sql_graph_edges WHERE edge_type='resolves_to'"
        ):
            keys.add(frm.split("/", 1)[1] if "/" in frm else frm)
    finally:
        conn.close()
    return keys


def test_no_placeholders_passes() -> None:
    ok, reason, warnings = _ENGINE.validate_temporal_contract(
        "SELECT part_id, quantity FROM inventory_transaction", "no_params"
    )
    assert ok, f"expected pass, got: {reason}"
    assert reason == ""
    assert warnings == []
    print("PASS: test_no_placeholders_passes")


def test_real_parameterized_snippet_passes() -> None:
    matches = glob.glob(
        os.path.join(
            HF_DIR,
            "app_schema",
            "ground_truth",
            "sql_snippets",
            "payables_uninvoicedreceipts*.sql",
        )
    )
    assert matches, "parameterized ground-truth snippet not found"
    sql = open(matches[0], encoding="utf-8").read()
    ok, reason, _ = _ENGINE.validate_temporal_contract(
        sql, "payables_uninvoicedreceipts"
    )
    assert ok, (
        "the approved parameterized snippet must satisfy its own Temporal "
        f"Parameter Contract, got fail: {reason}"
    )
    print("PASS: test_real_parameterized_snippet_passes")


def test_unrecognized_placeholder_fails_closed() -> None:
    # Placeholder in LIMIT — not a column-bound, classifiable comparison.
    ok_limit, reason_limit, _ = _ENGINE.validate_temporal_contract(
        "SELECT part_id FROM inventory_transaction LIMIT :n", "bad_limit"
    )
    assert not ok_limit, "placeholder in LIMIT must fail closed"
    assert ":n" in reason_limit, reason_limit

    # Placeholder inside a function call — not a comparison predicate.
    ok_fn, reason_fn, _ = _ENGINE.validate_temporal_contract(
        "SELECT COUNT(:foo) AS c FROM inventory_transaction", "bad_fn"
    )
    assert not ok_fn, "placeholder in a function call must fail closed"
    assert ":foo" in reason_fn, reason_fn
    print("PASS: test_unrecognized_placeholder_fails_closed")


def test_reused_token_in_invalid_context_fails_closed() -> None:
    # :end_date is valid in the guarded predicate but reused in LIMIT — the
    # per-occurrence check must fail closed even though the token is recognized
    # by its valid occurrence.
    sql = (
        "SELECT r.received_date FROM receiving r "
        "WHERE (:end_date IS NULL OR r.received_date <= :end_date) "
        "LIMIT :end_date"
    )
    ok, reason, _ = _ENGINE.validate_temporal_contract(sql, "reuse")
    assert not ok, "a token reused in an invalid context must fail closed"
    assert ":end_date" in reason, reason
    print("PASS: test_reused_token_in_invalid_context_fails_closed")


def test_is_not_null_arm_is_not_the_approved_guard() -> None:
    # Only the positive `:param IS NULL` arm is the SME-approved guard shape.
    # `IS NOT NULL` (or any non-NULL IS form) is NOT the idiom, so a token whose
    # only extra occurrence is `:end_date IS NOT NULL` must fail closed even
    # though it is validly bound in the guarded comparison.
    sql = (
        "SELECT r.received_date FROM receiving r "
        "WHERE (:end_date IS NULL OR r.received_date <= :end_date) "
        "AND :end_date IS NOT NULL"
    )
    ok, reason, _ = _ENGINE.validate_temporal_contract(sql, "is_not_null")
    assert not ok, "an `IS NOT NULL` placeholder arm must fail closed"
    assert ":end_date" in reason, reason
    print("PASS: test_is_not_null_arm_is_not_the_approved_guard")


def test_owl_complement_zero_weight_rule_present() -> None:
    assert os.path.exists(TTL_PATH), f"ontology missing: {TTL_PATH}"
    ttl = open(TTL_PATH, encoding="utf-8").read()
    assert "owl:complementOf" in ttl, "owl:complementOf rule missing from ontology"
    assert "wgt:ZeroSemanticWeightContext" in ttl, "zero-weight context class missing"
    assert "wgt:lot_id" in ttl, "lot_id zero-weight flag missing"
    # The rule must live in the dedicated weight namespace, never on the governed
    # `:` showcase vocabulary (which the drift gate closes against the mapping).
    assert ":ZeroSemanticWeightContext" not in ttl.replace(
        "wgt:ZeroSemanticWeightContext", ""
    ), "zero-weight term must not be minted in the governed `:` namespace"
    print("PASS: test_owl_complement_zero_weight_rule_present")


def test_zero_weight_fields_have_no_resolves_to_edge() -> None:
    """Fail-closed enforcement: a field the ontology declares zero-weight (via the
    owl:complementOf rule) must NEVER carry a resolves_to edge in the governed
    graph. The presence test above only proves the *rule text* exists; this gate
    proves the graph actually obeys it, so a future graph change can't silently
    elevate a zero-weight field."""
    assert os.path.exists(TTL_PATH), f"ontology missing: {TTL_PATH}"

    contexts = _read_zero_weight_contexts()
    assert contexts, (
        "no owl:complementOf zero-weight contexts found in the ontology — the "
        "enforcement gate would be a no-op and must fail closed"
    )

    json_from = _resolves_to_from_keys_json()
    sqlite_from = _resolves_to_from_keys_sqlite()
    assert json_from or sqlite_from, (
        "no resolves_to edges found in either the committed graph_metadata.json "
        "or the SQLite sql_graph_edges table — cannot verify the invariant, so "
        "the gate fails closed"
    )

    violations = []
    for term, node_key in sorted(contexts.items()):
        where = []
        if node_key in json_from:
            where.append("graph_metadata.json")
        if node_key in sqlite_from:
            where.append("sql_graph_edges")
        if where:
            violations.append(
                f"  {term} -> {node_key} is ELEVATED via resolves_to in "
                f"{', '.join(where)}"
            )

    assert not violations, (
        "zero-weight (owl:complementOf-flagged) field(s) gained semantic weight "
        "— a resolves_to edge now elevates a field the ontology declares to carry "
        "ZERO semantic weight:\n" + "\n".join(violations)
    )
    print(
        "PASS: test_zero_weight_fields_have_no_resolves_to_edge "
        f"({len(contexts)} zero-weight field(s) verified against "
        f"{len(json_from)} JSON + {len(sqlite_from)} SQLite resolves_to edge(s))"
    )


def main() -> int:
    tests = [
        test_no_placeholders_passes,
        test_real_parameterized_snippet_passes,
        test_unrecognized_placeholder_fails_closed,
        test_reused_token_in_invalid_context_fails_closed,
        test_is_not_null_arm_is_not_the_approved_guard,
        test_owl_complement_zero_weight_rule_present,
        test_zero_weight_fields_have_no_resolves_to_edge,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}:\n{exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
