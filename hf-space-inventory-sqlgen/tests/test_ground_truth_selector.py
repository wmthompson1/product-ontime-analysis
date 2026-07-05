"""Tests for the reusable 6-slot ground-truth selector element."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ground_truth_selector import (  # noqa: E402
    POINT_IN_TIME_MARK,
    TIME_PHASED_MARK,
    UNKNOWN_MARK,
    _abbrev3,
    load_selector_entries,
    selector_choices,
    slot_label,
)

APP_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST = os.path.join(APP_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")
DB_PATH = os.path.join(APP_DIR, "app_schema", "manufacturing.db")


def test_abbrev3_rule():
    assert _abbrev3("inventory_management") == "INV"
    assert _abbrev3("DIRECT") == "DIR"
    assert _abbrev3("ab") == "AB_"
    assert _abbrev3("") == "___"


def test_all_labels_same_length():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    assert entries, "manifest should yield approved entries"
    lengths = {len(slot_label(e)) for e in entries}
    assert len(lengths) == 1, f"labels must be same-length, got {lengths}"


def test_label_has_six_slots():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    for e in entries:
        assert slot_label(e).count(":") == 5, "exactly 6 colon-delimited slots"


def test_time_slot_marks():
    base = {
        "category": "x", "concept_anchor": "A", "perspective": "P",
        "logic_type": "DIRECT", "base_tables": ["part"],
    }
    assert slot_label({**base, "time_phased": True}).endswith(TIME_PHASED_MARK)
    assert slot_label({**base, "time_phased": False}).endswith(POINT_IN_TIME_MARK)
    assert slot_label({**base, "time_phased": None}).endswith(UNKNOWN_MARK)


def test_choices_preserve_binding_keys():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    choices = selector_choices(entries)
    assert len(choices) == len(entries)
    assert {bk for _, bk in choices} == {e["binding_key"] for e in entries}


def test_seeded_mrp_views_have_known_time_phase():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    seeded = [e for e in entries if e["time_phased"] is not None]
    assert len(seeded) >= 7, "the 7 seeded MRP views should resolve time_phased"


def test_entries_sorted_by_perspective_then_concept():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    keys = [(e["perspective"], e["concept_anchor"]) for e in entries]
    assert keys == sorted(keys)


def test_slot0_is_perspective_abbrev():
    entries = load_selector_entries(MANIFEST, DB_PATH)
    for e in entries:
        assert slot_label(e).split(":")[0] == _abbrev3(e["perspective"])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All ground_truth_selector tests passed.")
