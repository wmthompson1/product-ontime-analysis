"""write_parity_reports.py — regenerate both parity reports + CSVs (cross-platform).

This is a single Python entry point that runs the same two parity checks
``scripts/post-merge.sh`` runs, with the same ``--report-file`` / ``--csv-dir``
flags — but as plain Python so it behaves identically on Windows (the private
repo) without needing bash:

    python replit_integrations/write_parity_reports.py

It runs, in order:
  1. SQL (SQLite ``sql_graph_*`` tables) <-> ``graph_metadata.json``
     (``sql_graph_parity_check.py``)
  2. SQL (SQLite ``sql_graph_*`` tables) <-> live ArangoDB graph
     (``sql_aql_parity_check.py`` with ``--skip-on-missing``)

Each check writes a human-readable ``.txt`` report and columnar per-record CSVs
into ``replit_integrations/`` (the checkers clear the CSVs up front, so a CSV's
presence still means "fresh successful dump from this run").

Exit codes:
    0  — every check passed (a skipped AQL check, e.g. ArangoDB unreachable,
         counts as a pass)
    1  — one or more checks reported a real parity mismatch / error
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SQL_GRAPH_REPORT = os.path.join(HERE, "sql_graph_parity_report.txt")
SQL_AQL_REPORT = os.path.join(HERE, "sql_aql_parity_report.txt")


def _checks(db: str | None) -> list[dict]:
    """Build the check list, forwarding an optional --db override to both."""
    db_args = ["--db", db] if db else []
    return [
        {
            "name": "SQL <-> graph_metadata.json",
            "script": os.path.join(HERE, "sql_graph_parity_check.py"),
            "args": [
                *db_args,
                "--report-file", SQL_GRAPH_REPORT,
                "--csv-dir", HERE,
            ],
        },
        {
            "name": "SQL <-> live ArangoDB (AQL)",
            "script": os.path.join(HERE, "sql_aql_parity_check.py"),
            "args": [
                *db_args,
                "--skip-on-missing",
                "--report-file", SQL_AQL_REPORT,
                "--csv-dir", HERE,
            ],
        },
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        default=None,
        help="Override path to manufacturing.db; forwarded to both parity checks "
        "(defaults to each check's own default when omitted).",
    )
    ns = parser.parse_args(argv)

    overall = 0
    for check in _checks(ns.db):
        print(f"\n=== {check['name']} ===", flush=True)
        cmd = [sys.executable, check["script"], *check["args"]]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(
                f"[write_parity_reports] FAIL — {check['name']} "
                f"(exit {result.returncode})"
            )
            overall = 1
        else:
            print(f"[write_parity_reports] OK — {check['name']}")

    if overall == 0:
        print(
            "\n[write_parity_reports] all parity reports written OK\n"
            f"  - {SQL_GRAPH_REPORT}\n"
            f"  - {SQL_AQL_REPORT}"
        )
    else:
        print("\n[write_parity_reports] one or more parity checks FAILED")
    return overall


if __name__ == "__main__":
    sys.exit(main())
