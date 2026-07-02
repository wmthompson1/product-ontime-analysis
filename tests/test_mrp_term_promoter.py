"""
tests/test_mrp_term_promoter.py
Tests for scripts/mrp_term_promoter.py

Covers:
  - approved-only filtering (term nodes; anchor nodes are ignored)
  - node_to_concept_row mapping (name, description, acronym→synonyms, foundational→tags, domain)
  - reserved-token guard fails closed before any DB write
  - dry run never touches DB or files (committed=False, dry_run=True)
  - commit requires MRP_ENABLE_GRAPH_COMMIT=true env var (fails closed without it)
  - INSERT OR IGNORE idempotency: re-running same approved set inserts 0 new rows
  - already_in_certified vs new_concepts reported correctly
  - invalid reviewer_decision fails closed (mirrors committer behaviour)
  - missing reviewer_decision column fails closed
  - SCHEMA_VERSION bump round-trips correctly in a temp file
  - no approved terms exits cleanly (committed=False)
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import mrp_term_promoter as pt  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_TERM_NODES: List[Dict[str, Any]] = [
    {
        "_key": "term__available_capacity",
        "node_type": "proposed_term",
        "name": "Available Capacity",
        "term": "Available Capacity",
        "acronym": "",
        "foundational": False,
        "proposed_definition": "Total productive capacity in a planning period.",
        "document_definition": "The total productive capacity available.",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": True,
    },
    {
        "_key": "term__bill_of_materials",
        "node_type": "proposed_term",
        "name": "Bill of Materials",
        "term": "Bill of Materials",
        "acronym": "BOM",
        "foundational": True,
        "proposed_definition": "Hierarchical list of all components.",
        "document_definition": "A hierarchical structured list of all components.",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": True,
    },
    {
        "_key": "term__lot_sizing",
        "node_type": "proposed_term",
        "name": "Lot Sizing",
        "term": "Lot Sizing",
        "acronym": "",
        "foundational": False,
        "proposed_definition": "Determining the quantity to order or produce.",
        "document_definition": "",
        "approval_status": "proposed",
        "certified": False,
        "is_anchored": False,
    },
]

_ANCHOR_NODES: List[Dict[str, Any]] = [
    {
        "_key": "anchor_perspective__work_orders",
        "node_type": "approved_anchor",
        "name": "Work_Orders",
        "mirrors_certified_name": "Work_Orders",
        "approval_status": "approved_reference",
    },
]

_EDGES: List[Dict[str, Any]] = [
    {
        "_from": "term__available_capacity",
        "_to": "anchor_perspective__work_orders",
        "predicate": "CANDIDATE_TERM_FOR_PERSPECTIVE",
        "match_score": 2,
        "approval_status": "proposed",
    },
]

_PAYLOAD: Dict[str, Any] = {"nodes": _TERM_NODES + _ANCHOR_NODES, "edges": _EDGES}

_CSV_HEADER = [
    "term", "acronym", "foundational", "perspective_anchors",
    "category_anchors", "anchored", "definition", "reviewer_decision",
]
_CSV_HEADER_NO_DECISION = _CSV_HEADER[:-1]


def _make_row(term: str, decision: str, acronym: str = "", foundational: str = "") -> tuple:
    return (term, acronym, foundational, "", "", "yes", f"Def of {term}.", decision)


def _make_run_dir(
    csv_rows: List[tuple],
    payload: Dict[str, Any],
    include_decision_col: bool = True,
) -> Path:
    """Create a temp staging run folder with the given fixture CSV and JSON."""
    tmp = Path(tempfile.mkdtemp())
    run_dir = tmp / "20260701T120000Z"
    run_dir.mkdir()

    header = _CSV_HEADER if include_decision_col else _CSV_HEADER_NO_DECISION
    with (run_dir / "proposed_terms.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in csv_rows:
            writer.writerow(row[: len(header)])

    (run_dir / "proposed_terms.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return run_dir


def _make_temp_db() -> Path:
    """Create a minimal in-memory SQLite DB file with schema_concepts table."""
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "test_manufacturing.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_concepts (
            concept_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_name         TEXT NOT NULL UNIQUE,
            concept_type         TEXT DEFAULT '',
            description          TEXT,
            domain               TEXT,
            parent_concept_id    INTEGER,
            created_at           DATETIME,
            synonyms             TEXT,
            tags                 TEXT,
            computation_template TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _make_temp_export_script(version: int = 19, milestone: str = "test_milestone") -> Path:
    """Create a minimal export_graph_metadata.py stub in a temp dir."""
    tmp = Path(tempfile.mkdtemp())
    script = tmp / "export_graph_metadata.py"
    script.write_text(
        f'SCHEMA_VERSION = {version}\n'
        f'MILESTONE_NAME = "{milestone}"\n'
        'import sys; sys.exit(0)\n',
        encoding="utf-8",
    )
    return script


# ---------------------------------------------------------------------------
# Unit tests — filtering
# ---------------------------------------------------------------------------


def test_filter_approved_only():
    """Only proposed_term nodes with reviewer_decision='approved' are returned."""
    csv_rows = [
        _make_row("Available Capacity", "approved"),
        _make_row("Bill of Materials", "rejected"),
        _make_row("Lot Sizing", "proposed"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)

    loaded_csv = pt._load_csv(run_dir)
    loaded_json = pt._load_json(run_dir)
    approved_nodes, rejected_names = pt._filter_approved_terms(
        loaded_csv, loaded_json["nodes"]
    )

    approved_names = {n.get("name") or n.get("term") for n in approved_nodes}
    assert approved_names == {"Available Capacity"}, (
        f"Expected only 'Available Capacity', got: {approved_names}"
    )
    assert "Bill of Materials" in rejected_names, "rejected term must appear in rejected_names"
    assert "Lot Sizing" not in rejected_names, "pending term must not be in rejected_names"


def test_anchor_nodes_are_excluded_from_promotion():
    """Anchor nodes (node_type='approved_anchor') are never returned for promotion."""
    csv_rows = [_make_row("Available Capacity", "approved")]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)

    loaded_csv = pt._load_csv(run_dir)
    loaded_json = pt._load_json(run_dir)
    approved_nodes, _ = pt._filter_approved_terms(loaded_csv, loaded_json["nodes"])

    for node in approved_nodes:
        assert node.get("node_type") != "approved_anchor", (
            f"Anchor node must not appear in promotion set: {node}"
        )


# ---------------------------------------------------------------------------
# Unit tests — node_to_concept_row mapping
# ---------------------------------------------------------------------------


def test_concept_row_mapping_basic():
    """node_to_concept_row maps term fields to schema_concepts columns correctly."""
    node = _TERM_NODES[0]  # Available Capacity, no acronym, not foundational
    row = pt._node_to_concept_row(node)

    assert row["concept_name"] == "Available Capacity"
    assert row["domain"] == "MRP"
    assert row["description"] == "The total productive capacity available."  # document_definition
    assert row["synonyms"] == "[]", "empty acronym → empty synonyms array"
    assert row["tags"] == "[]", "non-foundational → empty tags"
    assert row["computation_template"] is None


def test_concept_row_mapping_with_acronym_and_foundational():
    """Acronym populates synonyms; foundational=True populates tags."""
    node = _TERM_NODES[1]  # Bill of Materials, BOM, foundational=True
    row = pt._node_to_concept_row(node)

    assert row["concept_name"] == "Bill of Materials"
    assert json.loads(row["synonyms"]) == ["BOM"]
    assert json.loads(row["tags"]) == ["foundational"]


def test_concept_row_falls_back_to_proposed_definition():
    """When document_definition is absent/empty, proposed_definition is used."""
    node = {**_TERM_NODES[2]}  # Lot Sizing has empty document_definition
    row = pt._node_to_concept_row(node)

    assert row["description"] == "Determining the quantity to order or produce."


def test_concept_row_domain_always_mrp():
    """domain is always 'MRP' regardless of what the node carries."""
    node = {**_TERM_NODES[0], "domain": "something_else"}
    row = pt._node_to_concept_row(node)

    assert row["domain"] == "MRP"


# ---------------------------------------------------------------------------
# Unit tests — reserved-token guard
# ---------------------------------------------------------------------------


def test_reserved_token_guard_fails_closed():
    """concept_name matching an exporter reserved token raises ValueError."""
    bad_rows = [{"concept_name": "none"}]
    try:
        pt._check_reserved_names(bad_rows)
        raise AssertionError("Expected ValueError was not raised for reserved name 'none'")
    except ValueError as exc:
        assert "none" in str(exc).lower()


def test_reserved_token_guard_passes_normal_names():
    """Ordinary MRP concept names do not trigger the reserved-token guard."""
    rows = [
        {"concept_name": "Available Capacity"},
        {"concept_name": "Bill of Materials"},
        {"concept_name": "Net Requirements"},
    ]
    pt._check_reserved_names(rows)  # must not raise


# ---------------------------------------------------------------------------
# Unit tests — SCHEMA_VERSION bump
# ---------------------------------------------------------------------------


def test_schema_version_read():
    """_read_current_schema_version parses the integer from the script file."""
    script = _make_temp_export_script(version=19)
    assert pt._read_current_schema_version(script) == 19


def test_schema_version_bump_round_trip():
    """_bump_schema_version rewrites the version integer and milestone name."""
    script = _make_temp_export_script(version=19, milestone="old_milestone")
    pt._bump_schema_version(script, 20, "mrp_term_promotion")

    text = script.read_text(encoding="utf-8")
    assert "SCHEMA_VERSION = 20" in text, "version not bumped correctly"
    assert 'MILESTONE_NAME = "mrp_term_promotion"' in text, "milestone not updated"
    assert "SCHEMA_VERSION = 19" not in text, "old version must be replaced"


# ---------------------------------------------------------------------------
# Unit tests — dry run behaviour
# ---------------------------------------------------------------------------


def test_dry_run_never_writes(tmp_path):
    """run() with commit=False never inserts rows or modifies any file."""
    csv_rows = [
        _make_row("Available Capacity", "approved"),
        _make_row("Lot Sizing", "rejected"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)
    original_text = export_script.read_text(encoding="utf-8")

    summary = pt.run(
        run_dir=run_dir,
        commit=False,
        db_path=db_path,
        export_script=export_script,
        coverage_check=tmp_path / "nonexistent_coverage.py",
    )

    assert summary["committed"] is False
    assert summary["dry_run"] is True

    # DB must be untouched
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM schema_concepts").fetchone()[0]
    conn.close()
    assert count == 0, f"Dry run must not write to DB, found {count} rows"

    # Export script must be untouched
    assert export_script.read_text(encoding="utf-8") == original_text, (
        "Dry run must not modify export_graph_metadata.py"
    )


def test_dry_run_reports_new_vs_existing(tmp_path):
    """Dry run still reports which concepts are new vs already in the certified layer."""
    csv_rows = [
        _make_row("Available Capacity", "approved"),
        _make_row("Bill of Materials", "approved"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()

    # Pre-populate one concept as if it's already certified
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO schema_concepts (concept_name, domain) VALUES (?, ?)",
        ("Available Capacity", "MRP"),
    )
    conn.commit()
    conn.close()

    export_script = _make_temp_export_script(version=19)
    summary = pt.run(
        run_dir=run_dir,
        commit=False,
        db_path=db_path,
        export_script=export_script,
        coverage_check=tmp_path / "nonexistent_coverage.py",
    )

    assert "Available Capacity" in summary["already_in_certified"]
    assert "Bill of Materials" in summary["new_concepts"]


# ---------------------------------------------------------------------------
# Unit tests — commit requires env var
# ---------------------------------------------------------------------------


def test_commit_requires_env_var(tmp_path):
    """Committing without MRP_ENABLE_GRAPH_COMMIT=true raises EnvironmentError."""
    csv_rows = [_make_row("Available Capacity", "approved")]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    env_without_flag = {k: v for k, v in os.environ.items() if k != "MRP_ENABLE_GRAPH_COMMIT"}
    with mock.patch.dict(os.environ, env_without_flag, clear=True):
        try:
            pt.run(
                run_dir=run_dir,
                commit=True,
                db_path=db_path,
                export_script=export_script,
                coverage_check=tmp_path / "nonexistent_coverage.py",
            )
            raise AssertionError("Expected EnvironmentError was not raised")
        except EnvironmentError as exc:
            assert "MRP_ENABLE_GRAPH_COMMIT" in str(exc)


# ---------------------------------------------------------------------------
# Unit tests — full commit (with env var mocked, exporter mocked)
# ---------------------------------------------------------------------------


def test_commit_inserts_new_concepts(tmp_path):
    """With env var set and exporter mocked, commit inserts schema_concepts rows."""
    csv_rows = [
        _make_row("Available Capacity", "approved"),
        _make_row("Bill of Materials", "approved", acronym="BOM", foundational="yes"),
        _make_row("Lot Sizing", "rejected"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    with mock.patch.dict(os.environ, {"MRP_ENABLE_GRAPH_COMMIT": "true"}):
        with mock.patch.object(pt, "_run_exporter"):
            with mock.patch.object(pt, "_run_coverage_check"):
                summary = pt.run(
                    run_dir=run_dir,
                    commit=True,
                    db_path=db_path,
                    export_script=export_script,
                    coverage_check=tmp_path / "nonexistent_coverage.py",
                )

    assert summary["committed"] is True
    assert summary["dry_run"] is False
    assert summary["inserted"] == 2, f"Expected 2 inserted, got {summary['inserted']}"

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT concept_name, domain FROM schema_concepts ORDER BY concept_name"
    ).fetchall()
    conn.close()
    names = {r[0] for r in rows}
    assert "Available Capacity" in names
    assert "Bill of Materials" in names
    assert "Lot Sizing" not in names, "rejected term must not be inserted"
    for _, domain in rows:
        assert domain == "MRP", f"Every promoted concept must have domain='MRP', got '{domain}'"


def test_commit_idempotent(tmp_path):
    """Re-running commit with same approved set inserts 0 new rows (INSERT OR IGNORE)."""
    csv_rows = [_make_row("Available Capacity", "approved")]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    with mock.patch.dict(os.environ, {"MRP_ENABLE_GRAPH_COMMIT": "true"}):
        with mock.patch.object(pt, "_run_exporter"):
            with mock.patch.object(pt, "_run_coverage_check"):
                pt.run(
                    run_dir=run_dir,
                    commit=True,
                    db_path=db_path,
                    export_script=export_script,
                    coverage_check=tmp_path / "nonexistent_coverage.py",
                )
                # Second run — now uses version 20
                export_script2 = _make_temp_export_script(version=20)
                summary2 = pt.run(
                    run_dir=run_dir,
                    commit=True,
                    db_path=db_path,
                    export_script=export_script2,
                    coverage_check=tmp_path / "nonexistent_coverage.py",
                )

    assert summary2["inserted"] == 0, (
        f"Idempotent re-run must insert 0 rows, got {summary2['inserted']}"
    )
    assert "Available Capacity" in summary2["already_in_certified"]


def test_commit_bumps_schema_version(tmp_path):
    """Commit increments SCHEMA_VERSION by exactly 1 in the export script."""
    csv_rows = [_make_row("Available Capacity", "approved")]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    with mock.patch.dict(os.environ, {"MRP_ENABLE_GRAPH_COMMIT": "true"}):
        with mock.patch.object(pt, "_run_exporter"):
            with mock.patch.object(pt, "_run_coverage_check"):
                summary = pt.run(
                    run_dir=run_dir,
                    commit=True,
                    db_path=db_path,
                    export_script=export_script,
                    coverage_check=tmp_path / "nonexistent_coverage.py",
                )

    assert summary["schema_version_bumped_to"] == 20
    text = export_script.read_text(encoding="utf-8")
    assert "SCHEMA_VERSION = 20" in text


# ---------------------------------------------------------------------------
# Unit tests — edge cases
# ---------------------------------------------------------------------------


def test_no_approved_terms_exits_clean(tmp_path):
    """All rejected/pending → no commit, no error, committed=False."""
    csv_rows = [
        _make_row("Available Capacity", "rejected"),
        _make_row("Lot Sizing", "proposed"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    summary = pt.run(
        run_dir=run_dir,
        commit=False,
        db_path=db_path,
        export_script=export_script,
        coverage_check=tmp_path / "nonexistent_coverage.py",
    )

    assert summary["approved"] == 0
    assert summary["committed"] is False
    assert summary.get("inserted") is None, "no insert should have occurred"


def test_invalid_decision_fails_closed(tmp_path):
    """Unrecognised reviewer_decision value raises ValueError before any write."""
    csv_rows = [
        _make_row("Available Capacity", "approved"),
        _make_row("Lot Sizing", "BAD_DECISION"),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD)
    db_path = _make_temp_db()
    export_script = _make_temp_export_script(version=19)

    try:
        pt.run(
            run_dir=run_dir,
            commit=False,
            db_path=db_path,
            export_script=export_script,
            coverage_check=tmp_path / "nonexistent_coverage.py",
        )
        raise AssertionError("Expected ValueError was not raised")
    except ValueError as exc:
        assert "Unrecognised reviewer_decision" in str(exc)
        assert "BAD_DECISION" in str(exc)

    # DB must be untouched
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM schema_concepts").fetchone()[0]
    conn.close()
    assert count == 0, "No DB writes should occur before validation passes"


def test_missing_reviewer_decision_column_fails_closed(tmp_path):
    """CSV without reviewer_decision column fails closed with a clear message."""
    csv_rows = [
        ("Available Capacity", "", "", "", "", "yes", "Cap definition."),
    ]
    run_dir = _make_run_dir(csv_rows, _PAYLOAD, include_decision_col=False)

    try:
        pt._load_csv(run_dir)
        raise AssertionError("Expected ValueError for missing reviewer_decision column")
    except ValueError as exc:
        assert "reviewer_decision" in str(exc)


# ---------------------------------------------------------------------------
# Entry point (run directly or via pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    tests = [
        test_filter_approved_only,
        test_anchor_nodes_are_excluded_from_promotion,
        test_concept_row_mapping_basic,
        test_concept_row_mapping_with_acronym_and_foundational,
        test_concept_row_falls_back_to_proposed_definition,
        test_concept_row_domain_always_mrp,
        test_reserved_token_guard_fails_closed,
        test_reserved_token_guard_passes_normal_names,
        test_schema_version_read,
        test_schema_version_bump_round_trip,
        test_dry_run_never_writes,
        test_dry_run_reports_new_vs_existing,
        test_commit_requires_env_var,
        test_commit_inserts_new_concepts,
        test_commit_idempotent,
        test_commit_bumps_schema_version,
        test_no_approved_terms_exits_clean,
        test_invalid_decision_fails_closed,
        test_missing_reviewer_decision_column_fails_closed,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        import inspect

        sig = inspect.signature(test_fn)
        if sig.parameters:
            # Provide a real tmp_path for tests that request it
            import pathlib
            import tempfile
            _tmp = pathlib.Path(tempfile.mkdtemp())
            args = [_tmp]
        else:
            args = []
        try:
            test_fn(*args)
            print(f"  PASS  {test_fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {test_fn.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
