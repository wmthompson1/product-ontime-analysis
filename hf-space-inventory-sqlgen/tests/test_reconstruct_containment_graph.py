"""Tests for reconstruct_containment_graph dry-run logic and key conventions.

Two test modes:

Dry-run / key-format tests (always run):
    No ArangoDB connection required.  Exercises _run_dry() and the key helpers
    from arangodb_helpers.manufacturing_graph_version_0_0_1.

Live ArangoDB tests (gated on ARANGO_DB env var):
    Connect to a real ArangoDB instance and verify that reconstruct() correctly
    upserts vertices/edges on the first call, then returns 0 upserts on the
    second call (idempotency).  Throwaway documents are inserted and cleaned up
    so the tests are safe to run against a production database.

Coverage:
- Valid table→column rows produce two vertex ops and one edge op in dry-run output.
- Rows with an unknown edge_predicate are counted in rows_skipped.
- Rows with an unsupported source_node_type or target_node_type are counted in rows_skipped.
- Key format regression guard: table_key and column_key follow the ``type::NAME``
  convention (uppercase, double-colon prefix) so that a future key-convention
  change immediately breaks this test.
- Live: first reconstruct() call writes vertices + edge; second call reports 0 upserts.
- Live: rows with unknown edge_predicate produce rows_skipped > 0 and write nothing to
  ArangoDB (collection count before == collection count after).
- Live: rows with unsupported node types produce rows_skipped > 0 and write nothing to
  ArangoDB (collection count before == collection count after).

Run:
    python hf-space-inventory-sqlgen/tests/test_reconstruct_containment_graph.py
"""

from __future__ import annotations

import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "scripts"))

import reconstruct_containment_graph as sut
from arangodb_helpers.manufacturing_graph_version_0_0_1 import (
    table_key,
    column_key,
    contains_edge_key,
    TABLES_COLLECTION,
    COLUMNS_COLLECTION,
    CONTAINS_EDGE_COLLECTION,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    id_: int = 1,
    src_type: str = "table",
    tgt_type: str = "column",
    src_key: str = "ORDERS",
    tgt_key: str = "ORDER_ID",
    predicate: str = "CONTAINS",
    weight: float = 1.0,
    notes: str = "",
) -> dict:
    return {
        "id": id_,
        "source_node_type": src_type,
        "target_node_type": tgt_type,
        "source_key": src_key,
        "target_key": tgt_key,
        "edge_predicate": predicate,
        "weight": weight,
        "notes": notes,
    }


def _capture_dry_run(rows: list[dict]) -> str:
    """Run _run_dry(rows) and return all stdout as a string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sut._run_dry(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_valid_row_produces_vertex_and_edge_ops():
    """A valid table→column CONTAINS row must announce two vertex ops and one edge op."""
    rows = [_make_row()]
    output = _capture_dry_run(rows)

    assert "would upsert" in output.lower(), (
        f"Expected 'would upsert' in dry-run output. Got:\n{output}"
    )
    assert "vertex" in output.lower(), (
        f"Expected 'vertex' in dry-run output. Got:\n{output}"
    )
    assert "edge" in output.lower(), (
        f"Expected 'edge' in dry-run output. Got:\n{output}"
    )
    assert "2" in output, (
        f"Expected vertex count '2' in dry-run output. Got:\n{output}"
    )
    assert "1" in output, (
        f"Expected edge count '1' in dry-run output. Got:\n{output}"
    )
    print("PASS: valid table→column row produces vertex and edge ops in dry-run output")


def test_unknown_predicate_counted_in_rows_skipped():
    """A row with an unknown edge_predicate must be counted in rows_skipped."""
    rows = [
        _make_row(id_=1, predicate="UNKNOWN_PREDICATE"),
    ]
    output = _capture_dry_run(rows)

    assert "skip" in output.lower(), (
        f"Expected '[DRY-RUN SKIP]' in output for unknown predicate. Got:\n{output}"
    )
    assert "1 rows skipped" in output, (
        f"Expected '1 rows skipped' in summary line. Got:\n{output}"
    )
    print("PASS: unknown edge_predicate counted in rows_skipped")


def test_unsupported_node_type_counted_in_rows_skipped():
    """A row with an unsupported source_node_type must be counted in rows_skipped."""
    rows = [
        _make_row(id_=1, src_type="schema", tgt_type="column", predicate="CONTAINS"),
    ]
    output = _capture_dry_run(rows)

    assert "skip" in output.lower(), (
        f"Expected '[DRY-RUN SKIP]' in output for unsupported node type. Got:\n{output}"
    )
    assert "1 rows skipped" in output, (
        f"Expected '1 rows skipped' in summary line. Got:\n{output}"
    )
    print("PASS: unsupported source_node_type counted in rows_skipped")


def test_unsupported_target_node_type_counted_in_rows_skipped():
    """A row with an unsupported target_node_type must be counted in rows_skipped."""
    rows = [
        _make_row(id_=1, src_type="table", tgt_type="database", predicate="CONTAINS"),
    ]
    output = _capture_dry_run(rows)

    assert "skip" in output.lower(), (
        f"Expected '[DRY-RUN SKIP]' for unsupported target_node_type. Got:\n{output}"
    )
    assert "1 rows skipped" in output, (
        f"Expected '1 rows skipped' in summary line. Got:\n{output}"
    )
    print("PASS: unsupported target_node_type counted in rows_skipped")


def test_mixed_rows_skip_count_is_accurate():
    """A mix of valid and invalid rows produces the correct skipped count."""
    rows = [
        _make_row(id_=1, predicate="CONTAINS"),
        _make_row(id_=2, predicate="BAD_PREDICATE"),
        _make_row(id_=3, src_type="view", tgt_type="column", predicate="CONTAINS"),
        _make_row(id_=4, predicate="CONTAINS", src_key="PRODUCTS", tgt_key="PRODUCT_ID"),
    ]
    output = _capture_dry_run(rows)

    assert "2 rows skipped" in output, (
        f"Expected '2 rows skipped' for 2 invalid rows. Got:\n{output}"
    )
    print("PASS: mixed rows produce correct skipped count in dry-run output")


def test_key_format_table_vertex():
    """table_key must produce 'table::{TABLE_NAME}' (uppercase, double-colon prefix).

    This is a regression guard: if the key convention changes, this test fails
    immediately so the breakage surfaces before production.
    """
    result = table_key("corrective_actions")
    assert result == "table::CORRECTIVE_ACTIONS", (
        f"table_key format regression: expected 'table::CORRECTIVE_ACTIONS', got {result!r}"
    )
    result_mixed = table_key("Corrective_Actions")
    assert result_mixed == "table::CORRECTIVE_ACTIONS", (
        f"table_key must uppercase input. Got {result_mixed!r}"
    )
    print("PASS: table_key produces correct 'table::TABLE_NAME' format")


def test_key_format_column_vertex():
    """column_key must produce 'column::{TABLE_NAME}.{COL_NAME}' (uppercase, dot separator).

    This is a regression guard for the column vertex key convention.
    """
    result = column_key("corrective_actions", "capa_id")
    assert result == "column::CORRECTIVE_ACTIONS.CAPA_ID", (
        f"column_key format regression: expected 'column::CORRECTIVE_ACTIONS.CAPA_ID', "
        f"got {result!r}"
    )
    print("PASS: column_key produces correct 'column::TABLE_NAME.COL_NAME' format")


def test_contains_edge_key_matches_column_key():
    """contains_edge_key must equal column_key (one parent per column → unique edge key)."""
    tbl = "EMPLOYEE"
    col = "ADDR_1"
    assert contains_edge_key(tbl, col) == column_key(tbl, col), (
        "contains_edge_key must equal column_key for the same table/column pair."
    )
    print("PASS: contains_edge_key equals column_key for same table/column")


def test_dry_run_summary_line_present():
    """_run_dry() must always print a summary line with the DRY-RUN label."""
    rows = [_make_row()]
    output = _capture_dry_run(rows)
    assert "DRY-RUN" in output, (
        f"Expected 'DRY-RUN' summary line in output. Got:\n{output}"
    )
    print("PASS: dry-run summary line is always printed")


# ---------------------------------------------------------------------------
# Live ArangoDB tests (gated on ARANGO_DB env var)
# ---------------------------------------------------------------------------

_LIVE_TEST_TABLE = "__TEST_RECONSTRUCT_TBL__"
_LIVE_TEST_COL = "__TEST_COL__"


def _live_arango_connection():
    """Connect to ArangoDB using the same env vars as reconstruct_containment_graph.

    Returns (client, db) on success, or raises an exception on failure.
    Does NOT call sys.exit — callers are responsible for handling errors.
    """
    from arango import ArangoClient

    raw_host = (
        os.environ.get("ARANGO_HOST")
        or os.environ.get("DATABASE_HOST", "http://localhost:8529")
    ).strip()
    if "arangodb.cloud" in raw_host and ":" not in raw_host.split("//", 1)[-1]:
        raw_host = f"{raw_host}:8529"

    db_name = os.environ.get("ARANGO_DB", "manufacturing_graph")
    username = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_ROOT_PASSWORD", "")

    client = ArangoClient(hosts=raw_host)
    sys_db = client.db("_system", username=username, password=password)
    if not sys_db.has_database(db_name):
        raise RuntimeError(f"ArangoDB database {db_name!r} does not exist")
    return client, client.db(db_name, username=username, password=password)


def _make_temp_sqlite_with_test_row() -> str:
    """Create a temporary SQLite database with one test table→column row.

    Returns the path to the temp file; the caller must delete it.
    """
    import sqlite3
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = tmp.name

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE schema_topology_metadata (
            id               INTEGER PRIMARY KEY,
            source_node_type TEXT,
            target_node_type TEXT,
            source_key       TEXT,
            target_key       TEXT,
            edge_predicate   TEXT,
            weight           REAL,
            notes            TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO schema_topology_metadata "
        "VALUES (1, 'table', 'column', ?, ?, 'CONTAINS', 1.0, '')",
        (_LIVE_TEST_TABLE, _LIVE_TEST_COL),
    )
    conn.commit()
    conn.close()
    return path


def _cleanup_live_test_docs(db) -> None:
    """Remove the throwaway vertices and edge written by the live test."""
    sut._ensure_collections(db)
    for coll_name, key in [
        (TABLES_COLLECTION,   table_key(_LIVE_TEST_TABLE)),
        (COLUMNS_COLLECTION,  column_key(_LIVE_TEST_TABLE, _LIVE_TEST_COL)),
        (CONTAINS_EDGE_COLLECTION, contains_edge_key(_LIVE_TEST_TABLE, _LIVE_TEST_COL)),
    ]:
        try:
            coll = db.collection(coll_name)
            if coll.has(key):
                coll.delete(key)
        except Exception as exc:
            print(f"WARN: could not delete test doc '{key}' from '{coll_name}': {exc}")


def _capture_reconstruct(dry_run: bool = False) -> str:
    """Run sut.reconstruct() and return combined stdout as a string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sut.reconstruct(dry_run=dry_run)
    return buf.getvalue()


def test_live_reconstruct_idempotency():
    """Live ArangoDB: reconstruct() is idempotent — second run produces 0 upserts.

    Skipped when ARANGO_DB env var is not set.

    Steps:
      1. Create a throwaway SQLite DB with one test table→column CONTAINS row.
      2. Call reconstruct() (live) — writes table vertex, column vertex, contains edge.
      3. Call reconstruct() again — every document is unchanged, so 0 upserts expected.
      4. Clean up the throwaway documents from ArangoDB and delete the temp SQLite file.
    """
    if not os.environ.get("ARANGO_DB"):
        print("SKIP: ARANGO_DB not set — live ArangoDB reconstruct test skipped")
        return

    try:
        _, db = _live_arango_connection()
    except Exception as exc:
        print(f"SKIP: could not connect to ArangoDB: {exc}")
        return

    tmp_path = _make_temp_sqlite_with_test_row()
    original_sqlite_path = sut.SQLITE_DB_PATH
    sut.SQLITE_DB_PATH = tmp_path

    try:
        # First call — creates the table vertex, column vertex, and contains edge.
        out1 = _capture_reconstruct(dry_run=False)
        assert "vertices upserted:" in out1, (
            f"First reconstruct() run missing upsert summary line. Got:\n{out1}"
        )

        # Second call — all documents are identical; must report 0 upserts.
        out2 = _capture_reconstruct(dry_run=False)
        assert "vertices upserted: 0" in out2, (
            "Second reconstruct() run must report vertices upserted: 0 "
            f"(idempotency). Got:\n{out2}"
        )
        assert "edges upserted: 0" in out2, (
            "Second reconstruct() run must report edges upserted: 0 "
            f"(idempotency). Got:\n{out2}"
        )

        print(
            "PASS: reconstruct() is idempotent — "
            "second live run reports 0 vertex upserts and 0 edge upserts"
        )

    finally:
        sut.SQLITE_DB_PATH = original_sqlite_path
        _cleanup_live_test_docs(db)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _collection_counts(db) -> dict:
    """Return a dict of {collection_name: document_count} for the three containment
    collections.  Used to verify that a reconstruct() call with only skippable rows
    leaves ArangoDB completely untouched.
    """
    sut._ensure_collections(db)
    return {
        TABLES_COLLECTION:        db.collection(TABLES_COLLECTION).count(),
        COLUMNS_COLLECTION:       db.collection(COLUMNS_COLLECTION).count(),
        CONTAINS_EDGE_COLLECTION: db.collection(CONTAINS_EDGE_COLLECTION).count(),
    }


def _make_temp_sqlite_with_row(row_kwargs: dict) -> str:
    """Create a throwaway SQLite database containing one schema_topology_metadata row
    built from *row_kwargs* (id, source_node_type, target_node_type, source_key,
    target_key, edge_predicate, weight, notes).  Returns the temp file path.
    """
    import sqlite3
    import tempfile

    defaults = dict(
        id=1,
        source_node_type="table",
        target_node_type="column",
        source_key="__UNUSED__",
        target_key="__UNUSED_COL__",
        edge_predicate="CONTAINS",
        weight=1.0,
        notes="",
    )
    defaults.update(row_kwargs)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = tmp.name

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE schema_topology_metadata (
            id               INTEGER PRIMARY KEY,
            source_node_type TEXT,
            target_node_type TEXT,
            source_key       TEXT,
            target_key       TEXT,
            edge_predicate   TEXT,
            weight           REAL,
            notes            TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO schema_topology_metadata "
        "VALUES (:id, :source_node_type, :target_node_type, "
        ":source_key, :target_key, :edge_predicate, :weight, :notes)",
        defaults,
    )
    conn.commit()
    conn.close()
    return path


def test_live_unknown_predicate_writes_nothing():
    """Live ArangoDB: a row with an unknown edge_predicate must be skipped and must
    not write any documents to ArangoDB.

    Verification:
    - The summary line reports rows_skipped >= 1.
    - Collection counts for tables, columns, and contains are identical before and
      after the reconstruct() call.

    Skipped when ARANGO_DB env var is not set.
    """
    if not os.environ.get("ARANGO_DB"):
        print("SKIP: ARANGO_DB not set — live unknown-predicate test skipped")
        return

    try:
        _, db = _live_arango_connection()
    except Exception as exc:
        print(f"SKIP: could not connect to ArangoDB: {exc}")
        return

    counts_before = _collection_counts(db)

    tmp_path = _make_temp_sqlite_with_row({"edge_predicate": "NONEXISTENT_PRED"})
    original_sqlite_path = sut.SQLITE_DB_PATH
    sut.SQLITE_DB_PATH = tmp_path

    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sut.reconstruct(dry_run=False)
        out = buf.getvalue()

        assert "rows skipped: 1" in out, (
            f"Expected 'rows skipped: 1' in live output for unknown predicate. Got:\n{out}"
        )

        counts_after = _collection_counts(db)
        assert counts_before == counts_after, (
            f"ArangoDB collection counts changed after a skipped-predicate row.\n"
            f"Before: {counts_before}\nAfter:  {counts_after}"
        )

        print(
            "PASS: live reconstruct() with unknown edge_predicate reports rows_skipped=1 "
            "and leaves ArangoDB collections unchanged"
        )
    finally:
        sut.SQLITE_DB_PATH = original_sqlite_path
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_live_unsupported_node_type_writes_nothing():
    """Live ArangoDB: a row with an unsupported source_node_type must be skipped and
    must not write any documents to ArangoDB.

    Verification:
    - The summary line reports rows_skipped >= 1.
    - Collection counts for tables, columns, and contains are identical before and
      after the reconstruct() call.

    Skipped when ARANGO_DB env var is not set.
    """
    if not os.environ.get("ARANGO_DB"):
        print("SKIP: ARANGO_DB not set — live unsupported-node-type test skipped")
        return

    try:
        _, db = _live_arango_connection()
    except Exception as exc:
        print(f"SKIP: could not connect to ArangoDB: {exc}")
        return

    counts_before = _collection_counts(db)

    tmp_path = _make_temp_sqlite_with_row(
        {"source_node_type": "schema", "edge_predicate": "CONTAINS"}
    )
    original_sqlite_path = sut.SQLITE_DB_PATH
    sut.SQLITE_DB_PATH = tmp_path

    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sut.reconstruct(dry_run=False)
        out = buf.getvalue()

        assert "rows skipped: 1" in out, (
            f"Expected 'rows skipped: 1' in live output for unsupported node type. Got:\n{out}"
        )

        counts_after = _collection_counts(db)
        assert counts_before == counts_after, (
            f"ArangoDB collection counts changed after a skipped-node-type row.\n"
            f"Before: {counts_before}\nAfter:  {counts_after}"
        )

        print(
            "PASS: live reconstruct() with unsupported node type reports rows_skipped=1 "
            "and leaves ArangoDB collections unchanged"
        )
    finally:
        sut.SQLITE_DB_PATH = original_sqlite_path
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_dry_run_valid_row_produces_vertex_and_edge_ops,
        test_unknown_predicate_counted_in_rows_skipped,
        test_unsupported_node_type_counted_in_rows_skipped,
        test_unsupported_target_node_type_counted_in_rows_skipped,
        test_mixed_rows_skip_count_is_accurate,
        test_key_format_table_vertex,
        test_key_format_column_vertex,
        test_contains_edge_key_matches_column_key,
        test_dry_run_summary_line_present,
        test_live_reconstruct_idempotency,
        test_live_unknown_predicate_writes_nothing,
        test_live_unsupported_node_type_writes_nothing,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(
        f"{'PASS' if failed == 0 else 'FAIL'}: "
        f"{len(tests) - failed}/{len(tests)} tests passed"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
