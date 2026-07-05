"""
test_view_ontology_extractor.py
Tests for the view ontology extraction pipeline.

What's covered:
  1. extract_view_ontology on a minimal hand-crafted SQL view
  2. Physical tables exclude CTE names
  3. Join extraction — equi-join keys, join types, dedup
  4. State-predicate extraction from WHERE clauses
  5. Time-phasing detection via CTE names and window functions
  6. Grain columns (GROUP BY / ORDER BY)
  7. Selected columns from outermost SELECT
  8. extract_all_mrp_views — all 7 canonical views parse without error
  9. Per-view spot checks: ATP physical tables, AllocatedQty joins, time-phased flags
 10. SQLite round-trip: create_table → seed → get → list (idempotent)
 11. Missing view file is skipped gracefully (no crash)
 12. get_view_ontology returns None for unknown concept_anchor
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

HF_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(HF_DIR))

from view_ontology_extractor import (
    SEMANTICS_VERSION,
    MRP_VIEW_BINDING_KEYS,
    ViewOntology,
    create_view_ontology_table,
    extract_all_mrp_views,
    extract_view_ontology,
    get_view_ontology,
    list_view_ontologies,
    seed_view_ontology_table,
)

MANIFEST_PATH = HF_DIR / "app_schema" / "ground_truth" / "reviewer_manifest.json"
BASE_DIR = str(HF_DIR)


SIMPLE_VIEW_SQL = """
WITH horizon AS (
    SELECT date('now', '-30 days') AS h_start
),
open_demand AS (
    SELECT col.part_id, SUM(col.order_qty) AS qty
    FROM customer_order_line col
    JOIN customer_order o ON o.order_id = col.order_id
    JOIN horizon h ON date(col.need_by_date) >= h.h_start
    WHERE o.status = 'Open'
    GROUP BY col.part_id
)
SELECT
    p.part_id,
    p.on_hand_qty,
    od.qty AS open_demand_qty
FROM part p
LEFT JOIN open_demand od ON od.part_id = p.part_id
WHERE p.active = 1
ORDER BY p.part_id
"""


@pytest.fixture
def simple_vo():
    return extract_view_ontology(
        SIMPLE_VIEW_SQL,
        binding_key="test_simple_000",
        concept_anchor="TESTCONCEPT",
        view_file="app_schema/ground_truth/sql_snippets/test_simple.sql",
    )


@pytest.fixture
def all_views():
    return extract_all_mrp_views(str(MANIFEST_PATH), BASE_DIR)


@pytest.fixture
def mem_db():
    conn = sqlite3.connect(":memory:")
    create_view_ontology_table(conn)
    yield conn
    conn.close()


# ── 1. Basic structure from hand-crafted SQL ──────────────────────────────────

def test_concept_anchor_stored(simple_vo):
    assert simple_vo.concept_anchor == "TESTCONCEPT"


def test_binding_key_stored(simple_vo):
    assert simple_vo.binding_key == "test_simple_000"


def test_semantics_version(simple_vo):
    assert simple_vo.semantics_version == SEMANTICS_VERSION


def test_extracted_at_is_iso(simple_vo):
    assert "T" in simple_vo.extracted_at  # ISO-8601


# ── 2. Physical tables exclude CTE names ─────────────────────────────────────

def test_physical_tables_exclude_ctes(simple_vo):
    assert "horizon" not in simple_vo.physical_tables
    assert "open_demand" not in simple_vo.physical_tables


def test_physical_tables_include_real_tables(simple_vo):
    assert "part" in simple_vo.physical_tables
    assert "customer_order_line" in simple_vo.physical_tables
    assert "customer_order" in simple_vo.physical_tables


def test_cte_names_captured(simple_vo):
    assert "horizon" in simple_vo.cte_names
    assert "open_demand" in simple_vo.cte_names


# ── 3. Join extraction ────────────────────────────────────────────────────────

def test_joins_non_empty(simple_vo):
    assert len(simple_vo.joins) > 0


def test_equi_join_keys_extracted(simple_vo):
    col_order_join = next(
        (j for j in simple_vo.joins
         if j["left_table"] == "customer_order_line" and j["right_table"] == "customer_order"),
        None,
    )
    assert col_order_join is not None
    assert col_order_join["left_key"] == "order_id"
    assert col_order_join["right_key"] == "order_id"


def test_left_join_type_captured(simple_vo):
    left_join = next(
        (j for j in simple_vo.joins if j["join_type"] == "LEFT"),
        None,
    )
    assert left_join is not None
    assert left_join["right_table"] == "open_demand"


def test_joins_are_deduped(simple_vo):
    keys = [(j["left_table"], j["right_table"], j["join_type"]) for j in simple_vo.joins]
    assert len(keys) == len(set(keys))


# ── 4. State predicates ───────────────────────────────────────────────────────

def test_state_predicates_non_empty(simple_vo):
    assert len(simple_vo.state_predicates) > 0


def test_active_filter_in_predicates(simple_vo):
    combined = " ".join(simple_vo.state_predicates)
    assert "active" in combined


def test_status_filter_in_predicates(simple_vo):
    combined = " ".join(simple_vo.state_predicates)
    assert "Open" in combined


# ── 5. Time-phasing detection ─────────────────────────────────────────────────

def test_simple_view_time_phased_via_cte(simple_vo):
    assert simple_vo.time_phased is True  # "horizon" CTE triggers detection


def test_time_phased_false_for_non_temporal():
    sql = "SELECT p.part_id FROM part p WHERE p.active = 1"
    vo = extract_view_ontology(sql, "k", "TEST", "f.sql")
    assert vo.time_phased is False


# ── 6. Grain columns ─────────────────────────────────────────────────────────

def test_grain_columns_captured(simple_vo):
    assert "part_id" in simple_vo.grain_columns


# ── 7. Selected columns ───────────────────────────────────────────────────────

def test_selected_columns_non_empty(simple_vo):
    assert len(simple_vo.selected_columns) > 0


def test_selected_columns_include_known_aliases(simple_vo):
    assert "part_id" in simple_vo.selected_columns
    assert "on_hand_qty" in simple_vo.selected_columns


# ── 8. All 7 canonical MRP views parse without error ─────────────────────────

def test_all_7_views_extracted(all_views):
    assert len(all_views) == 7


def test_all_binding_keys_present(all_views):
    extracted_keys = {vo.binding_key for vo in all_views}
    assert extracted_keys == set(MRP_VIEW_BINDING_KEYS)


def test_all_views_have_physical_tables(all_views):
    for vo in all_views:
        assert len(vo.physical_tables) > 0, f"{vo.concept_anchor} has no physical tables"


def test_all_views_have_selected_columns(all_views):
    for vo in all_views:
        assert len(vo.selected_columns) > 0, f"{vo.concept_anchor} has no selected columns"


# ── 9. Per-view spot checks ───────────────────────────────────────────────────

def _get(all_views, anchor):
    return next(v for v in all_views if v.concept_anchor == anchor)


def test_atp_physical_tables(all_views):
    atp = _get(all_views, "AVAILABLETOPROMISE")
    for expected in ("part", "customer_order_line", "customer_order", "work_order"):
        assert expected in atp.physical_tables


def test_atp_is_time_phased(all_views):
    assert _get(all_views, "AVAILABLETOPROMISE").time_phased is True


def test_atp_has_bucket_temporal_keys(all_views):
    atp = _get(all_views, "AVAILABLETOPROMISE")
    assert any("bucket" in k.lower() for k in atp.temporal_keys)


def test_atp_has_joins(all_views):
    atp = _get(all_views, "AVAILABLETOPROMISE")
    assert len(atp.joins) > 0


def test_allocated_joins_equi_keys(all_views):
    alloc = _get(all_views, "ALLOCATEDQUANTITY")
    col_order = next(
        (j for j in alloc.joins
         if j["left_table"] == "customer_order_line" and j["right_table"] == "customer_order"),
        None,
    )
    assert col_order is not None
    assert col_order["left_key"] == "order_id"
    assert col_order["right_key"] == "order_id"


def test_safetystock_is_time_phased(all_views):
    assert _get(all_views, "SAFETYSTOCK").time_phased is True


def test_minimum_stock_not_time_phased(all_views):
    assert _get(all_views, "MINIMUMSTOCKQUANTITY").time_phased is False


def test_minimum_stock_only_part_table(all_views):
    minstock = _get(all_views, "MINIMUMSTOCKQUANTITY")
    assert minstock.physical_tables == ["part"]


def test_eoq_predicates_include_cancelled_filter(all_views):
    eoq = _get(all_views, "ECONOMICORDERQUANTITY")
    combined = " ".join(eoq.state_predicates)
    assert "Cancelled" in combined


# ── 10. SQLite round-trip ─────────────────────────────────────────────────────

def test_seed_returns_count(mem_db, all_views):
    n = seed_view_ontology_table(mem_db, all_views)
    assert n == 7


def test_get_returns_record(mem_db, all_views):
    seed_view_ontology_table(mem_db, all_views)
    rec = get_view_ontology(mem_db, "AVAILABLETOPROMISE")
    assert rec is not None
    assert rec["concept_anchor"] == "AVAILABLETOPROMISE"


def test_get_decodes_json_lists(mem_db, all_views):
    seed_view_ontology_table(mem_db, all_views)
    rec = get_view_ontology(mem_db, "AVAILABLETOPROMISE")
    assert isinstance(rec["physical_tables_json"], list)
    assert isinstance(rec["joins_json"], list)
    assert isinstance(rec["state_predicates_json"], list)
    assert isinstance(rec["time_phased"], bool)


def test_list_returns_all_7(mem_db, all_views):
    seed_view_ontology_table(mem_db, all_views)
    rows = list_view_ontologies(mem_db)
    assert len(rows) == 7


def test_seed_is_idempotent(mem_db, all_views):
    seed_view_ontology_table(mem_db, all_views)
    seed_view_ontology_table(mem_db, all_views)
    rows = list_view_ontologies(mem_db)
    assert len(rows) == 7


# ── 11. Missing file is skipped gracefully ────────────────────────────────────

def test_missing_view_file_skipped(tmp_path):
    manifest = {
        "approved_snippets": {
            "test_missing": {
                "concept_anchor": "MISSINGCONCEPT",
                "file_path": "app_schema/ground_truth/sql_snippets/does_not_exist.sql",
            }
        }
    }
    manifest_file = tmp_path / "reviewer_manifest.json"
    manifest_file.write_text(json.dumps(manifest))
    views = extract_all_mrp_views(str(manifest_file), str(tmp_path))
    assert views == []


# ── 12. Unknown concept_anchor returns None ───────────────────────────────────

def test_get_unknown_returns_none(mem_db, all_views):
    seed_view_ontology_table(mem_db, all_views)
    assert get_view_ontology(mem_db, "DOESNOTEXIST") is None
