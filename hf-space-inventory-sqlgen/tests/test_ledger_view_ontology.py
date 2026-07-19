"""Regression gate: the 5 governed General_Ledger queries are surfaced in the
ontology mosaic.

Asserts:
  1. extract_all_ledger_views parses all 5 ledger binding keys from the
     manifest with semantics_version 'ledger_views_v1'.
  2. time_phased flags: the period-window queries (bounded :start_date /
     :end_date horizon) are time-phased; the :as_of_date balance is
     point-in-time.
  3. Physical tables are the gl_* sub-ledger tables only.
  4. The live DB (when present) carries the seeded sql_view_ontology rows and
     ground_truth_table_usage rows for every ledger binding key.

Run gate-style:  python tests/test_ledger_view_ontology.py
"""
import os
import sqlite3
import sys
from pathlib import Path

HF_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(HF_DIR))

from view_ontology_extractor import (
    LEDGER_SEMANTICS_VERSION,
    LEDGER_VIEW_BINDING_KEYS,
    extract_all_ledger_views,
)

MANIFEST_PATH = HF_DIR / "app_schema" / "ground_truth" / "reviewer_manifest.json"
DB_PATH = HF_DIR / "app_schema" / "manufacturing.db"

EXPECTED_TIME_PHASED = {
    "ledger_inventorybalance_20260719_000001": False,  # :as_of_date cutoff
    "ledger_jobcostsummary_20260719_000002": True,
    "ledger_eventtrace_20260719_000003": True,
    "ledger_materialissued_20260719_000004": True,
    "ledger_fgproduced_20260719_000005": True,
}


def test_extraction():
    views = extract_all_ledger_views(str(MANIFEST_PATH), str(HF_DIR))
    by_key = {v.binding_key: v for v in views}
    assert set(by_key) == set(LEDGER_VIEW_BINDING_KEYS), (
        f"expected all 5 ledger views, got {sorted(by_key)}")
    for key, vo in by_key.items():
        assert vo.semantics_version == LEDGER_SEMANTICS_VERSION, key
        assert vo.time_phased == EXPECTED_TIME_PHASED[key], (
            f"{key}: time_phased={vo.time_phased}, "
            f"expected {EXPECTED_TIME_PHASED[key]}")
        assert vo.physical_tables, key
        assert all(t.startswith("gl_") for t in vo.physical_tables), (
            f"{key}: non-gl_ table in {vo.physical_tables}")
        assert vo.concept_anchor.startswith("GL"), key
    print(f"PASS test_extraction ({len(views)} ledger views)")


def test_db_seeded():
    if not DB_PATH.exists():
        print("SKIP test_db_seeded (no manufacturing.db)")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        vo_keys = {r[0] for r in conn.execute(
            "SELECT binding_key FROM sql_view_ontology "
            "WHERE semantics_version = ?", (LEDGER_SEMANTICS_VERSION,))}
        missing = set(LEDGER_VIEW_BINDING_KEYS) - vo_keys
        assert not missing, f"sql_view_ontology missing ledger rows: {missing}"
        usage_keys = {r[0] for r in conn.execute(
            "SELECT DISTINCT category_id FROM ground_truth_table_usage "
            "WHERE category_id LIKE 'ledger_%'")}
        missing_usage = set(LEDGER_VIEW_BINDING_KEYS) - usage_keys
        assert not missing_usage, (
            f"ground_truth_table_usage missing ledger rows: {missing_usage}")
    finally:
        conn.close()
    print("PASS test_db_seeded")


if __name__ == "__main__":
    test_extraction()
    test_db_seeded()
    print("All ledger view-ontology tests passed.")
