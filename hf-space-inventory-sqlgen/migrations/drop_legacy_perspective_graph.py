"""One-shot migration: drop the legacy perspective graph from ArangoDB.

Drops the retired surfaces from the `manufacturing_graph` (or whatever
ARANGO_DB points to):
    - `perspectives`     vertex collection
    - `operates_within`  edge collection
    - `uses_definition`  edge collection

Replacement model: Perspective is a property on bridge rows in
`Perspective_Intents` and `Perspective_Concepts` document collections,
written by `graph_sync.py`. Resolvers read those bridge rows directly.

Safety:
    1. Pre-flight grep gate. If any consumer still references the legacy
       surfaces (per scripts/check_legacy_perspective_refs.py), this
       migration refuses to run.
    2. Idempotent. Safe to run multiple times — a missing collection is
       treated as already-dropped, not an error.

Usage:
    python -m hf-space-inventory-sqlgen.migrations.drop_legacy_perspective_graph
    python hf-space-inventory-sqlgen/migrations/drop_legacy_perspective_graph.py --dry-run
"""

from __future__ import annotations

import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(THIS_DIR)
REPO_ROOT = os.path.dirname(HF_DIR)
if HF_DIR not in sys.path:
    sys.path.insert(0, HF_DIR)
if os.path.join(HF_DIR, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(HF_DIR, "scripts"))

LEGACY_VERTEX_COLLECTIONS = ["perspectives"]
LEGACY_EDGE_COLLECTIONS = ["operates_within", "uses_definition"]
GRAPH_NAME = "semantic_graph"


def _run_grep_gate() -> bool:
    import check_legacy_perspective_refs as gate
    hits = gate.scan()
    if hits:
        print("ABORTED: legacy perspective references still present in the codebase.")
        for path, lineno, line in hits:
            print(f"  {path}:{lineno}: {line}")
        return False
    print("Grep gate OK: no fresh references to retired surfaces.")
    return True


def _drop_from_graph(db, graph, name: str) -> str:
    if not db.has_collection(name):
        return f"  {name}: already absent (skipped)"
    try:
        existing_edge_defs = {ed["edge_collection"] for ed in graph.edge_definitions()}
        if name in existing_edge_defs:
            graph.delete_edge_definition(name, purge=True)
            return f"  {name}: edge definition removed (purged collection)"
    except Exception as e:
        return f"  {name}: edge definition delete failed: {e}"

    try:
        props = graph.properties()
        orphans = props.get("orphan_collections", [])
        if name in orphans:
            graph.delete_vertex_collection(name, purge=True)
            return f"  {name}: orphan vertex collection removed (purged)"
    except Exception as e:
        return f"  {name}: orphan vertex collection remove failed: {e}"

    try:
        db.delete_collection(name)
        return f"  {name}: collection dropped"
    except Exception as e:
        return f"  {name}: drop failed: {e}"


def main() -> int:
    dry = "--dry-run" in sys.argv

    print("=" * 60)
    print("MIGRATION: drop legacy perspective graph")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry else 'LIVE'}")
    print()

    if not _run_grep_gate():
        return 2

    if dry:
        print("DRY RUN — would drop the following collections (if present):")
        for n in LEGACY_EDGE_COLLECTIONS + LEGACY_VERTEX_COLLECTIONS:
            print(f"  {n}")
        return 0

    try:
        from graph_sync import get_arango_client, get_arango_db
    except Exception as e:
        print(f"FAILED to import ArangoDB helpers: {e}")
        return 3

    try:
        client = get_arango_client()
        db = get_arango_db(client)
    except Exception as e:
        print(f"FAILED to connect to ArangoDB: {e}")
        return 4

    if db.has_graph(GRAPH_NAME):
        graph = db.graph(GRAPH_NAME)
    else:
        graph = None
        print(f"Note: graph '{GRAPH_NAME}' not present; will drop standalone collections only.")

    print("Dropping legacy edge collections:")
    for name in LEGACY_EDGE_COLLECTIONS:
        if graph is not None:
            print(_drop_from_graph(db, graph, name))
        else:
            if db.has_collection(name):
                try:
                    db.delete_collection(name)
                    print(f"  {name}: collection dropped")
                except Exception as e:
                    print(f"  {name}: drop failed: {e}")
            else:
                print(f"  {name}: already absent (skipped)")

    print("Dropping legacy vertex collections:")
    for name in LEGACY_VERTEX_COLLECTIONS:
        if graph is not None:
            print(_drop_from_graph(db, graph, name))
        else:
            if db.has_collection(name):
                try:
                    db.delete_collection(name)
                    print(f"  {name}: collection dropped")
                except Exception as e:
                    print(f"  {name}: drop failed: {e}")
            else:
                print(f"  {name}: already absent (skipped)")

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
