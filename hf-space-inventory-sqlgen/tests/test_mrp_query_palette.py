"""hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py

CI guard: catch a missing or empty SQL snippet before an MRP concept can
appear in the semantic graph yet return a comment stub from the Query Palette.

Covers:
  1. All three MRP manifest entries (REORDERPOINT, ONHANDQUANTITY, LEADTIME)
     are present in reviewer_manifest.json with validation_status=APPROVED.
  2. Each entry's file_path resolves to a real file on disk.
  3. Each resolved SQL file has non-empty content.
  4. SolderEngine.solder('inventory_planning') returns SQL that is NOT a
     comment stub (does not start with '--' or '/*').
  5. SolderEngine.solder('inventory_stock_status') returns real SQL.
  6. SolderEngine.resolve_by_binding_key() returns non-empty SQL for each
     of the three MRP binding keys directly.

Run: python hf-space-inventory-sqlgen/tests/test_mrp_query_palette.py
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)

sys.path.insert(0, HF_DIR)

from solder_engine import SolderEngine  # noqa: E402

MANIFEST_PATH = os.path.join(HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")
MANIFEST_DIR = os.path.dirname(MANIFEST_PATH)
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

MRP_CONCEPT_ANCHORS = ["REORDERPOINT", "ONHANDQUANTITY", "LEADTIME"]

MRP_BINDING_KEYS = {
    "REORDERPOINT": "inventory_reorderpoint_20260703_000001",
    "ONHANDQUANTITY": "inventory_onhandquantity_20260703_000002",
    "LEADTIME": "inventory_leadtime_20260703_000003",
}

MRP_INTENTS = [
    "inventory_planning",
    "inventory_stock_status",
]

# Batch 7: dataset-derived concepts — primary_binding_key on the intent row
# resolves directly; no schema_concept_fields column anchor.
DERIVED_CONCEPT_ANCHORS = ["AVAILABLETOPROMISE", "ALLOCATEDQUANTITY"]

DERIVED_BINDING_KEYS = {
    "AVAILABLETOPROMISE": "inventory_atp_20260703_000004",
    "ALLOCATEDQUANTITY":  "inventory_allocated_20260703_000005",
}

DERIVED_INTENTS = [
    "inventory_atp",
    "inventory_allocated_qty",
]


def _resolve_sql_path(file_path: str) -> str | None:
    """Resolve a manifest file_path to an absolute path on disk.

    Mirrors SolderEngine.load_approved_bindings() path-resolution order so the
    test and the engine stay in agreement about where snippets live.
    """
    if not file_path:
        return None
    candidates = [
        file_path if os.path.isabs(file_path) else None,
        os.path.join(MANIFEST_DIR, os.path.basename(file_path)),
        os.path.join(HF_DIR, file_path),
        os.path.join(REPO_ROOT, file_path),
        os.path.join(MANIFEST_DIR, file_path),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _is_comment_stub(sql: str) -> bool:
    """Return True if the SQL contains no real DML/DQL statement.

    Approved snippet files legitimately open with '--' comment headers before
    the SELECT.  A true stub is content that contains ONLY comments or is
    blank — no SELECT / WITH / INSERT keyword anywhere in the body.
    """
    stripped = (sql or "").strip()
    if not stripped:
        return True
    upper = stripped.upper()
    return not any(kw in upper for kw in ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE"))


# ---------------------------------------------------------------------------
# Manifest-level assertions (no DB needed)
# ---------------------------------------------------------------------------

def test_mrp_manifest_entries_are_approved():
    """All three MRP concept anchors have an APPROVED entry in the manifest."""
    manifest = _load_manifest()
    snippets = manifest.get("approved_snippets", {})

    approved_anchors = {
        entry["concept_anchor"].upper()
        for entry in snippets.values()
        if entry.get("validation_status") == "APPROVED"
    }

    missing = [anchor for anchor in MRP_CONCEPT_ANCHORS if anchor not in approved_anchors]
    assert not missing, (
        f"MRP concept anchor(s) missing from approved_snippets in reviewer_manifest.json: "
        f"{missing}. Add an APPROVED entry for each."
    )


def test_mrp_snippet_files_exist_on_disk():
    """Each MRP binding entry's file_path resolves to a file that exists on disk."""
    manifest = _load_manifest()
    snippets = manifest.get("approved_snippets", {})

    errors = []
    for bk in MRP_BINDING_KEYS.values():
        entry = snippets.get(bk)
        if entry is None:
            errors.append(f"{bk}: binding key not found in manifest")
            continue
        file_path = entry.get("file_path", "")
        resolved = _resolve_sql_path(file_path)
        if not resolved:
            errors.append(
                f"{bk}: file_path='{file_path}' does not resolve to an existing file. "
                f"Searched: manifest_dir/basename, hf_dir/filepath, repo_root/filepath."
            )

    assert not errors, "\n".join(errors)


def test_mrp_snippet_files_have_non_empty_content():
    """Each MRP SQL snippet file is non-empty and contains real SQL (not blank)."""
    manifest = _load_manifest()
    snippets = manifest.get("approved_snippets", {})

    errors = []
    for concept, bk in MRP_BINDING_KEYS.items():
        entry = snippets.get(bk, {})
        file_path = entry.get("file_path", "")
        resolved = _resolve_sql_path(file_path)
        if not resolved:
            errors.append(f"{concept} ({bk}): SQL file not found on disk")
            continue
        content = open(resolved, encoding="utf-8").read().strip()
        if not content:
            errors.append(f"{concept} ({bk}): SQL file exists but is empty: {resolved}")
        elif _is_comment_stub(content):
            errors.append(
                f"{concept} ({bk}): SQL file contains only a comment stub "
                f"(starts with '--' or '/*'): {resolved}"
            )

    assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# SolderEngine end-to-end assertions (require manufacturing.db)
# ---------------------------------------------------------------------------

def _require_db():
    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"manufacturing.db not found at {DB_PATH}. "
            "Run the app once to initialise the database, then re-run this test."
        )


def test_inventory_planning_solder_returns_real_sql():
    """SolderEngine.solder('inventory_planning') must return non-comment SQL."""
    _require_db()
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)
    result = engine.solder("inventory_planning", target_dialect="sqlite")
    sql = result.soldered_sql

    assert sql, "solder('inventory_planning') returned an empty string"
    assert not _is_comment_stub(sql), (
        f"solder('inventory_planning') returned a comment stub instead of real SQL:\n{sql[:200]}"
    )


def test_inventory_stock_status_solder_returns_real_sql():
    """SolderEngine.solder('inventory_stock_status') must return non-comment SQL."""
    _require_db()
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)
    result = engine.solder("inventory_stock_status", target_dialect="sqlite")
    sql = result.soldered_sql

    assert sql, "solder('inventory_stock_status') returned an empty string"
    assert not _is_comment_stub(sql), (
        f"solder('inventory_stock_status') returned a comment stub instead of real SQL:\n{sql[:200]}"
    )


def test_resolve_by_binding_key_returns_sql_for_all_mrp_concepts():
    """resolve_by_binding_key returns non-empty, non-stub SQL for each MRP binding."""
    _require_db()
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    errors = []
    for concept, bk in MRP_BINDING_KEYS.items():
        result = engine.resolve_by_binding_key(bk, target_dialect="sqlite")
        sql = result.get("sql", "")
        if not sql:
            errors.append(f"{concept} ({bk}): resolve_by_binding_key returned empty SQL")
        elif _is_comment_stub(sql):
            errors.append(
                f"{concept} ({bk}): resolve_by_binding_key returned a comment stub:\n{sql[:200]}"
            )

    assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Batch 7: dataset-derived concepts (ATP and AllocatedQuantity)
# Resolved via primary_binding_key on the intent row — no column anchor needed.
# ---------------------------------------------------------------------------

def test_derived_manifest_entries_are_approved():
    """ATP and AllocatedQuantity have APPROVED entries in the manifest."""
    manifest = _load_manifest()
    snippets = manifest.get("approved_snippets", {})

    approved_anchors = {
        entry["concept_anchor"].upper()
        for entry in snippets.values()
        if entry.get("validation_status") == "APPROVED"
    }

    missing = [a for a in DERIVED_CONCEPT_ANCHORS if a not in approved_anchors]
    assert not missing, (
        f"Derived concept anchor(s) missing from approved_snippets: {missing}"
    )


def test_derived_snippet_files_exist_and_have_sql():
    """Each derived binding entry's file exists on disk and contains real SQL."""
    manifest = _load_manifest()
    snippets = manifest.get("approved_snippets", {})

    errors = []
    for concept, bk in DERIVED_BINDING_KEYS.items():
        entry = snippets.get(bk)
        if entry is None:
            errors.append(f"{concept} ({bk}): binding key not found in manifest")
            continue
        resolved = _resolve_sql_path(entry.get("file_path", ""))
        if not resolved:
            errors.append(f"{concept} ({bk}): file_path does not resolve on disk")
            continue
        content = open(resolved, encoding="utf-8").read().strip()
        if _is_comment_stub(content):
            errors.append(f"{concept} ({bk}): SQL file contains no DML/DQL statement")

    assert not errors, "\n".join(errors)


def test_derived_intents_solder_returns_real_sql():
    """solder() returns non-stub SQL for the two dataset-derived intents."""
    _require_db()
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    errors = []
    for intent in DERIVED_INTENTS:
        result = engine.solder(intent, target_dialect="sqlite")
        sql = result.soldered_sql
        if not sql:
            errors.append(f"solder('{intent}') returned empty string")
        elif _is_comment_stub(sql):
            errors.append(
                f"solder('{intent}') returned a comment stub — "
                f"primary_binding_key may be missing or file not found:\n{sql[:200]}"
            )

    assert not errors, "\n".join(errors)


def test_derived_resolve_by_binding_key_returns_sql():
    """resolve_by_binding_key returns non-empty SQL for ATP and AllocatedQuantity."""
    _require_db()
    engine = SolderEngine(db_path=DB_PATH, manifest_path=MANIFEST_PATH)

    errors = []
    for concept, bk in DERIVED_BINDING_KEYS.items():
        result = engine.resolve_by_binding_key(bk, target_dialect="sqlite")
        sql = result.get("sql", "")
        if not sql:
            errors.append(f"{concept} ({bk}): resolve_by_binding_key returned empty SQL")
        elif _is_comment_stub(sql):
            errors.append(f"{concept} ({bk}): resolve_by_binding_key returned comment stub")

    assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Standalone runner (also runs under pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _TESTS = [
        test_mrp_manifest_entries_are_approved,
        test_mrp_snippet_files_exist_on_disk,
        test_mrp_snippet_files_have_non_empty_content,
        test_inventory_planning_solder_returns_real_sql,
        test_inventory_stock_status_solder_returns_real_sql,
        test_resolve_by_binding_key_returns_sql_for_all_mrp_concepts,
        test_derived_manifest_entries_are_approved,
        test_derived_snippet_files_exist_and_have_sql,
        test_derived_intents_solder_returns_real_sql,
        test_derived_resolve_by_binding_key_returns_sql,
    ]
    passed = failed = 0
    for _t in _TESTS:
        try:
            _t()
            print(f"  PASS  {_t.__name__}")
            passed += 1
        except Exception as _exc:
            import traceback
            print(f"  FAIL  {_t.__name__}: {_exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        raise SystemExit(1)
