"""Tests for masking_matrix (the column-masking DAG matrix + its hash rule).

Uses temp CSV + SQLite files so no live database or root CSV is touched.

Coverage:
- load_matrix_from_csv() upserts CSV rows into SQLite, keyed on dag_no, and is
  idempotent (reload -> same count; a changed status/field updates in place).
- read_matrix() returns rows in DAG-numeric order (1.2 before 1.10 before 2.0).
- _clean_row normalization: whitespace trimmed, blank masking_mode -> 1,
  non-int masking_mode -> 1, blank/non-int field_length -> 0, negative
  field_length clamped to 0, blank/unknown status -> 'active', no dag_no skipped.
- The CHECK constraint accepts active/static/complete (status coercion keeps the
  load from ever violating it).
- export_matrix_to_csv() round-trips: load -> export -> reload yields equal rows
  (field_length included).
- write_default_csv() recreates the curated default matrix (incl. the row with an
  empty column_name) with its field_length widths.
- ensure_table() self-heals an older table that predates the field_length column
  (idempotent ALTER TABLE ADD COLUMN).
- hash_sha256() (the matrix's hash_sha256(col,length) rule): deterministic,
  truncates to the schema width (length), full digest when length<=0, uppercase
  hex, NULL/empty passthrough, and requires a salt.
- mask_row_value() sizes the hash to the row's stored field_length (the schema
  width), full digest when field_length is 0/missing, NULL passthrough.

Run:
    python hf-space-inventory-sqlgen/tests/test_masking_matrix.py
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
if HF_DIR not in sys.path:
    sys.path.insert(0, HF_DIR)

import masking_matrix as mm  # noqa: E402

SALT = "unit-test-salt"

CSV_HEADER = ",".join(mm.MATRIX_COLUMNS)


def _write_csv(path: str, body_lines: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(CSV_HEADER + "\n")
        for line in body_lines:
            fh.write(line + "\n")


def test_load_upsert_and_idempotent() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        _write_csv(csv_path, [
            '1.1,vendor,id,,,"hash_sha256(id,length)",deterministic_hash,30,1,sql-lab-2,static',
            '1.2,part,pref_vendor,vendor,id,"hash_sha256(pref_vendor,length)",deterministic_hash,30,1,sql-lab-2,active',
        ])
        res = mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["ok"] is True, res
        assert res["loaded"] == 2
        assert mm.count_rows(db_path) == 2

        # Reload unchanged CSV -> still 2 rows (upsert, no duplicate).
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert mm.count_rows(db_path) == 2

        # Change a field + status, reload -> updated in place, still 2 rows.
        _write_csv(csv_path, [
            '1.1,vendor,id,,,"hash_sha256(id,length)",deterministic_hash,40,1,sql-lab-9,complete',
            '1.2,part,pref_vendor,vendor,id,"hash_sha256(pref_vendor,length)",deterministic_hash,30,1,sql-lab-2,active',
        ])
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert mm.count_rows(db_path) == 2
        rows = {r["dag_no"]: r for r in mm.read_matrix(db_path)}
        assert rows["1.1"]["pre_stage_server"] == "sql-lab-9"
        assert rows["1.1"]["status"] == "complete"
        assert rows["1.1"]["field_length"] == 40  # updated in place
    print("PASS: load_matrix_from_csv upserts and is idempotent")


def test_dag_numeric_ordering() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        _write_csv(csv_path, [
            "2.0,t,c,,,rule,deterministic_hash,0,1,srv,active",
            "1.10,t,c,,,rule,deterministic_hash,0,1,srv,active",
            "1.2,t,c,,,rule,deterministic_hash,0,1,srv,active",
            "1.1,t,c,,,rule,deterministic_hash,0,1,srv,active",
        ])
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        order = [r["dag_no"] for r in mm.read_matrix(db_path)]
        assert order == ["1.1", "1.2", "1.10", "2.0"], order
    print("PASS: read_matrix orders rows by DAG number")


def test_row_normalization() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        _write_csv(csv_path, [
            # trailing/leading spaces, padded field_length, blank masking_mode, blank status
            '1.1, vendor , id ,,,"hash_sha256(id,length)",deterministic_hash, 30 ,,sql-lab-2,',
            # non-int field_length + non-int masking_mode, unknown status
            "1.2,part,pref_vendor,vendor,id,rule,deterministic_hash,x,x,srv,bogus",
            # negative field_length -> clamped to 0
            "1.3,t,c,,,rule,deterministic_hash,-5,1,srv,active",
            # no dag_no -> skipped entirely
            ",ghost,col,,,rule,deterministic_hash,1,1,srv,active",
        ])
        res = mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["loaded"] == 3, res  # ghost row skipped
        rows = {r["dag_no"]: r for r in mm.read_matrix(db_path)}
        assert rows["1.1"]["table_name"] == "vendor"   # trimmed
        assert rows["1.1"]["column_name"] == "id"       # trimmed
        assert rows["1.1"]["field_length"] == 30        # padded -> int
        assert rows["1.1"]["masking_mode"] == 1         # blank -> 1
        assert rows["1.1"]["status"] == "active"        # blank -> active
        assert rows["1.2"]["field_length"] == 0         # non-int -> 0
        assert rows["1.2"]["masking_mode"] == 1         # non-int -> 1
        assert rows["1.2"]["status"] == "active"        # unknown -> active
        assert rows["1.3"]["field_length"] == 0         # negative -> 0
    print("PASS: row normalization (trim, field_length, masking_mode, status, skip)")


def test_status_check_accepts_vocabulary() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        _write_csv(csv_path, [
            "1.1,t,c,,,rule,deterministic_hash,0,1,srv,active",
            "1.2,t,c,,,rule,deterministic_hash,0,1,srv,static",
            "1.3,t,c,,,rule,deterministic_hash,0,1,srv,complete",
        ])
        res = mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["ok"] is True and res["loaded"] == 3, res
        statuses = {r["status"] for r in mm.read_matrix(db_path)}
        assert statuses == {"active", "static", "complete"}, statuses
    print("PASS: status CHECK accepts active/static/complete")


def test_export_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        out_path = os.path.join(d, "out.csv")
        _write_csv(csv_path, [
            '1.1,vendor,id,,,"hash_sha256(id,length)",deterministic_hash,30,1,sql-lab-2,static',
            '2.0,user_def_fields,,,,"hash_sha256(id,length)",deterministic_hash,0,1,sql-lab-2,active',
        ])
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        before = mm.read_matrix(db_path)
        written = mm.export_matrix_to_csv(db_path=db_path, csv_path=out_path)
        assert written == 2, written

        # Reload the exported CSV into a fresh DB -> identical rows (field_length too).
        db2 = os.path.join(d, "m2.db")
        mm.load_matrix_from_csv(csv_path=out_path, db_path=db2)
        after = mm.read_matrix(db2)
        assert before == after, (before, after)
    print("PASS: export_matrix_to_csv round-trips back to identical rows")


def test_write_default_csv_seed() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "certificate_for_receiving", "masking_matrix.csv")
        db_path = os.path.join(d, "m.db")
        created = mm.write_default_csv(csv_path)
        assert created == len(mm.DEFAULT_MATRIX) == 4, created
        assert os.path.exists(csv_path)
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        rows = {r["dag_no"]: r for r in mm.read_matrix(db_path)}
        assert set(rows) == {"1.1", "1.2", "1.3", "2.0"}, set(rows)
        # the user_def_fields row carries an empty column_name + unbounded width
        assert rows["2.0"]["table_name"] == "user_def_fields"
        assert rows["2.0"]["column_name"] == ""
        assert rows["2.0"]["field_length"] == 0
        # the id-style rows carry their schema width
        assert rows["1.1"]["field_length"] == 30
    print("PASS: write_default_csv recreates the curated default matrix")


def test_ensure_table_migrates_old_schema() -> None:
    """A table created before field_length existed is back-filled by ensure_table."""
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "old.db")
        conn = sqlite3.connect(db_path)
        # Old DDL: no field_length column.
        conn.execute(
            """
            CREATE TABLE masking_matrix (
                dag_no           TEXT    NOT NULL PRIMARY KEY,
                table_name       TEXT    NOT NULL,
                column_name      TEXT    NOT NULL DEFAULT '',
                parent_table     TEXT    NOT NULL DEFAULT '',
                parent_column    TEXT    NOT NULL DEFAULT '',
                masking_rule     TEXT,
                masking_type     TEXT,
                masking_mode     INTEGER NOT NULL DEFAULT 1,
                pre_stage_server TEXT,
                status           TEXT    NOT NULL DEFAULT 'active'
            )
            """
        )
        conn.execute(
            "INSERT INTO masking_matrix (dag_no, table_name) VALUES ('9.9', 'legacy')"
        )
        conn.commit()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(masking_matrix)")}
        assert "field_length" not in cols  # precondition

        # ensure_table adds the column; re-running is a no-op.
        mm.ensure_table(conn)
        mm.ensure_table(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(masking_matrix)")}
        assert "field_length" in cols
        val = conn.execute(
            "SELECT field_length FROM masking_matrix WHERE dag_no='9.9'"
        ).fetchone()[0]
        assert val == 0  # existing row back-filled to the default
        conn.close()

        # And a normal CSV load now works against the migrated DB.
        csv_path = os.path.join(d, "m.csv")
        _write_csv(csv_path, [
            '1.1,vendor,id,,,"hash_sha256(id,length)",deterministic_hash,30,1,srv,static',
        ])
        res = mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert res["ok"] is True, res
        rows = {r["dag_no"]: r for r in mm.read_matrix(db_path)}
        assert rows["1.1"]["field_length"] == 30
    print("PASS: ensure_table self-heals a pre-field_length table")


def test_hash_deterministic_and_width() -> None:
    a = mm.hash_sha256("VEND-001", length=8, salt=SALT)
    b = mm.hash_sha256("VEND-001", length=8, salt=SALT)
    assert a == b, (a, b)                       # deterministic
    assert len(a) == 8, a                        # truncated to schema width
    expected = hashlib.sha256(f"VEND-001{SALT}".encode()).hexdigest().upper()
    assert a == expected[:8], (a, expected[:8])  # prefix of full digest
    assert a == a.upper(), a                      # uppercase hex

    full = mm.hash_sha256("VEND-001", length=0, salt=SALT)
    assert full == expected and len(full) == 64, full  # length<=0 -> full digest

    # Different inputs -> different masked values (collision-free at width 16).
    other = mm.hash_sha256("VEND-002", length=16, salt=SALT)
    assert other != mm.hash_sha256("VEND-001", length=16, salt=SALT)
    print("PASS: hash_sha256 is deterministic, width-sized, uppercase hex")


def test_hash_passthrough_and_requires_salt() -> None:
    assert mm.hash_sha256(None, length=8, salt=SALT) is None
    assert mm.hash_sha256("", length=8, salt=SALT) == ""

    # Salt comes from the env var when not passed explicitly.
    prev = os.environ.get(mm.SALT_ENV_VAR)
    try:
        os.environ.pop(mm.SALT_ENV_VAR, None)
        raised = False
        try:
            mm.hash_sha256("VEND-001", length=8)
        except RuntimeError:
            raised = True
        assert raised, "expected RuntimeError when no salt is available"

        os.environ[mm.SALT_ENV_VAR] = SALT
        from_env = mm.hash_sha256("VEND-001", length=8)
        assert from_env == mm.hash_sha256("VEND-001", length=8, salt=SALT)
    finally:
        if prev is None:
            os.environ.pop(mm.SALT_ENV_VAR, None)
        else:
            os.environ[mm.SALT_ENV_VAR] = prev
    print("PASS: hash_sha256 passes through NULL/empty and requires a salt")


def test_to_int_handles_floats_and_junk() -> None:
    assert mm._to_int("30", 0) == 30
    assert mm._to_int("30.0", 0) == 30      # grid hands back floats
    assert mm._to_int(" 12 ", 0) == 12      # padded
    assert mm._to_int("", 7) == 7           # blank -> default
    assert mm._to_int(None, 7) == 7         # None -> default
    assert mm._to_int("x", 1) == 1          # junk -> default
    assert mm._to_int(40.0, 0) == 40        # already a float
    print("PASS: _to_int handles '30.0' / blanks / junk")


def test_replace_matrix_full_replace_and_csv_mirror() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        # Seed two rows the normal way.
        _write_csv(csv_path, [
            "1.1,vendor,id,,,rule,deterministic_hash,30,1,srv,active",
            "1.2,part,pref_vendor,vendor,id,rule,deterministic_hash,30,1,srv,active",
        ])
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)
        assert mm.count_rows(db_path) == 2

        # Replace with a different set (a grid edit): drop 1.2, change 1.1, add 3.0.
        # field_length comes in as a float (30.0) like the Dataframe would send it.
        new_rows = [
            {"dag_no": "1.1", "table_name": "vendor", "column_name": "id",
             "parent_table": "", "parent_column": "", "masking_rule": "rule",
             "masking_type": "deterministic_hash", "field_length": 40.0,
             "masking_mode": 1, "pre_stage_server": "sql-lab-9", "status": "complete"},
            {"dag_no": "3.0", "table_name": "ops", "column_name": "code",
             "parent_table": "", "parent_column": "", "masking_rule": "rule",
             "masking_type": "deterministic_hash", "field_length": "",
             "masking_mode": 1, "pre_stage_server": "srv", "status": "active"},
            # a blank row (no dag_no) is silently dropped
            {"dag_no": "", "table_name": "ghost"},
        ]
        res = mm.replace_matrix(new_rows, db_path=db_path, csv_path=csv_path)
        assert res["ok"] is True, res
        assert res["saved"] == 2, res          # ghost dropped
        assert res["csv_written"] == 2, res

        rows = {r["dag_no"]: r for r in mm.read_matrix(db_path)}
        assert set(rows) == {"1.1", "3.0"}, set(rows)   # 1.2 gone (full replace)
        assert rows["1.1"]["field_length"] == 40         # 40.0 -> 40
        assert rows["1.1"]["status"] == "complete"
        assert rows["3.0"]["field_length"] == 0          # blank -> 0

        # The CSV was mirrored: reloading it into a fresh DB matches.
        db2 = os.path.join(d, "m2.db")
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db2)
        assert {r["dag_no"] for r in mm.read_matrix(db2)} == {"1.1", "3.0"}
    print("PASS: replace_matrix full-replaces SQLite and mirrors the CSV")


def test_replace_matrix_guards_empty_and_duplicate() -> None:
    with tempfile.TemporaryDirectory() as d:
        csv_path = os.path.join(d, "m.csv")
        db_path = os.path.join(d, "m.db")
        _write_csv(csv_path, [
            "1.1,vendor,id,,,rule,deterministic_hash,30,1,srv,active",
        ])
        mm.load_matrix_from_csv(csv_path=csv_path, db_path=db_path)

        # All-empty input is refused (matrix not wiped).
        res = mm.replace_matrix([{"dag_no": ""}], db_path=db_path, csv_path=csv_path)
        assert res["ok"] is False and "empty" in res["error"], res
        assert mm.count_rows(db_path) == 1, "existing matrix must survive a refused save"

        # Duplicate primary key is rejected.
        dup = [
            {"dag_no": "1.1", "table_name": "a", "column_name": "x",
             "masking_type": "deterministic_hash", "field_length": 1,
             "masking_mode": 1, "status": "active"},
            {"dag_no": "1.1", "table_name": "b", "column_name": "y",
             "masking_type": "deterministic_hash", "field_length": 1,
             "masking_mode": 1, "status": "active"},
        ]
        res = mm.replace_matrix(dup, db_path=db_path, csv_path=csv_path)
        assert res["ok"] is False and "duplicate" in res["error"], res
        assert mm.count_rows(db_path) == 1
    print("PASS: replace_matrix refuses empty input and duplicate dag_no")


def test_mask_row_value_uses_field_length() -> None:
    expected = hashlib.sha256(f"VEND-001{SALT}".encode()).hexdigest().upper()

    # A row's field_length sizes the masked value to the schema width.
    masked = mm.mask_row_value({"field_length": 8}, "VEND-001", salt=SALT)
    assert masked == expected[:8] and len(masked) == 8, masked

    # field_length 0 -> unbounded -> full digest.
    full = mm.mask_row_value({"field_length": 0}, "VEND-001", salt=SALT)
    assert full == expected and len(full) == 64, full

    # Missing field_length is treated as 0 (full digest).
    missing = mm.mask_row_value({}, "VEND-001", salt=SALT)
    assert missing == expected, missing

    # NULL passes through unchanged.
    assert mm.mask_row_value({"field_length": 8}, None, salt=SALT) is None
    print("PASS: mask_row_value sizes the hash to the row's field_length")


def main() -> int:
    tests = [
        test_load_upsert_and_idempotent,
        test_dag_numeric_ordering,
        test_row_normalization,
        test_status_check_accepts_vocabulary,
        test_export_roundtrip,
        test_write_default_csv_seed,
        test_ensure_table_migrates_old_schema,
        test_to_int_handles_floats_and_junk,
        test_replace_matrix_full_replace_and_csv_mirror,
        test_replace_matrix_guards_empty_and_duplicate,
        test_hash_deterministic_and_width,
        test_hash_passthrough_and_requires_salt,
        test_mask_row_value_uses_field_length,
    ]
    passed = 0
    for t in tests:
        t()
        passed += 1
    print(f"\nPASS: {passed}/{len(tests)} masking_matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
