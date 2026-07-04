"""
tests/test_mrp_terminology_stager_preserve.py
Tests for the --preserve-decisions feature of scripts/mrp_terminology_stager.py

Covers:
  - _load_prior_decisions: loads only approved/rejected rows, ignores proposed/blank
  - _load_prior_decisions: raises FileNotFoundError on missing CSV
  - write_artifacts: carries approved decision forward for a matching term
  - write_artifacts: carries rejected decision forward for a matching term
  - write_artifacts: brand-new terms not in prior map start as 'proposed'
  - write_artifacts: 'proposed' value in prior map does NOT carry over (starts as 'proposed', not pinned)
  - write_artifacts: blank reviewer_decision in prior map does NOT carry over
  - write_artifacts: prior_decisions=None behaves identically to original (all 'proposed')
"""

from __future__ import annotations

import csv
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import mrp_terminology_stager as stager


# ---------------------------------------------------------------------------
# Minimal CandidateTerm factory for tests (avoids docx/SQLite deps)
# ---------------------------------------------------------------------------

def _make_term(name: str, foundational: bool = False, definition: str = "A definition.") -> stager.CandidateTerm:
    return stager.CandidateTerm(
        term=name,
        slug=stager.slugify(name),
        acronym="",
        foundational=foundational,
        definition=definition,
        source_section="Glossary",
        perspective_anchors=[],
        category_anchors=[],
    )


def _write_prior_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    """Write a minimal proposed_terms.csv with term and reviewer_decision columns."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["term", "acronym", "reviewer_decision"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_and_read_csv(
    terms: List[stager.CandidateTerm],
    prior_decisions: Dict[str, str] | None,
) -> List[Dict[str, str]]:
    """Run write_artifacts into a temp dir and return the rows from proposed_terms.csv."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run"
        payload: Dict[str, Any] = {"nodes": [], "edges": []}
        manifest: Dict[str, Any] = {"run_id": "test"}
        stager.write_artifacts(run_dir, payload, terms, manifest, prior_decisions)
        with (run_dir / "proposed_terms.csv").open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Tests for _load_prior_decisions
# ---------------------------------------------------------------------------

class TestLoadPriorDecisions:
    def test_loads_approved_row(self, tmp_path):
        csv_path = tmp_path / "prior.csv"
        _write_prior_csv(csv_path, [
            {"term": "Safety Stock", "acronym": "", "reviewer_decision": "approved"},
        ])
        decisions = stager._load_prior_decisions(csv_path)
        assert decisions == {"Safety Stock": "approved"}

    def test_loads_rejected_row(self, tmp_path):
        csv_path = tmp_path / "prior.csv"
        _write_prior_csv(csv_path, [
            {"term": "Phantom Bill", "acronym": "", "reviewer_decision": "rejected"},
        ])
        decisions = stager._load_prior_decisions(csv_path)
        assert decisions == {"Phantom Bill": "rejected"}

    def test_ignores_proposed_row(self, tmp_path):
        csv_path = tmp_path / "prior.csv"
        _write_prior_csv(csv_path, [
            {"term": "Lead Time", "acronym": "", "reviewer_decision": "proposed"},
        ])
        decisions = stager._load_prior_decisions(csv_path)
        assert decisions == {}

    def test_ignores_blank_decision(self, tmp_path):
        csv_path = tmp_path / "prior.csv"
        _write_prior_csv(csv_path, [
            {"term": "Cycle Count", "acronym": "", "reviewer_decision": ""},
        ])
        decisions = stager._load_prior_decisions(csv_path)
        assert decisions == {}

    def test_loads_mixed_rows(self, tmp_path):
        csv_path = tmp_path / "prior.csv"
        _write_prior_csv(csv_path, [
            {"term": "Safety Stock", "acronym": "", "reviewer_decision": "approved"},
            {"term": "Phantom Bill", "acronym": "", "reviewer_decision": "rejected"},
            {"term": "Lead Time", "acronym": "", "reviewer_decision": "proposed"},
            {"term": "Cycle Count", "acronym": "", "reviewer_decision": ""},
        ])
        decisions = stager._load_prior_decisions(csv_path)
        assert decisions == {"Safety Stock": "approved", "Phantom Bill": "rejected"}

    def test_raises_on_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.csv"
        try:
            stager._load_prior_decisions(missing)
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Tests for write_artifacts with prior_decisions
# ---------------------------------------------------------------------------

class TestWriteArtifactsPreserveDecisions:
    def test_approved_decision_carries_over(self):
        terms = [_make_term("Safety Stock")]
        prior = {"Safety Stock": "approved"}
        rows = _write_and_read_csv(terms, prior)
        assert rows[0]["reviewer_decision"] == "approved"

    def test_rejected_decision_carries_over(self):
        terms = [_make_term("Phantom Bill")]
        prior = {"Phantom Bill": "rejected"}
        rows = _write_and_read_csv(terms, prior)
        assert rows[0]["reviewer_decision"] == "rejected"

    def test_brand_new_term_starts_as_proposed(self):
        terms = [_make_term("Brand New Term")]
        prior = {"Safety Stock": "approved"}
        rows = _write_and_read_csv(terms, prior)
        assert rows[0]["reviewer_decision"] == "proposed"

    def test_proposed_in_prior_does_not_pin(self):
        terms = [_make_term("Lead Time")]
        prior = {"Lead Time": "proposed"}
        rows = _write_and_read_csv(terms, prior)
        assert rows[0]["reviewer_decision"] == "proposed"

    def test_none_prior_all_proposed(self):
        terms = [_make_term("Safety Stock"), _make_term("Phantom Bill")]
        rows = _write_and_read_csv(terms, None)
        assert all(r["reviewer_decision"] == "proposed" for r in rows)

    def test_mixed_old_and_new_terms(self):
        terms = [
            _make_term("Safety Stock"),
            _make_term("Phantom Bill"),
            _make_term("Brand New Term"),
        ]
        prior = {"Safety Stock": "approved", "Phantom Bill": "rejected"}
        rows = _write_and_read_csv(terms, prior)
        by_term = {r["term"]: r["reviewer_decision"] for r in rows}
        assert by_term["Safety Stock"] == "approved"
        assert by_term["Phantom Bill"] == "rejected"
        assert by_term["Brand New Term"] == "proposed"

    def test_empty_prior_map_all_proposed(self):
        terms = [_make_term("Safety Stock")]
        rows = _write_and_read_csv(terms, {})
        assert rows[0]["reviewer_decision"] == "proposed"
