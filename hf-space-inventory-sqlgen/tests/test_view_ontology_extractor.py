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
from datetime import datetime
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
    render_join_scope_sections_md,
    seed_view_ontology_table,
    split_joins_by_scope,
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
    # Parse the value rather than substring-matching "T": a genuine ISO-8601
    # timestamp round-trips through fromisoformat and is timezone-aware (UTC).
    parsed = datetime.fromisoformat(simple_vo.extracted_at)
    assert parsed.tzinfo is not None


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
    # Uniqueness is on the FULL relationship (pair + aliases + type + ON
    # predicate): byte-identical repeats collapse, distinct ones stay.
    keys = [
        (j["left_table"], j["left_alias"], j["right_table"],
         j["right_alias"], j["join_type"], j["on_condition"])
        for j in simple_vo.joins
    ]
    assert len(keys) == len(set(keys))


def test_join_aliases_captured(simple_vo):
    # Alias lineage is preserved (e.g. "col" for customer_order_line).
    col_order_join = next(
        (j for j in simple_vo.joins
         if j["left_table"] == "customer_order_line" and j["right_table"] == "customer_order"),
        None,
    )
    assert col_order_join is not None
    assert col_order_join["left_alias"] == "col"
    assert col_order_join["right_alias"] == "o"


def test_distinct_joins_same_pair_preserved():
    # Two joins to the same table pair with DIFFERENT aliases and predicates are
    # distinct relationships and must both survive — the dedup must not collapse
    # them, and the alias lineage must be retained for each.
    sql = """
        SELECT a.id
        FROM a
        JOIN b b1 ON b1.x = a.x
        JOIN b b2 ON b2.y = a.y
    """
    vo = extract_view_ontology(sql, "k", "TEST", "f.sql")
    a_b = [j for j in vo.joins if j["left_table"] == "a" and j["right_table"] == "b"]
    assert len(a_b) == 2
    assert len({j["on_condition"] for j in a_b}) == 2
    assert {j["right_alias"] for j in a_b} == {"b1", "b2"}


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
    # Use a REAL binding key: extract_all_mrp_views only iterates
    # MRP_VIEW_BINDING_KEYS, so an arbitrary manifest key would be skipped
    # before ever reaching the missing-file branch this test means to exercise.
    real_key = MRP_VIEW_BINDING_KEYS[0]
    manifest = {
        "approved_snippets": {
            real_key: {
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


# ── 13. Temporal Parameter Contract detection & classification ────────────────

UNINVOICED_TEMPORAL_SQL = """
SELECT r.receipt_id AS receiver_id, r.received_date AS received_date
FROM receiving r
JOIN purchase_order po ON po.po_id = r.po_id
JOIN suppliers s ON s.supplier_id = po.supplier_id
WHERE po.site_id = 'SITE-1'
  AND (:supplier_id IS NULL OR s.supplier_id = :supplier_id)
  AND (:start_date IS NULL OR r.received_date >= :start_date)
  AND (:end_date IS NULL OR r.received_date <= :end_date)
  AND EXISTS (
        SELECT 1
        FROM receiving_line rl
        WHERE rl.receipt_id = r.receipt_id
          AND rl.receipt_line_id NOT IN (
                SELECT pl.receipt_line_id
                FROM payable_line pl
                JOIN payables pay ON pay.invoice_id = pl.invoice_id
                WHERE pl.receipt_line_id IS NOT NULL
                  AND (:end_date IS NULL OR pay.invoice_date <= :end_date)
          )
      )
ORDER BY s.supplier_id, r.received_date
"""


@pytest.fixture
def temporal_vo():
    return extract_view_ontology(
        UNINVOICED_TEMPORAL_SQL,
        binding_key="test_temporal_000",
        concept_anchor="UNINVOICEDRECEIPTS",
        view_file="app_schema/ground_truth/sql_snippets/test_temporal.sql",
    )


def test_temporal_parameters_detected(temporal_vo):
    tokens = {p["token"] for p in temporal_vo.temporal_parameters}
    assert tokens == {":start_date", ":end_date", ":supplier_id"}


def test_start_date_is_horizon(temporal_vo):
    p = next(x for x in temporal_vo.temporal_parameters
             if x["token"] == ":start_date")
    assert p["classification"] == "horizon"
    assert p["column"] == "receiving.received_date"


def test_end_date_dual_role_horizon_and_netting(temporal_vo):
    ends = [x for x in temporal_vo.temporal_parameters
            if x["token"] == ":end_date"]
    assert {p["classification"] for p in ends} == {"horizon", "netting"}
    assert {p["column"] for p in ends} == {
        "receiving.received_date", "payables.invoice_date"}


def test_netting_cutoff_on_invoice_date(temporal_vo):
    netting = [x for x in temporal_vo.temporal_parameters
               if x["classification"] == "netting"]
    assert netting
    assert all(p["column"] == "payables.invoice_date" for p in netting)


def test_supplier_id_is_entity_filter(temporal_vo):
    p = next(x for x in temporal_vo.temporal_parameters
             if x["token"] == ":supplier_id")
    assert p["classification"] == "filter"
    assert p["column"] == "suppliers.supplier_id"


def test_temporal_trait_range_bounded_and_point_in_time(temporal_vo):
    assert set(temporal_vo.temporal_trait) == {
        "range-bounded", "point-in-time"}


def test_plain_view_has_no_temporal_parameters(simple_vo):
    assert simple_vo.temporal_parameters == []
    assert simple_vo.temporal_trait == []


# ── 14. Join scopes — sectioned topology (flat / derived subquery / CTE) ─────

FLAT_VIEW_SQL = """
SELECT pl.line_id, po.po_id
FROM po_line pl
JOIN purchase_order po ON po.po_id = pl.po_id
LEFT JOIN suppliers s  ON s.supplier_id = po.supplier_id
"""

DERIVED_SUBQUERY_SQL = """
SELECT pl.line_id
FROM po_line pl
JOIN purchase_order po ON po.po_id = pl.po_id
JOIN (
    SELECT rl.po_line_id, SUM(rl.quantity_received) AS qty
    FROM receiving_line rl
    JOIN receiving r ON r.receipt_id = rl.receipt_id
    GROUP BY rl.po_line_id
) rcv ON rcv.po_line_id = pl.line_id
LEFT JOIN (
    SELECT pl2.po_line_id, SUM(ABS(pl2.qty)) AS qty
    FROM payable_line pl2
    JOIN payables pay ON pay.invoice_id = pl2.invoice_id
    GROUP BY pl2.po_line_id
) inv ON inv.po_line_id = pl.line_id
"""


def test_flat_view_single_outer_scope():
    vo = extract_view_ontology(FLAT_VIEW_SQL, "k", "TEST", "f.sql")
    assert vo.joins
    assert all(j["scope"] == "" for j in vo.joins)
    outer, scoped = split_joins_by_scope(vo.joins)
    assert len(outer) == len(vo.joins)
    assert scoped == {}
    assert render_join_scope_sections_md(scoped, vo.cte_names) == ""


def test_derived_subquery_scopes_labeled_by_alias():
    vo = extract_view_ontology(DERIVED_SUBQUERY_SQL, "k", "TEST", "f.sql")
    outer, scoped = split_joins_by_scope(vo.joins)
    # outer spine: po_line->purchase_order, po_line->rcv, po_line->inv
    assert {j["right_table"] for j in outer} == {"purchase_order", "rcv", "inv"}
    assert set(scoped.keys()) == {"rcv", "inv"}
    assert [j["right_table"] for j in scoped["rcv"]] == ["receiving"]
    assert [j["right_table"] for j in scoped["inv"]] == ["payables"]


def test_derived_subquery_sections_render_as_derived():
    vo = extract_view_ontology(DERIVED_SUBQUERY_SQL, "k", "TEST", "f.sql")
    _, scoped = split_joins_by_scope(vo.joins)
    md = render_join_scope_sections_md(scoped, vo.cte_names)
    assert "Derived subquery `rcv`" in md
    assert "Derived subquery `inv`" in md
    assert "CTE `rcv`" not in md


def test_cte_scope_labeled_by_cte_alias(simple_vo):
    # SIMPLE_VIEW_SQL joins inside the `open_demand` CTE; the outer query only
    # LEFT JOINs the CTE itself.
    outer, scoped = split_joins_by_scope(simple_vo.joins)
    assert "open_demand" in scoped
    scoped_rights = {j["right_table"] for j in scoped["open_demand"]}
    assert "customer_order" in scoped_rights
    assert [j["right_table"] for j in outer] == ["open_demand"]
    md = render_join_scope_sections_md(scoped, simple_vo.cte_names)
    assert "CTE `open_demand`" in md
    assert "Derived subquery `open_demand`" not in md


def test_nested_subquery_inside_cte_takes_nearest_scope():
    # A derived subquery nested INSIDE a CTE: joins in the innermost SELECT
    # belong to the nearest enclosing scope (the subquery alias), not the CTE.
    sql = """
    WITH agg AS (
        SELECT sub.part_id, sub.qty
        FROM (
            SELECT rl.part_id, SUM(rl.quantity_received) AS qty
            FROM receiving_line rl
            JOIN receiving r ON r.receipt_id = rl.receipt_id
            GROUP BY rl.part_id
        ) sub
        JOIN part p ON p.part_id = sub.part_id
    )
    SELECT a.part_id FROM agg a
    """
    vo = extract_view_ontology(sql, "k", "TEST", "f.sql")
    _, scoped = split_joins_by_scope(vo.joins)
    assert set(scoped.keys()) == {"agg", "sub"}
    assert [j["right_table"] for j in scoped["sub"]] == ["receiving"]
    assert [j["right_table"] for j in scoped["agg"]] == ["part"]


def test_legacy_rows_without_scope_render_flat():
    # Previously seeded joins_json rows have no "scope" key at all — they must
    # load and land in the outer (flat/legacy) bucket with no sections.
    legacy = [
        {"left_table": "a", "right_table": "b", "join_type": "INNER",
         "on_condition": "b.x = a.x", "left_key": "x", "right_key": "x",
         "left_alias": "", "right_alias": ""},
    ]
    outer, scoped = split_joins_by_scope(legacy)
    assert len(outer) == 1
    assert scoped == {}
    assert render_join_scope_sections_md(scoped, []) == ""


def test_governed_pra_snippet_scopes():
    # The real PRA governed snippet: rcv/inv derived-subquery scaffolding must
    # section out, leaving the base-table spine in the outer scope.
    snippet = (
        HF_DIR / "app_schema" / "ground_truth" / "sql_snippets"
        / "payables_partialreceiptaccrual_20260708_000004.sql"
    )
    vo = extract_view_ontology(
        snippet.read_text(encoding="utf-8"),
        binding_key="payables_partialreceiptaccrual_20260708_000004",
        concept_anchor="PARTIALRECEIPTACCRUAL",
        view_file=str(snippet),
    )
    outer, scoped = split_joins_by_scope(vo.joins)
    assert set(scoped.keys()) == {"rcv", "inv"}
    assert all(j["left_table"] == "po_line" for j in outer)


def test_governed_twm_snippet_stays_flat():
    # The flat Three-Way Match Coverage spine has NO subquery scopes — a single
    # outer section with all six joins, no scaffolding sections.
    snippet = (
        HF_DIR / "app_schema" / "ground_truth" / "sql_snippets"
        / "payables_threewaymatchcoverage_20260708_000005.sql"
    )
    vo = extract_view_ontology(
        snippet.read_text(encoding="utf-8"),
        binding_key="payables_threewaymatchcoverage_20260708_000005",
        concept_anchor="THREEWAYMATCHCOVERAGE",
        view_file=str(snippet),
    )
    outer, scoped = split_joins_by_scope(vo.joins)
    assert scoped == {}
    assert len(outer) == 6


def test_governed_uninvoiced_snippet_carries_temporal_contract():
    # Regression for the bound (binding-key) render path: the real SME-approved
    # snippet must yield a machine-readable Temporal Contract straight from disk.
    snippet = (
        HF_DIR / "app_schema" / "ground_truth" / "sql_snippets"
        / "payables_uninvoicedreceipts_20260706_000003.sql"
    )
    vo = extract_view_ontology(
        snippet.read_text(encoding="utf-8"),
        binding_key="payables_uninvoicedreceipts_20260706_000003",
        concept_anchor="UNINVOICEDRECEIPTS",
        view_file=str(snippet),
    )
    by_token = {}
    for p in vo.temporal_parameters:
        by_token.setdefault(p["token"], set()).add(p["classification"])
    assert by_token.get(":start_date") == {"horizon"}
    assert by_token.get(":end_date") == {"horizon", "netting"}
    assert by_token.get(":supplier_id") == {"filter"}
    assert set(vo.temporal_trait) == {"range-bounded", "point-in-time"}
