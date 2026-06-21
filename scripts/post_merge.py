#!/usr/bin/env python3
"""Cross-platform Python port of scripts/post-merge.sh.

Runs the same post-merge gate as scripts/post-merge.sh — the dependency
installs, the sql_graph_* self-heal, and the full ordered test / parity battery
— so the gate runs identically on Windows (or anywhere without bash). It exits
non-zero on the first failing step, mirroring `set -e`.

Keep this file in lockstep with scripts/post-merge.sh: any step that is added,
removed, or reordered there must be mirrored here (see STEPS below), and vice
versa.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _target_python() -> str:
    base = REPO_ROOT / ".pythonlibs"
    cand = base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(cand) if cand.is_file() else sys.executable


PY = _target_python()


def _exists(rel: str) -> bool:
    return (REPO_ROOT / rel).is_file()


def _run(cmd: list[str], **kwargs) -> int:
    return subprocess.run(cmd, cwd=str(REPO_ROOT), **kwargs).returncode


def _die(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def _run_or_die(cmd: list[str], message: str) -> None:
    if _run(cmd) != 0:
        _die(message)


def _pip_install() -> None:
    for req in ("requirements.txt", "hf-space-inventory-sqlgen/requirements.txt"):
        if not _exists(req):
            continue
        try:
            _run(["uv", "pip", "install", "--quiet", "--python", PY, "-r", req])
        except FileNotFoundError:
            print(
                "post-merge: 'uv' not found on PATH — skipping dependency install",
                file=sys.stderr,
            )
            return


def _self_heal_sql_graph_tables() -> None:
    app_db = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"
    required = (
        "replit_integrations/seed_elevations.py",
        "replit_integrations/export_graph_metadata.py",
        "replit_integrations/sql_graph_parity_check.py",
    )
    if not (_exists(app_db) and all(_exists(p) for p in required)):
        return

    already_in_parity = (
        _run(
            [PY, "replit_integrations/sql_graph_parity_check.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        == 0
    )
    if already_in_parity:
        return

    print(
        "post-merge: sql_graph_* tables are stale vs committed "
        "graph_metadata.json — re-materializing"
    )
    gm_json = REPO_ROOT / "replit_integrations/graph_metadata.json"
    gm_bak: str | None = None
    if gm_json.is_file():
        fd, gm_bak = tempfile.mkstemp(prefix="graph_metadata.", suffix=".json.bak")
        os.close(fd)
        shutil.copy(gm_json, gm_bak)
    try:
        _run_or_die(
            [PY, "replit_integrations/seed_elevations.py"],
            "post-merge: seed_elevations regeneration failed",
        )
        _run_or_die(
            [PY, "replit_integrations/export_graph_metadata.py"],
            "post-merge: export_graph_metadata regeneration failed",
        )
    finally:
        if gm_bak and os.path.isfile(gm_bak):
            shutil.copy(gm_bak, gm_json)
            os.remove(gm_bak)


STEPS: list[tuple[str, list[str], str]] = [
    ("hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py", [],
     "post-merge: perspective deprecation regression failed"),
    ("hf-space-inventory-sqlgen/scripts/check_legacy_perspective_refs.py", [],
     "post-merge: legacy perspective grep gate failed"),
    ("hf-space-inventory-sqlgen/scripts/check_legacy_elevates_refs.py", [],
     "post-merge: legacy elevates (v16 resolves_to rename) grep gate failed"),
    ("hf-space-inventory-sqlgen/tests/test_sync_db_to_dab_config.py", [],
     "post-merge: DAB sync tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py", [],
     "post-merge: field description pipeline tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_metric_assembly.py", [],
     "post-merge: metric assembly tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_get_resolves_to.py", [],
     "post-merge: get_resolves_to endpoint tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_db_init_self_heal.py", [],
     "post-merge: DB init self-heal tests failed"),
    ("replit_integrations/field_description_coverage_check.py", [],
     "post-merge: field description graph coverage check failed"),
    ("hf-space-inventory-sqlgen/tests/test_masking_policy_pipeline.py", [],
     "post-merge: masking policy pipeline tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_sync_masking_to_dab_config.py", [],
     "post-merge: masking DAB sync tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_masking_matrix.py", [],
     "post-merge: masking matrix tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_masking_type.py", [],
     "post-merge: masking type tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_reconstruct_containment_graph.py", [],
     "post-merge: graph reconstructor tests failed"),
    ("scripts/verify_metadata_meaning.py",
     ["--skip-on-no-arango", "--allow-sweep1-gaps"],
     "post-merge: metadata meaning verification failed"),
    ("hf-space-inventory-sqlgen/tests/test_sweep1_coverage_gaps.py", [],
     "post-merge: sweep1 coverage gap tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_approved_snippets_execute.py", [],
     "post-merge: approved snippet execution tests failed"),
    ("tests/test_semantic_scaffolding.py", [],
     "post-merge: semantic scaffolding format-lock tests failed"),
    ("tests/test_sql_graph_tables.py", [],
     "post-merge: SQL graph source table tests failed"),
    ("tests/test_authored_edges_merge.py", [],
     "post-merge: SME-authored edge merge tests failed"),
    ("hf-space-inventory-sqlgen/tests/test_commit_edge_sqlite_first.py", [],
     "post-merge: SQLite-first canonical edge authoring tests failed"),
    ("replit_integrations/sql_graph_parity_check.py",
     ["--report-file", "replit_integrations/sql_graph_parity_report.txt",
      "--csv-dir", "replit_integrations"],
     "post-merge: SQLite <-> graph_metadata.json parity check failed"),
    ("tests/test_sql_aql_parity.py", [],
     "post-merge: SQL vs AQL parity tests failed"),
    ("replit_integrations/sql_aql_parity_check.py",
     ["--skip-on-missing",
      "--report-file", "replit_integrations/sql_aql_parity_report.txt",
      "--csv-dir", "replit_integrations"],
     "post-merge: SQLite <-> live ArangoDB (SQL vs AQL) parity check failed"),
]


def main() -> None:
    _pip_install()
    _self_heal_sql_graph_tables()
    for rel, args, message in STEPS:
        if _exists(rel):
            _run_or_die([PY, rel, *args], message)
    print("post-merge: OK")


if __name__ == "__main__":
    main()
