"""Grep gate: fail if the CANONICAL column->concept predicate reverts to the
retired ``elevates`` / ``ELEVATES`` token after the v16 rename to ``resolves_to``.

Background
----------
v16 renamed ONLY the canonical (Model B) column->concept semantic predicate:

    stored edge_type   elevates    -> resolves_to
    display/predicate  ELEVATES    -> RESOLVES_TO
    uid abbreviation   ELE         -> RES

The legacy (Model A) intent->concept binding model — the ArangoDB ``elevates``
edge collection, its ``ELEVATES`` relationship label, and all the SME-binding
prose around it — is a SEPARATE, still-live surface and is deliberately LEFT
INTACT. This gate must never flag Model A.

Two checks
----------
1. Whole-token scan (``\\belevates\\b`` / ``\\bELEVATES\\b``) over an explicit
   list of pure Model-B source/test files. After the rename these must contain
   zero standalone ``elevates`` / ``ELEVATES`` tokens. The whole-word boundary
   intentionally does NOT match kept identifiers like ``EDGE_PREDICATE_ELEVATES``,
   ``_build_elevates_edges``, ``semantic_elevations_skipped``, the ``ElevatesRepoint``
   class, ``PAY_RES`` uids, or title-case ``Elevates`` (the leading/trailing ``_``
   or differing case breaks the boundary / literal).
   A small allow-list permits the deliberate pre-M2 *legacy-shape* DDL fixture.

2. Canonical-token scan over the files where Model A and Model B coexist
   (``app.py``, ``schema_sqlite.sql``). A blanket whole-token scan there would
   false-positive on legitimate Model-A prose / collection handles, so instead we
   match only the two shapes that would reintroduce the *canonical* token:
     * a ``CHECK(edge_type IN (... 'elevates' ...))`` DDL constraint, and
     * a canonical authored ``edge_type = "elevates"`` / ``edge_type='elevates'``
       assignment.
   Model A uses neither shape (it routes through the ``elevates`` Arango
   collection name, never the SQLite ``edge_type`` column).

Exit code 0 means no regression; non-zero means the canonical token crept back.
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Check 1: whole-token scan over pure Model-B files ─────────────────────────
# Explicit include list (not a tree walk) so Model-A files that legitimately keep
# the legacy token are simply never scanned.
MODEL_B_FILES = [
    "replit_integrations/export_graph_metadata.py",
    "replit_integrations/seed_elevations.py",
    "replit_integrations/sql_graph_parity_check.py",
    "replit_integrations/sql_aql_parity_check.py",
    "tests/test_semantic_scaffolding.py",
    "tests/test_sql_graph_tables.py",
    "tests/test_sql_aql_parity.py",
    "tests/test_authored_edges_merge.py",
    "hf-space-inventory-sqlgen/migrations/add_sql_graph_tables.py",
    "hf-space-inventory-sqlgen/tests/test_commit_edge_sqlite_first.py",
    "hf-space-inventory-sqlgen/tests/test_commit_edge_duplicate.py",
    "hf-space-inventory-sqlgen/tests/test_commit_edge_success.py",
]

WHOLE_TOKEN_PATTERN = re.compile(r"\b(?:elevates|ELEVATES)\b")

# Lines permitted to contain the whole token, keyed by repo-relative path. The
# value is a list of substrings; a hit on a line that contains any of them is
# ignored. Used for deliberately preserved legacy-shape fixtures.
ALLOWED_LINE_SUBSTRINGS: dict[str, list[str]] = {
    # Pre-M2 (<= v13) legacy-shape DDL fixture: it intentionally carries the OLD
    # edge_type CHECK so the staleness/rebuild path can be exercised.
    "tests/test_sql_graph_tables.py": [
        "CHECK(edge_type IN ('has_column', 'references', 'elevates'))",
    ],
}

# ── Check 2: canonical-token scan over Model-A/Model-B mixed files ─────────────
MIXED_FILES = [
    "hf-space-inventory-sqlgen/app_schema/schema_sqlite.sql",
    "hf-space-inventory-sqlgen/app.py",
]

CANONICAL_TOKEN_PATTERNS = [
    # CHECK(edge_type IN (... 'elevates' ...)) — canonical DDL constraint
    re.compile(r"CHECK\s*\(\s*edge_type\s+IN\s*\([^)]*'elevates'", re.IGNORECASE),
    # edge_type = "elevates" / edge_type='elevates' — canonical authored assignment
    re.compile(r"""edge_type\s*=\s*["']elevates["']"""),
]

# Lines in the mixed files permitted to mention the legacy token, keyed by
# repo-relative path. Used for the one-time boot-guard that *migrates* an old
# DB by translating the legacy edge_type value to the v16 token.
ALLOWED_MIXED_LINE_SUBSTRINGS: dict[str, list[str]] = {
    # _migrate_edge_type_check(): rebuilds a pre-v16 edge table and translates
    # legacy edge_type values forward. It must name the old token to convert it.
    "hf-space-inventory-sqlgen/app.py": [
        "CASE WHEN edge_type='elevates' THEN 'resolves_to'",
    ],
}


def _read_lines(rel: str) -> list[str] | None:
    full = os.path.join(REPO_ROOT, rel)
    if not os.path.isfile(full):
        return None
    try:
        with open(full, "r", encoding="utf-8") as fh:
            return fh.readlines()
    except (OSError, UnicodeDecodeError):
        return None


def scan_model_b() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for rel in MODEL_B_FILES:
        lines = _read_lines(rel)
        if lines is None:
            continue
        allowed = ALLOWED_LINE_SUBSTRINGS.get(rel, [])
        for lineno, line in enumerate(lines, start=1):
            if not WHOLE_TOKEN_PATTERN.search(line):
                continue
            if any(sub in line for sub in allowed):
                continue
            hits.append((rel, lineno, line.rstrip()))
    return hits


def scan_mixed() -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for rel in MIXED_FILES:
        lines = _read_lines(rel)
        if lines is None:
            continue
        allowed = ALLOWED_MIXED_LINE_SUBSTRINGS.get(rel, [])
        for lineno, line in enumerate(lines, start=1):
            if not any(pat.search(line) for pat in CANONICAL_TOKEN_PATTERNS):
                continue
            if any(sub in line for sub in allowed):
                continue
            hits.append((rel, lineno, line.rstrip()))
    return hits


def main() -> int:
    failed = 0

    b_hits = scan_model_b()
    if b_hits:
        failed += 1
        print("FAIL: canonical 'elevates'/'ELEVATES' token found in Model-B files "
              "(v16 renamed it to 'resolves_to'/'RESOLVES_TO'):")
        for path, lineno, line in b_hits:
            print(f"  {path}:{lineno}: {line}")
    else:
        print("OK: no canonical 'elevates'/'ELEVATES' tokens in Model-B files.")

    m_hits = scan_mixed()
    if m_hits:
        failed += 1
        print("FAIL: canonical edge_type 'elevates' reintroduced in a mixed "
              "Model-A/Model-B file (use 'resolves_to'):")
        for path, lineno, line in m_hits:
            print(f"  {path}:{lineno}: {line}")
    else:
        print("OK: no canonical edge_type 'elevates' in mixed files.")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
