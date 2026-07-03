"""
scripts/mrp_term_promoter.py
Promotes SME-approved MRP research terms into the certified semantic layer.

Reads approved proposed_term nodes from a staging run's reviewed
``proposed_terms.csv`` (reviewer_decision == 'approved'), inserts them as
``schema_concepts`` rows (domain='MRP') into the certified SQLite
``manufacturing.db``, bumps SCHEMA_VERSION in ``export_graph_metadata.py``,
and re-runs the exporter to regenerate ``sql_graph_nodes``/``sql_graph_edges``
and ``graph_metadata.json``.

Governance (the "Solder Pattern"):
  * Only terms explicitly marked reviewer_decision='approved' are promoted.
    No bulk-approve shortcut; each term requires an explicit decision.
  * Default is a DRY RUN — prints a decision summary, touches no database or
    committed file.
  * Live writes require --commit AND MRP_ENABLE_GRAPH_COMMIT=true in the
    environment.  The same env guard used by mrp_approval_committer.py applies
    here so there is one canonical opt-in for the whole research pipeline.
  * INSERT OR IGNORE on concept_name (the UNIQUE constraint) makes promotion
    idempotent: re-running with the same staging run is safe.
  * Fails closed on any unrecognised reviewer_decision value rather than
    silently skipping terms.
  * The exporter re-run is always preceded by a SCHEMA_VERSION bump so the
    new canonical graph is versioned.  A concept_name that collides with a
    reserved exporter token causes an early hard stop (before any DB write).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("mrp_term_promoter")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

DB_PATH = _REPO_ROOT / "hf-space-inventory-sqlgen" / "app_schema" / "manufacturing.db"
EXPORT_SCRIPT = _REPO_ROOT / "replit_integrations" / "export_graph_metadata.py"
FIELD_COVERAGE_CHECK = _REPO_ROOT / "replit_integrations" / "field_description_coverage_check.py"

DEFAULT_STAGING_ROOT = Path(
    os.getenv("MRP_RESEARCH_STAGING_ROOT", str(_REPO_ROOT / "mrp_research_staging"))
).expanduser()

# Tokens that the canonical exporter reserves for its own key grammar.
# A concept whose name matches any of these would produce an invalid key.
_EXPORTER_RESERVED = frozenset(
    {"entity", "none", "system", "canonical", "structural", "semantic"}
)

VALID_DECISIONS: Set[str] = {"proposed", "approved", "rejected"}
DOMAIN_MRP = "MRP"

# ---------------------------------------------------------------------------
# Staging folder helpers (mirrors mrp_approval_committer.py)
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


def _resolve_run_dir(run_id: Optional[str], staging_root: Path) -> Path:
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
# Data loading & validation (mirrors mrp_approval_committer.py)
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
    if not isinstance(payload.get("nodes"), list) or not isinstance(
        payload.get("edges"), list
    ):
        raise ValueError(
            f"proposed_terms.json in {run_dir} must contain 'nodes' and 'edges' arrays"
        )
    return payload


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
                "Correct the CSV before running the promoter."
            )


# ---------------------------------------------------------------------------
# Filter & normalise approved nodes
# ---------------------------------------------------------------------------


def _filter_approved_terms(
    csv_rows: List[Dict[str, str]],
    json_nodes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Return (approved_term_nodes, rejected_names).

    Only proposed_term nodes whose CSV reviewer_decision is 'approved' are
    returned.  Anchor nodes are ignored — they mirror certified handles and are
    never inserted into schema_concepts.
    """
    term_by_name: Dict[str, Dict[str, Any]] = {}
    for node in json_nodes:
        if node.get("node_type") == "proposed_term":
            name = node.get("name") or node.get("term", "")
            if name:
                term_by_name[name] = node

    approved: List[Dict[str, Any]] = []
    rejected: List[str] = []
    for row in csv_rows:
        raw = (row.get("reviewer_decision") or "proposed").strip().lower()
        term_name = row.get("term", "").strip()
        if raw == "approved":
            node = term_by_name.get(term_name)
            if node:
                approved.append(node)
            else:
                logger.warning(
                    "Approved term '%s' not found in proposed_terms.json — skipping.",
                    term_name,
                )
        elif raw == "rejected":
            rejected.append(term_name)

    return approved, rejected


def _node_to_concept_row(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a proposed_term node dict into a schema_concepts insert payload.

    Fields mapped:
      name / term       → concept_name
      proposed_definition or document_definition → description
      acronym           → synonyms (JSON array with one entry if present)
      foundational      → tags (["foundational"] if true, else [])
      domain            → MRP (always, regardless of node content)
      concept_type      → "" (column exists but is deprecated)
      computation_template → NULL (MRP research terms are glossary nodes,
                              not metric templates)
    """
    name: str = (node.get("name") or node.get("term") or "").strip()
    if not name:
        raise ValueError(f"Proposed term node has no 'name' or 'term' field: {node}")

    # Prefer the document-extracted definition; fall back to the structured one.
    description: str = (
        (node.get("document_definition") or node.get("proposed_definition") or "")
        .strip()
    )

    acronym: str = (node.get("acronym") or "").strip()
    synonyms_list: List[str] = [acronym] if acronym else []

    foundational: bool = bool(node.get("foundational", False))
    tags_list: List[str] = ["foundational"] if foundational else []

    return {
        "concept_name": name,
        "description": description,
        "domain": DOMAIN_MRP,
        "concept_type": "",
        "synonyms": json.dumps(synonyms_list),
        "tags": json.dumps(tags_list),
        "computation_template": None,
        "parent_concept_id": None,
    }


# ---------------------------------------------------------------------------
# Reserved-token guard
# ---------------------------------------------------------------------------


def _check_reserved_names(concept_rows: List[Dict[str, Any]]) -> None:
    """Fail closed if any concept_name collides with an exporter reserved token.

    The canonical exporter's key grammar reserves a small set of tokens (e.g.
    'none', 'entity', 'system', 'canonical').  A concept whose name matches one
    of these would produce a malformed 6-slot key.  We check before any DB
    write so the failure is clean.
    """
    for row in concept_rows:
        name = row["concept_name"]
        if name.lower() in _EXPORTER_RESERVED:
            raise ValueError(
                f"Concept name '{name}' collides with a reserved exporter token "
                f"({sorted(_EXPORTER_RESERVED)}).  Rename the term before promoting."
            )


# ---------------------------------------------------------------------------
# SQLite promotion
# ---------------------------------------------------------------------------


def _check_existing_concepts(
    conn: sqlite3.Connection, concept_rows: List[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """Return (already_present, new_names) by querying schema_concepts."""
    names = [r["concept_name"] for r in concept_rows]
    placeholders = ", ".join("?" * len(names))
    rows = conn.execute(
        f"SELECT concept_name FROM schema_concepts WHERE concept_name IN ({placeholders})",
        names,
    ).fetchall()
    present = {r[0] for r in rows}
    already = [n for n in names if n in present]
    new = [n for n in names if n not in present]
    return already, new


def _insert_concepts(
    conn: sqlite3.Connection, concept_rows: List[Dict[str, Any]]
) -> int:
    """INSERT OR IGNORE concept rows into schema_concepts.  Returns count inserted."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    for row in concept_rows:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO schema_concepts
                (concept_name, description, domain, concept_type,
                 synonyms, tags, computation_template, parent_concept_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["concept_name"],
                row["description"],
                row["domain"],
                row["concept_type"],
                row["synonyms"],
                row["tags"],
                row["computation_template"],
                row["parent_concept_id"],
                now,
            ),
        )
        inserted += cur.rowcount
    return inserted


# ---------------------------------------------------------------------------
# SCHEMA_VERSION bump
# ---------------------------------------------------------------------------


def _read_current_schema_version(export_script: Path) -> int:
    """Parse the current SCHEMA_VERSION integer from export_graph_metadata.py."""
    text = export_script.read_text(encoding="utf-8")
    m = re.search(r"^SCHEMA_VERSION\s*=\s*(\d+)", text, re.MULTILINE)
    if not m:
        raise RuntimeError(
            f"Cannot find 'SCHEMA_VERSION = <int>' in {export_script}. "
            "Was the file modified by hand?"
        )
    return int(m.group(1))


def _bump_schema_version(
    export_script: Path,
    new_version: int,
    new_milestone: str,
) -> None:
    """Rewrite SCHEMA_VERSION and MILESTONE_NAME in export_graph_metadata.py."""
    text = export_script.read_text(encoding="utf-8")

    # Bump the integer.
    text = re.sub(
        r"^(SCHEMA_VERSION\s*=\s*)\d+",
        lambda m: f"{m.group(1)}{new_version}",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    # Update the milestone name.
    text = re.sub(
        r'^(MILESTONE_NAME\s*=\s*)"[^"]*"',
        lambda m: f'{m.group(1)}"{new_milestone}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )

    export_script.write_text(text, encoding="utf-8")
    logger.info(
        "Bumped SCHEMA_VERSION to %d, milestone '%s' in %s",
        new_version,
        new_milestone,
        export_script.name,
    )


# ---------------------------------------------------------------------------
# Exporter subprocess
# ---------------------------------------------------------------------------


def _run_exporter(export_script: Path) -> None:
    """Run export_graph_metadata.py as a subprocess; raise on failure."""
    logger.info("Running %s …", export_script.name)
    result = subprocess.run(
        [sys.executable, str(export_script)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"export_graph_metadata.py failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    logger.info("Exporter completed successfully.")
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            logger.debug("  exporter: %s", line)


def _run_coverage_check(coverage_script: Path) -> None:
    """Run field_description_coverage_check.py; warn (do not fail) if absent."""
    if not coverage_script.exists():
        logger.warning(
            "Coverage check script not found at %s — skipping.", coverage_script
        )
        return
    logger.info("Running field description coverage check …")
    result = subprocess.run(
        [sys.executable, str(coverage_script)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"field_description_coverage_check.py failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    logger.info("Coverage check passed.")


# ---------------------------------------------------------------------------
# Decision summary
# ---------------------------------------------------------------------------


def _print_decision_table(
    csv_rows: List[Dict[str, str]],
    already_present: List[str],
    mode: str,
) -> None:
    """Print a human-readable per-term decision table to stdout."""
    if not csv_rows:
        return
    col_w = max(len(r.get("term", "")) for r in csv_rows) + 2
    header_line = f"{'Term':<{col_w}} {'Decision':<10} {'Anchored':<8} {'Status'}"
    separator = "=" * (len(header_line) + 2)
    print(f"\n{separator}")
    print(f"  {mode}")
    print(separator)
    print(f"  {header_line}")
    print(f"  {'-' * len(header_line)}")
    present_set = set(already_present)
    for row in csv_rows:
        term = row.get("term", "")
        decision = (row.get("reviewer_decision") or "proposed").strip() or "proposed"
        anchored = row.get("anchored", "")
        if decision == "approved":
            marker = "+"
            status = "already in certified layer" if term in present_set else "will promote"
        elif decision == "rejected":
            marker = "-"
            status = "skip"
        else:
            marker = "·"
            status = "pending review"
        print(f"  {marker} {term:<{col_w}} {decision:<10} {anchored:<8} {status}")
    print()


# ---------------------------------------------------------------------------
# Main run function (importable for tests)
# ---------------------------------------------------------------------------


def run(
    run_dir: Path,
    commit: bool = False,
    db_path: Path = DB_PATH,
    export_script: Path = EXPORT_SCRIPT,
    coverage_check: Path = FIELD_COVERAGE_CHECK,
) -> Dict[str, Any]:
    """Load a staging run, validate decisions, promote approved terms.

    Returns a summary dict.  Does NOT write to any database or file unless
    commit=True AND MRP_ENABLE_GRAPH_COMMIT=true.

    Args:
        run_dir: Path to the staging run folder.
        commit: If True, perform actual writes (DB, exporter re-run).  Still
                requires the MRP_ENABLE_GRAPH_COMMIT env var.
        db_path: Path to the certified SQLite database (override for tests).
        export_script: Path to export_graph_metadata.py (override for tests).
        coverage_check: Path to field_description_coverage_check.py (override
                        for tests).
    """
    # --- Load & validate ---
    csv_rows = _load_csv(run_dir)
    payload = _load_json(run_dir)

    _validate_decisions(csv_rows)

    # Count decisions for summary
    decision_counts: Dict[str, int] = {"approved": 0, "rejected": 0, "proposed": 0}
    for row in csv_rows:
        raw = (row.get("reviewer_decision") or "proposed").strip().lower()
        key = raw if raw in decision_counts else "proposed"
        decision_counts[key] += 1

    # --- Filter approved proposed_term nodes ---
    approved_nodes, rejected_names = _filter_approved_terms(
        csv_rows, payload["nodes"]
    )

    # --- Convert to schema_concepts rows ---
    concept_rows: List[Dict[str, Any]] = []
    for node in approved_nodes:
        try:
            concept_rows.append(_node_to_concept_row(node))
        except ValueError as exc:
            logger.error("Skipping node due to mapping error: %s", exc)

    # --- Guard reserved token collisions (before any DB write) ---
    _check_reserved_names(concept_rows)

    summary: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "run_id": run_dir.name,
        "terms_in_csv": len(csv_rows),
        "approved": decision_counts["approved"],
        "rejected": decision_counts["rejected"],
        "pending_review": decision_counts["proposed"],
        "concepts_to_promote": len(concept_rows),
        "committed": False,
        "dry_run": not commit,
    }

    if not concept_rows:
        logger.info(
            "No approved terms to promote in %s "
            "(approved=%d, rejected=%d, pending=%d).",
            run_dir.name,
            decision_counts["approved"],
            decision_counts["rejected"],
            decision_counts["proposed"],
        )
        return summary

    # --- Pre-flight: report what already exists vs what is new ---
    conn_ro = sqlite3.connect(str(db_path))
    try:
        already_present, new_names = _check_existing_concepts(conn_ro, concept_rows)
    finally:
        conn_ro.close()

    summary["already_in_certified"] = already_present
    summary["new_concepts"] = new_names

    if not commit:
        logger.info(
            "DRY RUN: %d approved term(s) ready — %d new, %d already in certified layer.  "
            "Pass --commit to write.",
            len(concept_rows),
            len(new_names),
            len(already_present),
        )
        return summary

    # --- Guard the env var (same pattern as mrp_approval_committer.py) ---
    if os.environ.get("MRP_ENABLE_GRAPH_COMMIT", "").strip().lower() != "true":
        raise EnvironmentError(
            "Live promotion requires MRP_ENABLE_GRAPH_COMMIT=true in the environment. "
            "Set the variable and re-run with --commit."
        )

    # --- Determine new SCHEMA_VERSION ---
    current_version = _read_current_schema_version(export_script)
    new_version = current_version + 1
    new_milestone = "mrp_term_promotion"

    # --- Write to DB ---
    logger.info(
        "Promoting %d new concept(s) into schema_concepts (domain='%s') …",
        len(new_names),
        DOMAIN_MRP,
    )
    conn_rw = sqlite3.connect(str(db_path))
    try:
        inserted = _insert_concepts(conn_rw, concept_rows)
        conn_rw.commit()
    except Exception:
        conn_rw.rollback()
        raise
    finally:
        conn_rw.close()

    logger.info(
        "Inserted %d new concept row(s) (%d were already present, skipped by INSERT OR IGNORE).",
        inserted,
        len(already_present),
    )
    summary["inserted"] = inserted

    # --- Bump SCHEMA_VERSION and re-run exporter ---
    # Snapshot the file BEFORE any change so we can revert atomically if the
    # exporter subprocess fails.  The DB write is intentionally left in place on
    # failure — INSERT OR IGNORE makes re-promotion idempotent, so a subsequent
    # --commit run will skip the already-inserted rows and retry the export
    # cleanly without any manual cleanup.
    _export_script_original = export_script.read_text(encoding="utf-8")

    try:
        _bump_schema_version(export_script, new_version, new_milestone)
        summary["schema_version_bumped_to"] = new_version
        summary["milestone"] = new_milestone

        _run_exporter(export_script)
    except Exception as exc:
        # Restore the file so SCHEMA_VERSION stays in sync with the last
        # successfully committed graph_metadata.json snapshot.
        try:
            export_script.write_text(_export_script_original, encoding="utf-8")
            logger.warning(
                "Exporter failed — SCHEMA_VERSION reverted to %d in %s.",
                current_version,
                export_script.name,
            )
        except OSError as restore_err:
            logger.error(
                "SCHEMA_VERSION revert also failed (%s). "
                "Manually restore SCHEMA_VERSION = %d in %s before the next run.",
                restore_err,
                current_version,
                export_script,
            )
        raise RuntimeError(
            f"Promotion incomplete — exporter failed; SCHEMA_VERSION reverted to "
            f"{current_version}.\n\n"
            f"What happened:\n"
            f"  • {inserted} concept(s) were written to schema_concepts (they remain in the DB).\n"
            f"  • The SCHEMA_VERSION bump was rolled back so graph_metadata.json stays in\n"
            f"    sync with version {current_version} (the last clean snapshot).\n\n"
            f"Recovery — fix the exporter error, then re-run:\n"
            f"  MRP_ENABLE_GRAPH_COMMIT=true python scripts/mrp_term_promoter.py --commit\n"
            f"Re-running is safe: INSERT OR IGNORE will skip the already-inserted rows\n"
            f"and the exporter will run again against the complete concept set.\n\n"
            f"Original error:\n{exc}"
        ) from exc

    summary["export_ran"] = True

    # --- Verify field description coverage still passes ---
    _run_coverage_check(coverage_check)
    summary["coverage_check_passed"] = True

    summary["committed"] = True
    summary["dry_run"] = False

    logger.info(
        "Promotion complete: %d new concept(s) certified, SCHEMA_VERSION → %d.",
        inserted,
        new_version,
    )
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Promote SME-approved MRP research terms from a staging run into the "
            "certified semantic layer (schema_concepts + sql_graph_nodes + graph_metadata.json). "
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
            "Write approved terms into the certified layer. "
            "Also requires MRP_ENABLE_GRAPH_COMMIT=true in the environment."
        ),
    )
    parser.add_argument(
        "--no-table",
        action="store_true",
        help="Suppress the per-term decision table (JSON summary output only).",
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        help=f"Path to the certified SQLite database (default: {DB_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    staging_root = Path(args.staging_root).expanduser()
    run_dir = _resolve_run_dir(args.run_id, staging_root)
    db_path = Path(args.db)

    if not args.no_table:
        try:
            csv_rows = _load_csv(run_dir)
            payload = _load_json(run_dir)
            _validate_decisions(csv_rows)
            approved_nodes, _ = _filter_approved_terms(csv_rows, payload["nodes"])
            concept_rows = []
            for node in approved_nodes:
                try:
                    concept_rows.append(_node_to_concept_row(node))
                except ValueError:
                    pass
            conn = sqlite3.connect(str(db_path))
            try:
                already_present, _ = _check_existing_concepts(conn, concept_rows)
            finally:
                conn.close()
            mode = "COMMIT MODE" if args.commit else "DRY RUN (pass --commit to write)"
            _print_decision_table(csv_rows, already_present, mode)
        except (FileNotFoundError, ValueError):
            pass

    summary = run(run_dir=run_dir, commit=args.commit, db_path=db_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
