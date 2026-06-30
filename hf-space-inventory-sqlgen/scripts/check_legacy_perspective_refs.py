"""Grep gate: fail if any consumer references the retired perspective graph paths
or hardcodes the legacy graph name "semantic_graph".

Retired surfaces:
    - `perspectives` vertex collection (ArangoDB)
    - `operates_within` edge collection (ArangoDB)
    - `uses_definition` edge collection (ArangoDB)
    - hardcoded graph name string literal "semantic_graph" (use ARANGO_DB env var)

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

# Files that are allowed to reference the legacy collection names (docs,
# migration, this gate script itself, deprecation guards, regression test).
ALLOWED_PATHS = {
    os.path.relpath(__file__, REPO_ROOT),
    "hf-space-inventory-sqlgen/migrations/drop_legacy_perspective_graph.py",
    "hf-space-inventory-sqlgen/graph_sync.py",  # LEGACY_* constants for guard
    "hf-space-inventory-sqlgen/semantic_reasoning.py",  # deprecation note
    "hf-space-inventory-sqlgen/tests/test_perspective_deprecation.py",
}

# ── Hardcoded graph-name guard ────────────────────────────────────────────────
# Any file outside migrations/ that contains the bare string literal
# "semantic_graph" or 'semantic_graph' is using the old hard-coded name
# instead of reading from the ARANGO_DB environment variable.
HARDCODED_GRAPH_NAME_PATTERN = re.compile(r"""["']semantic_graph["']""")

# Paths allowed to contain "semantic_graph" as a literal: migration history,
# and guard constants that list the legacy name precisely so research/scratch
# writes can NEVER target it (a forbidden-name list, not a connection target —
# mirrors the graph_sync.py "LEGACY_* constants for guard" allowance above).
HARDCODED_GRAPH_NAME_ALLOWED_PATHS = {
    os.path.relpath(__file__, REPO_ROOT),
    "hf-space-inventory-sqlgen/migrations/rename_graph_to_manufacturing.py",
    "scripts/librarian_server.py",  # CERTIFIED_DB_NAMES forbidden-name guard
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


def scan_hardcoded_graph_name() -> list[tuple[str, int, str]]:
    """Return every line outside migrations/ that hardcodes 'semantic_graph'.

    Scans:
      - hf-space-inventory-sqlgen/  (recursive)
      - scripts/  at repo root (recursive)
      - *.py files directly in the repo root (non-recursive) — #80
    """
    hits: list[tuple[str, int, str]] = []

    def _scan_file(full: str) -> None:
        rel = os.path.relpath(full, REPO_ROOT)
        if rel in HARDCODED_GRAPH_NAME_ALLOWED_PATHS:
            return
        parts = rel.replace(os.sep, "/").split("/")
        if "migrations" in parts:
            return
        try:
            with open(full, "r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if HARDCODED_GRAPH_NAME_PATTERN.search(line):
                        hits.append((rel, lineno, line.rstrip()))
        except (OSError, UnicodeDecodeError):
            pass

    # Recursive scan of HF Space directory and repo-root scripts/
    scan_roots = [
        HF_DIR,
        os.path.join(REPO_ROOT, "scripts"),
    ]
    for scan_root in scan_roots:
        if not os.path.isdir(scan_root):
            continue
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = [
                d for d in dirs
                if d not in {"__pycache__", "node_modules", ".git"}
            ]
            for f in files:
                if f.endswith(SCAN_EXTS):
                    _scan_file(os.path.join(root, f))

    # Non-recursive scan of root-level Python scripts (#80)
    for f in os.listdir(REPO_ROOT):
        if not f.endswith(SCAN_EXTS):
            continue
        full = os.path.join(REPO_ROOT, f)
        if os.path.isfile(full):
            _scan_file(full)

    return hits


def main() -> int:
    failed = 0

    hits = scan()
    if hits:
        failed += 1
        print("FAIL: found references to retired perspective graph surfaces:")
        for path, lineno, line in hits:
            print(f"  {path}:{lineno}: {line}")
    else:
        print("OK: no fresh references to retired perspective graph surfaces.")

    graph_hits = scan_hardcoded_graph_name()
    if graph_hits:
        failed += 1
        print('FAIL: found hardcoded "semantic_graph" string literals '
              "(use os.environ.get(\"ARANGO_DB\", \"manufacturing_graph\") instead):")
        for path, lineno, line in graph_hits:
            print(f"  {path}:{lineno}: {line}")
    else:
        print('OK: no hardcoded "semantic_graph" graph-name literals found.')

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
