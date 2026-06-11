"""Tests for masking_type (the masking-type reference lookup, CSV <-> SQLite).

Uses temp CSV + SQLite files so no live database or root CSV is touched.

Coverage:
- load_types_from_csv() upserts CSV rows into SQLite, keyed on masking_type, and
  is idempotent (reload -> same count; a changed mode/status updates in place).
- read_types() returns rows ordered by masking_mode then masking_type.
- _clean_row normalization: whitespace trimmed, blank/non-int masking_mode -> 0,
  negative mode clamped to 0, blank/unknown status -> 'active', no masking_type
  skipped.
- The CHECK constraint accepts only active/inactive (status coercion keeps the
  load from ever violating it).
- export_types_to_csv() round-trips: load -> export -> reload yields equal rows.
- replace_types() full-replaces SQLite and mirrors the CSV; refuses an all-empty
  input and rejects a duplicate masking_type (the primary key).
- write_default_csv() recreates the curated default lookup (3 rows).

Run:
    python hf-space-inventory-sqlgen/tests/test_masking_type.py
"""

from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
if HF_DIR not in sys.path:
    sys.path.insert(0, HF_DIR)

import masking_type as mt  # noqa: E402

CSV_HEADER = ",".join(mt.TYPE_COLUMNS)


def _write_csv(path: str, body_lines: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(CSV_HEADER + "\n")
        for line in body_lines:
            fh.write(line + "\n")


def test_load_upsert_and_idempotent() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, [
            "deterministic_hash,1,active",
            "change to null,2,active",
        ])
        res = mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["ok"] is True and res["loaded"] == 2, res
        assert mt.count_rows(db_path) == 2

        # Reload unchanged -> still 2 (upsert, no duplicate).
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        assert mt.count_rows(db_path) == 2

        # Change mode + status, reload -> updated in place.
        _write_csv(csv_path, [
            "deterministic_hash,9,inactive",
            "change to null,2,active",
        ])
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        rows = {r["masking_type"]: r for r in mt.read_types(db_path)}
        assert mt.count_rows(db_path) == 2
        assert rows["deterministic_hash"]["masking_mode"] == 9
        assert rows["deterministic_hash"]["status"] == "inactive"
    print("PASS: load_types_from_csv upserts and is idempotent")


def test_ordering_by_mode_then_name() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, [
            "obfuscate binary text,3,active",
            "change to null,2,active",
            "deterministic_hash,1,active",
        ])
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        order = [r["masking_type"] for r in mt.read_types(db_path)]
        assert order == ["deterministic_hash", "change to null", "obfuscate binary text"], order
    print("PASS: read_types orders by masking_mode then masking_type")


def test_row_normalization() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, [
            " deterministic_hash , 1 , Active ",   # trimmed, status lowercased
            "blank_mode,,active",                    # blank mode -> 0
            "junk_mode,x,active",                    # non-int mode -> 0
            "neg_mode,-4,active",                    # negative -> 0
            "bad_status,5,bogus",                    # unknown status -> active
            ",2,active",                              # no masking_type -> skipped
        ])
        res = mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["loaded"] == 5, res  # blank-name row skipped
        rows = {r["masking_type"]: r for r in mt.read_types(db_path)}
        assert rows["deterministic_hash"]["masking_mode"] == 1
        assert rows["deterministic_hash"]["status"] == "active"   # lowercased
        assert rows["blank_mode"]["masking_mode"] == 0
        assert rows["junk_mode"]["masking_mode"] == 0
        assert rows["neg_mode"]["masking_mode"] == 0              # clamped
        assert rows["bad_status"]["status"] == "active"           # unknown -> active
    print("PASS: row normalization (trim, mode, status, skip)")


def test_status_check_only_active_inactive() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, [
            "a,1,active",
            "b,2,inactive",
        ])
        res = mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["ok"] is True and res["loaded"] == 2, res
        statuses = {r["status"] for r in mt.read_types(db_path)}
        assert statuses == {"active", "inactive"}, statuses
    print("PASS: status CHECK accepts active/inactive")


def test_export_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        out_path = os.path.join(d, "out.csv")
        _write_csv(csv_path, [
            "deterministic_hash,1,active",
            "change to null,2,inactive",
        ])
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        before = mt.read_types(db_path)
        written = mt.export_types_to_csv(db_path=db_path, csv_path=out_path)
        assert written == 2, written

        db2 = os.path.join(d, "t2.db")
        mt.load_types_from_csv(csv_path=out_path, db_path=db2)
        after = mt.read_types(db2)
        assert before == after, (before, after)
    print("PASS: export_types_to_csv round-trips back to identical rows")


def test_replace_types_full_replace_and_csv_mirror() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, [
            "deterministic_hash,1,active",
            "change to null,2,active",
        ])
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        assert mt.count_rows(db_path) == 2

        # Grid edit: drop "change to null", change deterministic_hash, add a new one.
        # masking_mode arrives as a float (like the Dataframe sends it).
        new_rows = [
            {"masking_type": "deterministic_hash", "masking_mode": 1.0, "status": "active"},
            {"masking_type": "obfuscate binary text", "masking_mode": 3.0, "status": "active"},
            {"masking_type": "", "masking_mode": 9, "status": "active"},  # dropped
        ]
        res = mt.replace_types(new_rows, db_path=db_path, csv_path=csv_path)
        assert res["ok"] is True and res["saved"] == 2, res
        assert res["csv_written"] == 2, res

        rows = {r["masking_type"]: r for r in mt.read_types(db_path)}
        assert set(rows) == {"deterministic_hash", "obfuscate binary text"}, set(rows)
        assert rows["obfuscate binary text"]["masking_mode"] == 3   # 3.0 -> 3

        # CSV mirrored: reload into a fresh DB matches.
        db2 = os.path.join(d, "t2.db")
        mt.load_types_from_csv(csv_path=csv_path, db_path=db2)
        assert {r["masking_type"] for r in mt.read_types(db2)} == set(rows)
    print("PASS: replace_types full-replaces SQLite and mirrors the CSV")


def test_replace_types_guards_empty_and_duplicate() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "t.csv")
        db_path = os.path.join(d, "t.db")
        _write_csv(csv_path, ["deterministic_hash,1,active"])
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)

        # All-empty input is refused (lookup not wiped).
        res = mt.replace_types([{"masking_type": ""}], db_path=db_path, csv_path=csv_path)
        assert res["ok"] is False and "empty" in res["error"], res
        assert mt.count_rows(db_path) == 1

        # Duplicate primary key rejected.
        dup = [
            {"masking_type": "x", "masking_mode": 1, "status": "active"},
            {"masking_type": "x", "masking_mode": 2, "status": "inactive"},
        ]
        res = mt.replace_types(dup, db_path=db_path, csv_path=csv_path)
        assert res["ok"] is False and "duplicate" in res["error"], res
        assert mt.count_rows(db_path) == 1
    print("PASS: replace_types refuses empty input and duplicate masking_type")


def test_write_default_csv_seed() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "masking_type.csv")
        db_path = os.path.join(d, "t.db")
        created = mt.write_default_csv(csv_path)
        assert created == len(mt.DEFAULT_TYPES) == 3, created
        assert os.path.exists(csv_path)
        mt.load_types_from_csv(csv_path=csv_path, db_path=db_path)
        rows = {r["masking_type"]: r for r in mt.read_types(db_path)}
        assert set(rows) == {"deterministic_hash", "change to null", "obfuscate binary text"}
        assert rows["deterministic_hash"]["masking_mode"] == 1
        assert rows["obfuscate binary text"]["masking_mode"] == 3
    print("PASS: write_default_csv recreates the curated default lookup")


def main() -> int:
    tests = [
        test_load_upsert_and_idempotent,
        test_ordering_by_mode_then_name,
        test_row_normalization,
        test_status_check_only_active_inactive,
        test_export_roundtrip,
        test_replace_types_full_replace_and_csv_mirror,
        test_replace_types_guards_empty_and_duplicate,
        test_write_default_csv_seed,
    ]
    passed = 0
    for t in tests:
        t()
        passed += 1
    print(f"\nPASS: {passed}/{len(tests)} masking_type tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
