"""
add_snippet_table_usage.py — index reviewer-manifest snippets into the
ground_truth_table_usage log.

The ground_truth_table_usage table is built by
SolderEngine.build_table_usage_index(), which only scans QUERIES_DIR
(app_schema/queries/*.sql). SME-approved snippets live in
app_schema/ground_truth/sql_snippets/ and are referenced from the reviewer
manifest, so the tables they touch (shop_resource, operation, receiving,
certification, work_order, purchase_order, suppliers) were never recorded.

This migration is idempotent: it upserts one row per
(binding_key, concept_anchor, table) for every APPROVED snippet, so it can be
re-run safely and survives database recreations.

Run from the hf-space-inventory-sqlgen directory:
    python migrations/add_snippet_table_usage.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from solder_engine import SolderEngine


def run() -> None:
    engine = SolderEngine()
    print("Indexing APPROVED reviewer-manifest snippets into "
          "ground_truth_table_usage…")
    summary = engine.index_snippet_table_usage(verbose=True)

    table_count = len({t for s in summary.values() for t in s["tables"]})
    row_count = sum(len(s["tables"]) for s in summary.values())
    print(f"\nDone — recorded {row_count} (snippet, table) rows for "
          f"{len(summary)} approved snippets across {table_count} distinct tables.")


if __name__ == "__main__":
    run()
