"""
scripts/mrp_approval_committer.py
Review-to-intermediate committer for MRP research term proposals.

Reads a staging run's reviewed proposed_terms.csv (from mrp_research_staging/),
filters rows where reviewer_decision == 'approved', resolves their nodes and edges
from the companion proposed_terms.json, and upserts them into the separate
`mrp_research` ArangoDB graph via the librarian's gated commit path.

Governance (the "Solder Pattern"):
  * Only terms explicitly marked reviewer_decision='approved' are committed.
    No bulk-approve shortcut; each term requires an explicit decision.
  * Approved anchor nodes referenced by approved edges are carried automatically.
  * Default is a DRY RUN — prints a decision summary, touches no database.
  * Live writes require --commit AND MRP_ENABLE_GRAPH_COMMIT=true in the environment.
  * The librarian's commit_to_arangodb guard enforces research-only isolation;
    the certified `manufacturing_graph` is structurally unreachable from here.
  * An unrecognised reviewer_decision value (not proposed/approved/rejected) fails
    closed with a clear error rather than silently proceeding.

The reviewer_decision column is required. CSVs that lack it are rejected with a
clear error; use `--migrate-csv` (or re-run the stager) to add the column.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("mrp_approval_committer")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

DEFAULT_STAGING_ROOT = Path(
    os.getenv("MRP_RESEARCH_STAGING_ROOT", str(_REPO_ROOT / "mrp_research_staging"))
).expanduser()

VALID_DECISIONS: Set[str] = {"proposed", "approved", "rejected"}


# ---------------------------------------------------------------------------
# Staging folder helpers
# ---------------------------------------------------------------------------

def _latest_run_dir(staging_root: Path) -> Path:
    """Return the most recent run folder (highest sort-order name), or raise."""
    dirs = sorted(
        (d for d in staging_root.iterdir() if d.is_dir()),
        key=lambda d: d.name,
    )
    if not dirs:
        raise FileNotFoundError(f"No staging runs found in {staging_root}")
    return dirs[-1]


def _resolve_run_dir(
    run_id: Optional[str],
    staging_root: Path,
) -> Path:
    """Resolve the staging run directory from an explicit run_id or auto-pick latest."""
    if run_id:
        run_dir = staging_root / run_id
        if not run_dir.is_dir():
            available = sorted(d.name for d in staging_root.iterdir() if d.is_dir())
            raise FileNotFoundError(
                f"Staging run folder not found: {run_dir}. "
                f"Available runs: {available}"
            )
        return run_dir
    return _latest_run_dir(staging_root)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_csv(run_dir: Path) -> List[Dict[str, str]]:
    """Load proposed_terms.csv; fail closed if reviewer_decision column is absent."""
    csv_path = run_dir / "proposed_terms.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"proposed_terms.csv not found in {run_dir}")
    rows: List[Dict[str, str]] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        if "reviewer_decision" not in fieldnames:
            raise ValueError(
                "proposed_terms.csv is missing the 'reviewer_decision' column. "
                "Re-run the terminology stager to regenerate the CSV with this "
                "column, then set each row to 'approved', 'rejected', or 'proposed'."
            )
        for row in reader:
            rows.append(dict(row))
    return rows


def _load_json(run_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load proposed_terms.json and validate its structure."""
    json_path = run_dir / "proposed_terms.json"
    if not json_path.exists():
        raise FileNotFoundError(f"proposed_terms.json not found in {run_dir}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("nodes"), list) or not isinstance(payload.get("edges"), list):
        raise ValueError(
            f"proposed_terms.json in {run_dir} must contain 'nodes' and 'edges' arrays"
        )
    return payload


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_decisions(csv_rows: List[Dict[str, str]]) -> None:
    """Fail closed on any blank or unrecognised reviewer_decision value."""
    for row in csv_rows:
        raw = (row.get("reviewer_decision") or "").strip()
        if not raw:
            raise ValueError(
                f"Blank reviewer_decision for term '{row.get('term', '?')}'. "
                f"Set each row to one of: {sorted(VALID_DECISIONS)}."
            )
        if raw.lower() not in VALID_DECISIONS:
            raise ValueError(
                f"Unrecognised reviewer_decision '{raw}' for term "
                f"'{row.get('term', '?')}'. "
                f"Valid values: {sorted(VALID_DECISIONS)}. "
                "Correct the CSV before running the committer."
            )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def _filter_payload(
    csv_rows: List[Dict[str, str]],
    json_nodes: List[Dict[str, Any]],
    json_edges: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (approved_term_nodes, approved_edges, referenced_anchor_nodes).

    Only nodes for terms whose reviewer_decision is 'approved' in the CSV are
    returned.  Edges are included only when their _from key matches an approved
    term.  Anchor nodes (node_type=='approved_anchor') referenced by those edges
    are collected automatically so the commit payload is self-contained.
    """
    term_by_name: Dict[str, Dict[str, Any]] = {
        n["name"]: n
        for n in json_nodes
        if n.get("node_type") == "proposed_term"
    }
    anchor_by_key: Dict[str, Dict[str, Any]] = {
        n["_key"]: n
        for n in json_nodes
        if n.get("node_type") == "approved_anchor"
    }

    approved_names: Set[str] = {
        row["term"]
        for row in csv_rows
        if (row.get("reviewer_decision") or "proposed").strip().lower() == "approved"
    }

    approved_nodes = [term_by_name[name] for name in approved_names if name in term_by_name]
    approved_keys: Set[str] = {n["_key"] for n in approved_nodes}

    approved_edges: List[Dict[str, Any]] = []
    referenced_anchor_keys: Set[str] = set()
    for edge in json_edges:
        from_key = (edge.get("_from") or "").strip()
        if from_key in approved_keys:
            approved_edges.append(edge)
            to_key = (edge.get("_to") or "").strip()
            if to_key in anchor_by_key:
                referenced_anchor_keys.add(to_key)

    anchor_nodes = [anchor_by_key[k] for k in sorted(referenced_anchor_keys)]

    return approved_nodes, approved_edges, anchor_nodes


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

def _do_commit(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Commit payload to mrp_research via the stager → librarian gated path."""
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import mrp_terminology_stager as stager  # noqa: E402 — lazy import
    return stager.commit_payload(payload)


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------

def _print_decision_table(csv_rows: List[Dict[str, str]], mode: str) -> None:
    """Print a human-readable per-term decision table to stdout."""
    if not csv_rows:
        return
    col_w = max(len(r.get("term", "")) for r in csv_rows) + 2
    header_line = f"{'Term':<{col_w}} {'Decision':<10} {'Anchored'}"
    separator = "=" * (len(header_line) + 2)
    print(f"\n{separator}")
    print(f"  {mode}")
    print(separator)
    print(f"  {header_line}")
    print(f"  {'-' * len(header_line)}")
    for row in csv_rows:
        term = row.get("term", "")
        decision = (row.get("reviewer_decision") or "proposed").strip() or "proposed"
        anchored = row.get("anchored", "")
        if decision == "approved":
            marker = "+"
        elif decision == "rejected":
            marker = "-"
        else:
            marker = "·"
        print(f"  {marker} {term:<{col_w}} {decision:<10} {anchored}")
    print()


# ---------------------------------------------------------------------------
# Main run function (importable for tests)
# ---------------------------------------------------------------------------

def run(
    run_dir: Path,
    commit: bool = False,
) -> Dict[str, Any]:
    """Load a staging run, validate decisions, filter approved terms, optionally commit.

    Returns a summary dict with decision counts and commit result (if committed).
    Does NOT write to any database unless commit=True AND MRP_ENABLE_GRAPH_COMMIT=true.
    """
    csv_rows = _load_csv(run_dir)
    payload = _load_json(run_dir)

    _validate_decisions(csv_rows)

    approved_nodes, approved_edges, anchor_nodes = _filter_payload(
        csv_rows, payload["nodes"], payload["edges"]
    )

    counts: Dict[str, int] = {"approved": 0, "rejected": 0, "proposed": 0}
    for row in csv_rows:
        raw = (row.get("reviewer_decision") or "proposed").strip().lower()
        key = raw if raw in counts else "proposed"
        counts[key] += 1

    summary: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "terms_in_csv": len(csv_rows),
        "approved": counts["approved"],
        "rejected": counts["rejected"],
        "pending_review": counts["proposed"],
        "edges_included": len(approved_edges),
        "anchor_nodes_included": len(anchor_nodes),
        "committed": False,
        "dry_run": not commit,
    }

    if not approved_nodes:
        logger.info(
            "No approved terms in %s — nothing to commit "
            "(approved=%d, rejected=%d, pending=%d).",
            run_dir.name,
            counts["approved"],
            counts["rejected"],
            counts["proposed"],
        )
        return summary

    commit_payload_data: Dict[str, Any] = {
        "nodes": approved_nodes + anchor_nodes,
        "edges": approved_edges,
    }

    if commit:
        logger.info(
            "Committing %d approved term(s) + %d anchor node(s), %d edge(s) to mrp_research.",
            len(approved_nodes),
            len(anchor_nodes),
            len(approved_edges),
        )
        result = _do_commit(commit_payload_data)
        summary["committed"] = True
        summary["dry_run"] = False
        summary["commit_result"] = result
        logger.info("Commit complete: %s", result)
    else:
        logger.info(
            "DRY RUN: would commit %d approved term(s) + %d anchor node(s), "
            "%d edge(s). Pass --commit to write to mrp_research.",
            len(approved_nodes),
            len(anchor_nodes),
            len(approved_edges),
        )

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Commit SME-approved proposed terms from a staging run into the "
            "mrp_research ArangoDB graph (the intermediate research sandbox). "
            "Default is a DRY RUN — use --commit to write."
        )
    )
    parser.add_argument(
        "--run-id",
        default=None,
        metavar="YYYYMMDDTHHMMSSZ",
        help=(
            "Staging run ID to process (folder name under staging root). "
            "Defaults to the most recent run."
        ),
    )
    parser.add_argument(
        "--staging-root",
        default=str(DEFAULT_STAGING_ROOT),
        help=f"Staging root folder (default: {DEFAULT_STAGING_ROOT})",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help=(
            "Write approved terms to the mrp_research graph. "
            "Also requires MRP_ENABLE_GRAPH_COMMIT=true in the environment."
        ),
    )
    parser.add_argument(
        "--no-table",
        action="store_true",
        help="Suppress the per-term decision table (JSON summary output only).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    staging_root = Path(args.staging_root).expanduser()
    run_dir = _resolve_run_dir(args.run_id, staging_root)

    if not args.no_table:
        try:
            csv_rows = _load_csv(run_dir)
            mode = "COMMIT MODE" if args.commit else "DRY RUN (pass --commit to write)"
            _print_decision_table(csv_rows, mode)
        except FileNotFoundError:
            pass

    summary = run(run_dir=run_dir, commit=args.commit)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
