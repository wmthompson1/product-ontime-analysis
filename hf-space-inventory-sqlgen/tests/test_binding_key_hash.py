"""Unit tests for the Solder Pattern primary binding key hash scheme.

Key convention:  {src3}_{tgt3}_{NNN}_{perspective_slug}

  src3            — first 3 lowercase alpha chars of the source table
  tgt3            — first 3 lowercase alpha chars of the target table
  NNN             — seq_num zero-padded to at least 3 digits
  perspective_slug — lowercase slug (spaces/punctuation → underscore)

Applies equally to intents, concepts, and field_components — the entity type
is NOT part of the key.

Run:  python hf-space-inventory-sqlgen/tests/test_binding_key_hash.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

from binding_key_utils import make_binding_key, parse_binding_key, _alpha3, _perspective_slug


# ---------------------------------------------------------------------------
# _alpha3 — table name → 3-char prefix
# ---------------------------------------------------------------------------

def test_alpha3_standard_table():
    """Plain table name: first 3 letters, lowercased."""
    assert _alpha3("suppliers") == "sup"
    assert _alpha3("orders") == "ord"
    assert _alpha3("production_quality") == "pro"
    assert _alpha3("quality_incidents") == "qua"
    print("PASS: _alpha3 standard table names")


def test_alpha3_prefixed_with_underscore_or_digit():
    """Leading underscores and digits are skipped; only alpha chars count."""
    assert _alpha3("stg_manufacturing_flat") == "stg"
    assert _alpha3("01_orders") == "ord"
    assert _alpha3("_quality") == "qua"
    print("PASS: _alpha3 skips leading underscores and digits")


def test_alpha3_mixed_case_normalised():
    """Input case does not affect the 3-char prefix — always lowercase output."""
    assert _alpha3("Suppliers") == "sup"
    assert _alpha3("ORDERS") == "ord"
    assert _alpha3("ProductionQuality") == "pro"
    print("PASS: _alpha3 normalises to lowercase")


def test_alpha3_short_name():
    """Table names with fewer than 3 alpha chars return whatever letters exist."""
    assert _alpha3("ab") == "ab"
    assert _alpha3("a") == "a"
    assert _alpha3("io") == "io"
    print("PASS: _alpha3 short names return partial prefix")


def test_alpha3_long_compound_name():
    """Compound names with many underscores: only the leading alpha chars matter."""
    assert _alpha3("stg_mfg_flat_v2") == "stg"
    assert _alpha3("dim_supplier_performance") == "dim"
    print("PASS: _alpha3 compound names use leading alpha block")


# ---------------------------------------------------------------------------
# _perspective_slug — perspective → URL/key-safe slug
# ---------------------------------------------------------------------------

def test_perspective_slug_simple():
    """Single-word perspectives are just lowercased."""
    assert _perspective_slug("Finance") == "finance"
    assert _perspective_slug("Operations") == "operations"
    assert _perspective_slug("QUALITY") == "quality"
    print("PASS: _perspective_slug single-word")


def test_perspective_slug_with_spaces():
    """Spaces are converted to underscores."""
    assert _perspective_slug("Supply Chain") == "supply_chain"
    assert _perspective_slug("Customer Service") == "customer_service"
    assert _perspective_slug("On Time Delivery") == "on_time_delivery"
    print("PASS: _perspective_slug spaces → underscores")


def test_perspective_slug_mixed_punctuation():
    """Hyphens, dots, and other punctuation are treated the same as spaces."""
    assert _perspective_slug("Finance/Ops") == "finance_ops"
    assert _perspective_slug("Cost & Quality") == "cost_quality"
    assert _perspective_slug("Supplier-Performance") == "supplier_performance"
    print("PASS: _perspective_slug punctuation normalised to underscore")


def test_perspective_slug_empty_fallback():
    """An empty or whitespace-only string falls back to 'default'."""
    assert _perspective_slug("") == "default"
    assert _perspective_slug("   ") == "default"
    assert _perspective_slug("---") == "default"
    print("PASS: _perspective_slug empty/blank → 'default'")


# ---------------------------------------------------------------------------
# make_binding_key — full key assembly
# ---------------------------------------------------------------------------

def test_make_binding_key_canonical():
    """Canonical examples from the key convention documentation."""
    assert make_binding_key("suppliers", "orders", 1, "Finance") == "sup_ord_001_finance"
    assert make_binding_key("quality_incidents", "production_quality", 3, "Operations") \
        == "qua_pro_003_operations"
    assert make_binding_key("stg_manufacturing_flat", "stg_orders", 5, "Supply Chain") \
        == "stg_stg_005_supply_chain"
    print("PASS: make_binding_key canonical examples")


def test_make_binding_key_seq_num_zero_padding():
    """seq_num is zero-padded to at least 3 digits."""
    assert make_binding_key("suppliers", "orders", 1,   "Finance").split("_")[2] == "001"
    assert make_binding_key("suppliers", "orders", 10,  "Finance").split("_")[2] == "010"
    assert make_binding_key("suppliers", "orders", 100, "Finance").split("_")[2] == "100"
    assert make_binding_key("suppliers", "orders", 999, "Finance").split("_")[2] == "999"
    print("PASS: make_binding_key seq_num zero-padded")


def test_make_binding_key_seq_num_beyond_999():
    """seq_num > 999 is accepted and rendered without truncation."""
    key = make_binding_key("suppliers", "orders", 1000, "Finance")
    assert "1000" in key
    print("PASS: make_binding_key seq_num > 999 accepted")


def test_make_binding_key_different_seq_nums_are_unique():
    """Two keys that differ only by seq_num must not be equal."""
    k1 = make_binding_key("suppliers", "orders", 1, "Finance")
    k2 = make_binding_key("suppliers", "orders", 2, "Finance")
    assert k1 != k2
    print("PASS: make_binding_key different seq_nums produce distinct keys")


def test_make_binding_key_self_referential():
    """Source and target can be the same table (e.g. parent-child hierarchy)."""
    key = make_binding_key("work_orders", "work_orders", 1, "Operations")
    assert key == "wor_wor_001_operations"
    print("PASS: make_binding_key self-referential (src == tgt)")


def test_make_binding_key_applies_to_intent():
    """Intent use-case: key encodes the two main tables the intent spans."""
    key = make_binding_key("suppliers", "purchase_orders", 1, "Finance")
    assert key.startswith("sup_pur_")
    assert key.endswith("_finance")
    print("PASS: make_binding_key intent use-case")


def test_make_binding_key_applies_to_concept():
    """Concept use-case: key encodes the fact and dimension tables."""
    key = make_binding_key("quality_incidents", "defect_codes", 2, "Quality")
    assert key.startswith("qua_def_")
    assert key.endswith("_quality")
    print("PASS: make_binding_key concept use-case")


def test_make_binding_key_applies_to_field_component():
    """Field component use-case: key encodes source table and lookup table."""
    key = make_binding_key("production_schedule", "work_centers", 1, "Operations")
    assert key.startswith("pro_wor_")
    assert key.endswith("_operations")
    print("PASS: make_binding_key field_component use-case")


def test_make_binding_key_collision_different_sources():
    """Tables sharing the same 3-char prefix must still differ in the full key
    when the target or perspective differs."""
    k1 = make_binding_key("suppliers", "orders", 1, "Finance")
    k2 = make_binding_key("supply_chain", "orders", 1, "Finance")
    assert k1 == k2, (
        "Expected collision on src3='sup' — callers must disambiguate with seq_num. "
        f"k1={k1!r}, k2={k2!r}"
    )
    k3 = make_binding_key("suppliers", "orders", 2, "Finance")
    assert k3 != k1, "seq_num=2 must differ from seq_num=1"
    print("PASS: make_binding_key collision documented, seq_num resolves it")


def test_make_binding_key_invalid_seq_num_zero():
    """seq_num=0 is not a valid positive integer and must raise ValueError."""
    try:
        make_binding_key("suppliers", "orders", 0, "Finance")
        assert False, "Expected ValueError for seq_num=0"
    except ValueError:
        pass
    print("PASS: make_binding_key raises ValueError for seq_num=0")


def test_make_binding_key_invalid_seq_num_negative():
    """Negative seq_num must raise ValueError."""
    try:
        make_binding_key("suppliers", "orders", -1, "Finance")
        assert False, "Expected ValueError for seq_num=-1"
    except ValueError:
        pass
    print("PASS: make_binding_key raises ValueError for negative seq_num")


def test_make_binding_key_invalid_source_no_alpha():
    """Source table with no alpha characters must raise ValueError."""
    try:
        make_binding_key("123", "orders", 1, "Finance")
        assert False, "Expected ValueError for source_table='123'"
    except ValueError:
        pass
    print("PASS: make_binding_key raises ValueError for source_table with no alpha")


def test_make_binding_key_invalid_target_no_alpha():
    """Target table with no alpha characters must raise ValueError."""
    try:
        make_binding_key("suppliers", "456_", 1, "Finance")
        assert False, "Expected ValueError for target_table='456_'"
    except ValueError:
        pass
    print("PASS: make_binding_key raises ValueError for target_table with no alpha")


# ---------------------------------------------------------------------------
# parse_binding_key — round-trip
# ---------------------------------------------------------------------------

def test_parse_binding_key_round_trip():
    """parse_binding_key reconstructs the components used to build the key."""
    key = make_binding_key("suppliers", "orders", 7, "Finance")
    parts = parse_binding_key(key)
    assert parts["src3"] == "sup"
    assert parts["tgt3"] == "ord"
    assert parts["seq_num"] == 7
    assert parts["perspective_slug"] == "finance"
    print("PASS: parse_binding_key round-trip")


def test_parse_binding_key_multi_word_perspective_round_trip():
    """Multi-word perspective slug survives a round-trip."""
    key = make_binding_key("production_schedule", "work_centers", 42, "Supply Chain")
    parts = parse_binding_key(key)
    assert parts["src3"] == "pro"
    assert parts["tgt3"] == "wor"
    assert parts["seq_num"] == 42
    assert parts["perspective_slug"] == "supply_chain"
    print("PASS: parse_binding_key multi-word perspective round-trip")


def test_parse_binding_key_invalid_format():
    """parse_binding_key raises ValueError for strings that don't match the pattern."""
    bad_keys = [
        "finance_ncm_cost_20260208_150000",   # old timestamp-based format
        "suppliers",                            # no separators
        "sup_ord",                              # missing seq and perspective
        "",                                     # empty
    ]
    for bad in bad_keys:
        try:
            parse_binding_key(bad)
            assert False, f"Expected ValueError for key {bad!r}"
        except ValueError:
            pass
    print("PASS: parse_binding_key rejects non-conforming keys")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_alpha3_standard_table,
        test_alpha3_prefixed_with_underscore_or_digit,
        test_alpha3_mixed_case_normalised,
        test_alpha3_short_name,
        test_alpha3_long_compound_name,
        test_perspective_slug_simple,
        test_perspective_slug_with_spaces,
        test_perspective_slug_mixed_punctuation,
        test_perspective_slug_empty_fallback,
        test_make_binding_key_canonical,
        test_make_binding_key_seq_num_zero_padding,
        test_make_binding_key_seq_num_beyond_999,
        test_make_binding_key_different_seq_nums_are_unique,
        test_make_binding_key_self_referential,
        test_make_binding_key_applies_to_intent,
        test_make_binding_key_applies_to_concept,
        test_make_binding_key_applies_to_field_component,
        test_make_binding_key_collision_different_sources,
        test_make_binding_key_invalid_seq_num_zero,
        test_make_binding_key_invalid_seq_num_negative,
        test_make_binding_key_invalid_source_no_alpha,
        test_make_binding_key_invalid_target_no_alpha,
        test_parse_binding_key_round_trip,
        test_parse_binding_key_multi_word_perspective_round_trip,
        test_parse_binding_key_invalid_format,
    ]

    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(
        f"{'PASS' if failed == 0 else 'FAIL'}: "
        f"{len(tests) - failed}/{len(tests)} tests passed"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
