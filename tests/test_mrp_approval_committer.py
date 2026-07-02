"""
tests/test_mrp_approval_committer.py
Tests for scripts/mrp_approval_committer.py

Covers:
  - approved-only filtering (term nodes and edges)
  - anchor node inclusion for approved terms
  - rejected and pending terms excluded from approved set
  - no approved rows exits cleanly (no error, committed=False)
  - unrecognised reviewer_decision value fails closed
  - backward-compat: CSV without reviewer_decision column defaults all to proposed
  - dry run never calls commit (committed=False)
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import mrp_approval_committer as ac  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_TERM_NODES: List[Dict[str, Any]] = [
    {
        "_key": "term__available_capacity",
        "node_type": "proposed_term",
        "name": "Available Capacity",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": True,
    },
    {
        "_key": "term__bill_of_materials",
        "node_type": "proposed_term",
        "name": "Bill of Materials",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": True,
    },
    {
        "_key": "term__lot_sizing",
        "node_type": "proposed_term",
        "name": "Lot Sizing",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": False,
    },
    {
        "_key": "term__net_requirements",
        "node_type": "proposed_term",
        "name": "Net Requirements",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": True,
    },
]

_ANCHOR_NODES: List[Dict[str, Any]] = [
    {
        "_key": "anchor_perspective__work_orders",
        "node_type": "approved_anchor",
        "name": "Work_Orders",
        "approval_status": "approved_reference",
    },
    {
        "_key": "anchor_perspective__parts",
        "node_type": "approved_anchor",
        "name": "Parts",
        "approval_status": "approved_reference",
    },
]

_EDGES: List[Dict[str, Any]] = [
    {
        "_from": "term__available_capacity",
        "_to": "anchor_perspective__work_orders",
        "predicate": "CANDIDATE_TERM_FOR_PERSPECTIVE",
    },
    {
        "_from": "term__bill_of_materials",
        "_to": "anchor_perspective__parts",
        "predicate": "CANDIDATE_TERM_FOR_PERSPECTIVE",
    },
    {
        "_from": "term__net_requirements",
        "_to": "anchor_perspective__work_orders",
        "predicate": "CANDIDATE_TERM_FOR_PERSPECTIVE",
    },
]

_PAYLOAD: Dict[str, Any] = {"nodes": _TERM_NODES + _ANCHOR_NODES, "edges": _EDGES}

_CSV_HEADER_WITH_DECISION = [
    "term", "acronym", "foundational", "perspective_anchors",
    "category_anchors", "anchored", "definition", "reviewer_decision",
]
_CSV_HEADER_WITHOUT_DECISION = _CSV_HEADER_WITH_DECISION[:-1]

_FULL_DECISIONS = [
    ("Available Capacity", "approved"),
    ("Bill of Materials", "rejected"),
    ("Lot Sizing", "proposed"),
    ("Net Requirements", "approved"),
]


def _make_csv_row(term: str, decision: str) -> tuple:
    return (term, "", "", "", "", "yes", f"Definition of {term}.", decision)


def _make_run_dir(
    csv_rows: List[tuple],
    payload: Dict[str, Any],
    include_reviewer_decision: bool = True,
) -> Path:
    """Create a temp staging run folder with given fixture CSV and JSON."""
    tmp = Path(tempfile.mkdtemp())
    run_dir = tmp / "20260701T120000Z"
    run_dir.mkdir()

    header = _CSV_HEADER_WITH_DECISION if include_reviewer_decision else _CSV_HEADER_WITHOUT_DECISION
    with (run_dir / "proposed_terms.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in csv_rows:
            writer.writerow(row[: len(header)])

    (run_dir / "proposed_terms.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_approved_only_filter():
    """Only terms with reviewer_decision=='approved' appear in approved_nodes."""
    rows = [_make_csv_row(t, d) for t, d in _FULL_DECISIONS]
    run_dir = _make_run_dir(rows, _PAYLOAD)

    csv_rows = ac._load_csv(run_dir)
    payload = ac._load_json(run_dir)
    approved_nodes, _edges, _anchors = ac._filter_payload(
        csv_rows, payload["nodes"], payload["edges"]
    )

    approved_names = {n["name"] for n in approved_nodes}
    assert approved_names == {"Available Capacity", "Net Requirements"}, (
        f"Expected only approved terms, got: {approved_names}"
    )
    assert "Bill of Materials" not in approved_names, "rejected term must be excluded"
    assert "Lot Sizing" not in approved_names, "pending term must be excluded"


def test_dry_run_committed_false():
    """run() with commit=False always returns committed=False and dry_run=True."""
    rows = [_make_csv_row(t, d) for t, d in _FULL_DECISIONS]
    run_dir = _make_run_dir(rows, _PAYLOAD)

    summary = ac.run(run_dir=run_dir, commit=False)

    assert summary["committed"] is False, "dry run must not set committed=True"
    assert summary["dry_run"] is True, "dry run must set dry_run=True"
    assert summary["approved"] == 2, f"expected 2 approved, got {summary['approved']}"


def test_no_approved_exits_clean():
    """All proposed/rejected → approved=0, committed=False, no exception raised."""
    rows = [
        _make_csv_row("Available Capacity", "rejected"),
        _make_csv_row("Lot Sizing", "proposed"),
        _make_csv_row("Bill of Materials", "rejected"),
    ]
    payload: Dict[str, Any] = {
        "nodes": _TERM_NODES[:3] + _ANCHOR_NODES,
        "edges": _EDGES[:2],
    }
    run_dir = _make_run_dir(rows, payload)

    summary = ac.run(run_dir=run_dir, commit=False)

    assert summary["approved"] == 0, "no approved terms expected"
    assert summary["committed"] is False
    assert summary["edges_included"] == 0, "no edges should be included"


def test_invalid_decision_fails_closed():
    """An unrecognised reviewer_decision value raises ValueError."""
    rows = [
        _make_csv_row("Available Capacity", "approved"),
        _make_csv_row("Bill of Materials", "INVALID_DECISION"),
    ]
    run_dir = _make_run_dir(rows, _PAYLOAD)

    csv_rows = ac._load_csv(run_dir)
    try:
        ac._validate_decisions(csv_rows)
        raise AssertionError("Expected ValueError was not raised for invalid decision")
    except ValueError as exc:
        assert "Unrecognised reviewer_decision" in str(exc), (
            f"Error message should mention 'Unrecognised reviewer_decision', got: {exc}"
        )
        assert "INVALID_DECISION" in str(exc)


def test_missing_reviewer_decision_column_defaults_proposed():
    """Old CSVs without reviewer_decision column → all default to 'proposed', nothing approved."""
    rows = [
        ("Available Capacity", "", "", "", "", "yes", "Cap definition."),
        ("Bill of Materials", "BOM", "yes", "", "", "yes", "BOM definition."),
    ]
    run_dir = _make_run_dir(rows, _PAYLOAD, include_reviewer_decision=False)

    csv_rows = ac._load_csv(run_dir)
    for row in csv_rows:
        decision = row.get("reviewer_decision") or "proposed"
        assert decision == "proposed", (
            f"Missing column should default to 'proposed', got '{decision}'"
        )

    summary = ac.run(run_dir=run_dir, commit=False)
    assert summary["approved"] == 0, "no approved terms without column"
    assert summary["committed"] is False


def test_edges_filtered_to_approved_terms():
    """Edges from rejected/pending terms are excluded; only approved terms' edges included."""
    rows = [_make_csv_row(t, d) for t, d in _FULL_DECISIONS]
    run_dir = _make_run_dir(rows, _PAYLOAD)

    csv_rows = ac._load_csv(run_dir)
    payload = ac._load_json(run_dir)
    _nodes, approved_edges, _anchors = ac._filter_payload(
        csv_rows, payload["nodes"], payload["edges"]
    )

    from_keys = {e["_from"] for e in approved_edges}
    assert "term__available_capacity" in from_keys, "approved term's edge must be included"
    assert "term__net_requirements" in from_keys, "approved term's edge must be included"
    assert "term__bill_of_materials" not in from_keys, "rejected term's edge must be excluded"
    assert "term__lot_sizing" not in from_keys, "pending term's edge must be excluded"


def test_anchor_nodes_included_for_approved_terms():
    """Anchor nodes referenced by approved terms' edges are pulled through; others excluded."""
    rows = [_make_csv_row(t, d) for t, d in _FULL_DECISIONS]
    run_dir = _make_run_dir(rows, _PAYLOAD)

    csv_rows = ac._load_csv(run_dir)
    payload = ac._load_json(run_dir)
    _nodes, _edges, anchor_nodes = ac._filter_payload(
        csv_rows, payload["nodes"], payload["edges"]
    )

    anchor_keys = {n["_key"] for n in anchor_nodes}
    assert "anchor_perspective__work_orders" in anchor_keys, (
        "Work_Orders anchor must be included (referenced by approved Available Capacity + Net Requirements)"
    )
    assert "anchor_perspective__parts" not in anchor_keys, (
        "Parts anchor must NOT be included (only referenced by rejected Bill of Materials)"
    )


# ---------------------------------------------------------------------------
# Standalone runner (also runs under pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _TESTS = [
        test_approved_only_filter,
        test_dry_run_committed_false,
        test_no_approved_exits_clean,
        test_invalid_decision_fails_closed,
        test_missing_reviewer_decision_column_defaults_proposed,
        test_edges_filtered_to_approved_terms,
        test_anchor_nodes_included_for_approved_terms,
    ]
    passed = failed = 0
    for _t in _TESTS:
        try:
            _t()
            print(f"PASS  {_t.__name__}")
            passed += 1
        except Exception as _exc:
            import traceback
            print(f"FAIL  {_t.__name__}: {_exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} approval committer tests passed")
    if failed:
        raise SystemExit(1)
