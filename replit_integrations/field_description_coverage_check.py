"""Coverage gate: every canonical-graph column node has a committed description.

File-vs-file (DB-independent, CI-safe): proves the committed
``field_descriptions.csv`` describes every ``node_type == "column"`` node in
``replit_integrations/graph_metadata.json`` with a non-empty description, and
carries no rows for columns that are not graph nodes.

Exit 0 when coverage is exact; exit 1 (with a report) otherwise. Run:

    python replit_integrations/field_description_coverage_check.py
"""
from __future__ import annotations

import os
import sys

_HF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hf-space-inventory-sqlgen",
)
if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)


def main(argv=None) -> int:
    from field_description_pipeline import (
        DEFAULT_CSV_PATH,
        DEFAULT_GRAPH_METADATA_PATH,
        compute_graph_coverage,
    )

    if not os.path.exists(DEFAULT_CSV_PATH):
        print(f"FAIL: field_descriptions.csv not found at {DEFAULT_CSV_PATH}")
        return 1

    cov = compute_graph_coverage(DEFAULT_CSV_PATH, DEFAULT_GRAPH_METADATA_PATH)
    total = cov["total"]
    described = cov["described"]
    missing = cov["missing"]
    extra = cov["extra"]
    duplicates = cov["duplicates"]

    print(
        f"field-description coverage: {described}/{total} graph column nodes "
        f"described."
    )
    if missing:
        print(f"FAIL: {len(missing)} graph column(s) missing a description:")
        for tbl, col in missing[:25]:
            print(f"  - {tbl}.{col}")
        if len(missing) > 25:
            print(f"  ... and {len(missing) - 25} more")
    if extra:
        print(f"FAIL: {len(extra)} CSV row(s) are not graph column nodes:")
        for tbl, col in extra[:25]:
            print(f"  - {tbl}.{col}")
        if len(extra) > 25:
            print(f"  ... and {len(extra) - 25} more")
    if duplicates:
        print(f"FAIL: {len(duplicates)} duplicate CSV key(s):")
        for tbl, col in duplicates[:25]:
            print(f"  - {tbl}.{col}")
        if len(duplicates) > 25:
            print(f"  ... and {len(duplicates) - 25} more")

    if missing or extra or duplicates:
        return 1
    print("PASS: field_descriptions.csv covers every graph column node exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
