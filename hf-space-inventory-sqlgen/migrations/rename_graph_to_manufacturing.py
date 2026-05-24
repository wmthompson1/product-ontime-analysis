"""One-shot migration: drop the semantic_graph named-graph wrapper and
recreate it as manufacturing_graph.

This migration fixes the naming drift introduced when graph_sync.py
hardcoded GRAPH_NAME = "semantic_graph" instead of reading from ARANGO_DB.
The correct name for both the database and the named graph is the value
of the ARANGO_DB env var — manufacturing_graph in production.

What this script does:
  1. Connects to ArangoDB using graph_sync helpers (inherits .strip() fix).
  2. Drops the "semantic_graph" named-graph wrapper if it exists
     (drop_collections=False — all vertex/edge collections are preserved).
  3. Calls sync_graph(dry_run=False) to recreate the wrapper under the
     name derived from ARANGO_DB (manufacturing_graph).
  4. Prints a before/after graph list so the result is visible in logs.

Safe to run multiple times — if semantic_graph is already gone and
manufacturing_graph already exists, the sync is a no-op.

Usage:
    python hf-space-inventory-sqlgen/migrations/rename_graph_to_manufacturing.py
    python hf-space-inventory-sqlgen/migrations/rename_graph_to_manufacturing.py --dry-run
"""

from __future__ import annotations

import os
import sys
import argparse

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(THIS_DIR)
if HF_DIR not in sys.path:
    sys.path.insert(0, HF_DIR)


def run(dry_run: bool = False) -> None:
    from graph_sync import get_arango_client, get_arango_db, sync_graph, GRAPH_NAME

    client = get_arango_client()
    db = get_arango_db(client)

    existing_graphs = [g["name"] for g in db.graphs()]
    print("Graphs before migration:", existing_graphs)

    if dry_run:
        print("\nDRY RUN — no changes will be written.")
        if "semantic_graph" in existing_graphs:
            print("  Would drop:    semantic_graph (collections preserved)")
        else:
            print("  semantic_graph not present — nothing to drop.")
        print(f"  Would ensure:  {GRAPH_NAME} (via sync_graph)")
        return

    # 1. Drop the stale semantic_graph wrapper (keep all collections)
    if "semantic_graph" in existing_graphs:
        print("\nDropping semantic_graph named-graph wrapper (collections preserved)...")
        db.delete_graph("semantic_graph", drop_collections=False)
        print("  Done.")
    else:
        print("\nsemantic_graph not present — skipping drop.")

    # 2. Re-create the wrapper under the correct name via a live sync
    print(f"\nRunning live sync to create/update '{GRAPH_NAME}' named graph...")
    report = sync_graph(dry_run=False)
    print(report.summary())

    # 3. Verify
    graphs_after = [g["name"] for g in db.graphs()]
    print("\nGraphs after migration:", graphs_after)

    if "semantic_graph" in graphs_after:
        print("WARNING: semantic_graph still present!")
        sys.exit(1)
    if GRAPH_NAME not in graphs_after:
        print(f"ERROR: {GRAPH_NAME} not found after sync!")
        sys.exit(1)

    print(f"\nSUCCESS: only '{GRAPH_NAME}' exists as a named graph.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
