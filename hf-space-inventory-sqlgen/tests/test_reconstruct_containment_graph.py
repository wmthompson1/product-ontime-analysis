"""Tests for reconstruct_containment_graph dry-run logic and key conventions.

No ArangoDB connection is required — all tests exercise either:
  - _run_dry()  : the dry-run path, which parses rows and prints what it would do
  - key helpers : table_key / column_key / contains_edge_key from
                  arangodb_helpers.manufacturing_graph_version_0_0_1

Coverage:
- Valid table→column rows produce two vertex ops and one edge op in dry-run output.
- Rows with an unknown edge_predicate are counted in rows_skipped.
- Rows with an unsupported source_node_type or target_node_type are counted in rows_skipped.
- Key format regression guard: table_key and column_key follow the ``type::NAME``
  convention (uppercase, double-colon prefix) so that a future key-convention
  change immediately breaks this test.

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
