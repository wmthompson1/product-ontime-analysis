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

Run directly:
    python hf-space-inventory-sqlgen/tests/test_temporal_contract_validation.py
"""

from __future__ import annotations

import glob
import os
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


def main() -> int:
    tests = [
        test_no_placeholders_passes,
        test_real_parameterized_snippet_passes,
        test_unrecognized_placeholder_fails_closed,
        test_reused_token_in_invalid_context_fails_closed,
        test_is_not_null_arm_is_not_the_approved_guard,
        test_owl_complement_zero_weight_rule_present,
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
