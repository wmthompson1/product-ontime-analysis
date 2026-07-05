"""Tests for the Ontop OBDA mapping selector (mirrors the Query Topology selector)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ontop_ontology_selector import (  # noqa: E402
    DEFAULT_POC_DIR,
    load_ontop_entries,
    parse_obda,
    parse_ttl_annotations,
    selector_choices,
    slot_label,
    _abbrev3,
    _target_terms,
)


def test_parse_obda_shop_floor_routing():
    path = os.path.join(DEFAULT_POC_DIR, "mapping", "shop_floor_routing.obda")
    mappings = parse_obda(path)
    ids = [m["mapping_id"] for m in mappings]
    assert ids == ["map-routing-operation", "map-routing-workorder"]
    for m in mappings:
        assert m["target"] and m["source"]
        assert m["source"].upper().startswith("SELECT")


def test_target_terms_classifies_facts_and_links():
    op = next(
        m for m in parse_obda(
            os.path.join(DEFAULT_POC_DIR, "mapping", "shop_floor_routing.obda")
        )
        if m["mapping_id"] == "map-routing-operation"
    )
    cls, facts, links = _target_terms(op["target"])
    assert cls == "Operation"
    assert set(facts) == {"sequenceNumber", "operationStatus", "runHours", "setupHours"}
    assert links == ["partOfWorkOrder"]


def test_fact_only_mapping_gets_parenthesized_subject():
    cls, facts, links = _target_terms(
        ":delivery/{receipt_id} :onTimeFinance {v}^^xsd:integer ."
    )
    assert cls == "(delivery)"
    assert facts == ["onTimeFinance"]
    assert links == []


def test_ttl_annotations_shop_floor_routing():
    path = os.path.join(DEFAULT_POC_DIR, "ontology", "shop_floor_routing.ttl")
    ann = parse_ttl_annotations(path)
    assert ann["ontology_label"] == "Shop Floor Routing Showcase Ontology"
    assert "WorkOrder" in ann["terms"]
    assert ann["terms"]["Operation"]["kind"] == "Class"
    assert ann["terms"]["runHours"]["kind"] == "DatatypeProperty"
    assert ann["terms"]["runHours"]["label"] == "run hours"
    assert ann["terms"]["partOfWorkOrder"]["kind"] == "ObjectProperty"


def test_entries_cover_all_obda_modules():
    entries = load_ontop_entries()
    assert len(entries) >= 15
    modules = {e["module"] for e in entries}
    expected = {
        "capacity_planning", "customer_order_demand", "inventory_transactions",
        "on_time_delivery", "operational_efficiency", "shop_floor_routing",
    }
    assert expected <= modules


def test_all_labels_same_length():
    entries = load_ontop_entries()
    lengths = {len(slot_label(e)) for e in entries}
    assert len(lengths) == 1, f"label widths differ: {lengths}"


def test_labels_have_six_slots_and_module_abbrev():
    for e in load_ontop_entries():
        parts = slot_label(e).split(":")
        assert len(parts) == 6
        assert parts[0] == _abbrev3(e["module"])


def test_entries_sorted_by_module_then_mapping():
    entries = load_ontop_entries()
    keys = [(e["module"], e["mapping_id"]) for e in entries]
    assert keys == sorted(keys)


def test_choices_preserve_entry_keys():
    entries = load_ontop_entries()
    choices = selector_choices(entries)
    assert [k for _, k in choices] == [e["entry_key"] for e in entries]


def test_base_tables_extracted_from_source_sql():
    entries = load_ontop_entries()
    op = next(e for e in entries if e["entry_key"] == "shop_floor_routing/map-routing-operation")
    assert set(op["base_tables"]) == {"operation", "work_order"}


def test_module_choices_one_per_showcase_with_counts():
    from ontop_ontology_selector import module_choices

    entries = load_ontop_entries()
    choices = module_choices(entries)
    modules = sorted({e["module"] for e in entries})
    assert [v for _, v in choices] == modules
    for label, module in choices:
        n = sum(1 for e in entries if e["module"] == module)
        assert label.endswith(f"({n})")
        # concrete, human-readable title — not the raw snake_case module id
        assert "_" not in label


def test_selector_choices_for_module_narrows_and_none_means_all():
    from ontop_ontology_selector import selector_choices_for_module

    entries = load_ontop_entries()
    module = entries[0]["module"]
    narrowed = selector_choices_for_module(entries, module)
    assert narrowed
    assert all(
        next(e for e in entries if e["entry_key"] == k)["module"] == module
        for _, k in narrowed
    )
    assert selector_choices_for_module(entries, None) == selector_choices(entries)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    if failures:
        sys.exit(1)
    print("All ontop_ontology_selector tests passed.")
