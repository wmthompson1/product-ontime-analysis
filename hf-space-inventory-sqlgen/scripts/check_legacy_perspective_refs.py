"""Grep gate: fail if any consumer references the retired perspective graph paths.

Retired surfaces:
    - `perspectives` vertex collection (ArangoDB)
    - `operates_within` edge collection (ArangoDB)
    - `uses_definition` edge collection (ArangoDB)

This script scans repository Python sources and known config files for
fresh references to those names. It allow-lists the locations where the
legacy names are *intentionally* preserved (this file, the migration
script, the deprecation comments, and SQLite-layer docs that mention the
old labels as historical context).

Exit code 0 means no fresh references; non-zero means a regression.
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HF_DIR = os.path.join(REPO_ROOT, "hf-space-inventory-sqlgen")

# We only care about ArangoDB *collection handle* usages — not API
# response dict keys, not docstrings, not the SQLite `schema_*` source
# tables. Match the specific access patterns that the retired Arango
# layer used:
#   graph.vertex_collection("perspectives")
#   graph.edge_collection("operates_within" | "uses_definition")
#   db.collection("perspectives" | "operates_within" | "uses_definition")
#   db.create_collection("...")
#   db.has_collection("...")
#   db.delete_collection("...")
#   string literal `perspectives/<key>` used as an Arango document id
LEGACY_COLLECTION_NAMES = ["perspectives", "operates_within", "uses_definition"]

_names_alt = "|".join(LEGACY_COLLECTION_NAMES)
LEGACY_PATTERNS = [
    rf'(?:vertex_collection|edge_collection|collection|create_collection|has_collection|delete_collection)\(\s*["\']({_names_alt})["\']',
    rf'["\'](?:{_names_alt})/[^"\']+["\']',  # Arango doc id like "perspectives/Quality"
]

# Files that are allowed to reference the legacy names (docs, migration,
# this gate script itself, deprecation guards, the regression test).
ALLOWED_PATHS = {
    os.path.relpath(__file__, REPO_ROOT),
    "hf-space-inventory-sqlgen/migrations/drop_legacy_perspective_graph.py",
    "hf-space-inventory-sqlgen/graph_sync.py",  # LEGACY_* constants for guard
    "hf-space-inventory-sqlgen/semantic_reasoning.py",  # deprecation note
    "hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py",
}

SCAN_EXTS = (".py",)


def scan() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    pattern = re.compile("|".join(LEGACY_PATTERNS))
    for root, dirs, files in os.walk(HF_DIR):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "node_modules", ".git"}]
        for f in files:
            if not f.endswith(SCAN_EXTS):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, REPO_ROOT)
            if rel in ALLOWED_PATHS:
                continue
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if pattern.search(line):
                            hits.append((rel, lineno, line.rstrip()))
            except (OSError, UnicodeDecodeError):
                continue
    return hits


def main() -> int:
    hits = scan()
    if not hits:
        print("OK: no fresh references to retired perspective graph surfaces.")
        return 0
    print("FAIL: found references to retired perspective graph surfaces:")
    for path, lineno, line in hits:
        print(f"  {path}:{lineno}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
