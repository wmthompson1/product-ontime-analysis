"""hf-space-inventory-sqlgen/tests/test_ledger_nlq_queries.py

CI guard for the ledger NLQ layer (governed gl_* queries).

Covers:
  1. All five ledger manifest entries are APPROVED with a v2 (join-aware)
     structural fingerprint, and each file_path resolves to real, non-empty SQL.
  2. SolderEngine.resolve_by_binding_key() serves every ledger binding
     (fingerprint + join + temporal-contract gates pass).
  3. Each ledger intent row carries the right primary_binding_key and is
     visible to the Query Palette via schema_intent_queries (indexes 0..4 of
     job_costing_ledger.sql) and linked to the General_Ledger perspective.
  4. Mock dispatcher routing: natural-language questions land on the right
     ledger intent and return real SQL (parses as a SELECT), and pre-existing
     non-ledger routes are unaffected.
  5. Every governed query executes against manufacturing.db with NULL params
     (guard idiom) and with bound temporal/entity params.

Run: python hf-space-inventory-sqlgen/tests/test_ledger_nlq_queries.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from unittest.mock import MagicMock

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import sqlglot  # noqa: E402
from sqlglot import exp  # noqa: E402

from solder_engine import SolderEngine  # noqa: E402
from production_dispatcher import ProductionDispatcher  # noqa: E402

MANIFEST_PATH = os.path.join(HF_DIR, "app_schema", "ground_truth", "reviewer_manifest.json")
DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

LEDGER_BINDINGS = {
    "ledger_inventory_balance": "ledger_inventorybalance_20260719_000001",
    "ledger_job_cost_summary":  "ledger_jobcostsummary_20260719_000002",
    "ledger_event_trace":       "ledger_eventtrace_20260719_000003",
    "ledger_material_issued":   "ledger_materialissued_20260719_000004",
    "ledger_fg_production":     "ledger_fgproduced_20260719_000005",
}

PALETTE_ROWS = {
    "ledger_inventory_balance": (0, "Inventory Balance per Bucket"),
    "ledger_job_cost_summary":  (1, "Job Cost Summary by Cost Element"),
    "ledger_event_trace":       (2, "Job Event Trace"),
    "ledger_material_issued":   (3, "Material Issued over a Period"),
    "ledger_fg_production":     (4, "Finished Goods Produced over a Period"),
}

ROUTING_CASES = [
    ("Show WIP for job 42",                       "ledger_job_cost_summary"),
    ("what material was issued in July",          "ledger_material_issued"),
    ("Show the event trace for job WO-00001",     "ledger_event_trace"),
    ("What finished goods were produced this year?", "ledger_fg_production"),
    ("Show me the inventory balance by bucket",   "ledger_inventory_balance"),
]

NON_LEDGER_CASES = [
    ("What is the cost impact of defects by severity?", "defect_cost_analysis"),
    ("Which suppliers have the best on-time delivery?", "supplier_scorecard"),
    ("How much stock is available to promise?",         "inventory_atp"),
]

ALL_PARAMS = {"as_of_date": None, "job_id": None, "start_date": None, "end_date": None}

failures: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        failures.append(label)


def test_manifest_entries() -> None:
    manifest = json.load(open(MANIFEST_PATH))
    snippets = manifest["approved_snippets"]
    for intent, key in LEDGER_BINDINGS.items():
        entry = snippets.get(key)
        check(entry is not None, f"manifest entry present: {key}")
        if not entry:
            continue
        check(entry["validation_status"] == "APPROVED", f"{key} is APPROVED")
        fp = entry.get("structural_fingerprint", {})
        check(fp.get("extractor", "").endswith("-v2"), f"{key} carries a v2 (join-aware) fingerprint")
        check(bool(fp.get("base_tables")), f"{key} fingerprint has base tables")
        path = os.path.join(HF_DIR, entry["file_path"])
        check(os.path.exists(path), f"{key} snippet file exists")
        if os.path.exists(path):
            check(bool(open(path).read().strip()), f"{key} snippet file non-empty")


def test_solder_engine_serves() -> None:
    eng = SolderEngine()
    for key in LEDGER_BINDINGS.values():
        r = eng.resolve_by_binding_key(key)
        check(bool(r.get("sql")) and not r.get("fail_closed"),
              f"SolderEngine serves {key} (fail_condition={r.get('fail_condition', '')})")


def test_intent_and_palette_rows() -> None:
    conn = sqlite3.connect(DB_PATH)
    for intent, key in LEDGER_BINDINGS.items():
        row = conn.execute(
            "SELECT primary_binding_key FROM schema_intents WHERE intent_name = ?",
            (intent,)).fetchone()
        check(row is not None and row[0] == key,
              f"intent {intent} carries primary_binding_key {key}")
        qi, qn = PALETTE_ROWS[intent]
        row = conn.execute("""
            SELECT 1 FROM schema_intent_queries siq
            JOIN schema_intents si USING (intent_id)
            WHERE si.intent_name = ? AND siq.query_file = 'job_costing_ledger.sql'
              AND siq.query_index = ? AND siq.query_name = ?
        """, (intent, qi, qn)).fetchone()
        check(row is not None, f"palette row for {intent} (index {qi}: {qn})")
        row = conn.execute("""
            SELECT 1 FROM schema_intent_perspectives sip
            JOIN schema_intents si USING (intent_id)
            JOIN schema_perspectives sp USING (perspective_id)
            WHERE si.intent_name = ? AND sp.perspective_name = 'General_Ledger'
              AND sip.intent_factor_weight = 1
        """, (intent,)).fetchone()
        check(row is not None, f"{intent} linked to General_Ledger perspective")
    conn.close()


def test_mock_routing() -> None:
    d = ProductionDispatcher(solder_engine=MagicMock(), use_live_api=False)
    for question, expected_intent in ROUTING_CASES + NON_LEDGER_CASES:
        got = d.extract_via_mock(question)["intent"]
        check(got == expected_intent, f"route {question!r} -> {expected_intent} (got {got})")


def test_dispatch_returns_real_sql() -> None:
    d = ProductionDispatcher(use_live_api=False)
    for question, expected_intent in ROUTING_CASES:
        r = d.dispatch(question)
        ok = r.intent == expected_intent and bool(r.assembled_sql)
        if ok:
            try:
                ast = sqlglot.parse_one(r.assembled_sql, read="sqlite")
                ok = isinstance(ast, (exp.Select, exp.Union))
            except Exception:
                ok = False
        check(ok, f"dispatch {question!r} returns governed SELECT via {r.binding_key}")


def test_snippets_execute() -> None:
    manifest = json.load(open(MANIFEST_PATH))
    conn = sqlite3.connect(DB_PATH)
    for key in LEDGER_BINDINGS.values():
        sql = open(os.path.join(HF_DIR, manifest["approved_snippets"][key]["file_path"])).read()
        rows = conn.execute(sql, ALL_PARAMS).fetchall()
        check(len(rows) > 0, f"{key} executes with NULL guards ({len(rows)} rows)")
    # Bound-parameter spot checks
    sql = open(os.path.join(HF_DIR, manifest["approved_snippets"][LEDGER_BINDINGS["ledger_event_trace"]]["file_path"])).read()
    rows = conn.execute(sql, {**ALL_PARAMS, "job_id": "WO-00001"}).fetchall()
    check(len(rows) > 0 and all(r[1] == "WO-00001" for r in rows),
          "event trace binds :job_id to a single job")
    sql = open(os.path.join(HF_DIR, manifest["approved_snippets"][LEDGER_BINDINGS["ledger_material_issued"]]["file_path"])).read()
    rows = conn.execute(sql, {**ALL_PARAMS, "start_date": "2025-07-01", "end_date": "2025-07-31"}).fetchall()
    check(all("2025-07-01" <= r[4][:10] <= "2025-07-31" for r in rows),
          f"material issued binds the July window ({len(rows)} rows)")
    conn.close()


if __name__ == "__main__":
    for fn in (test_manifest_entries, test_solder_engine_serves,
               test_intent_and_palette_rows, test_mock_routing,
               test_dispatch_returns_real_sql, test_snippets_execute):
        fn()
    if failures:
        print(f"\n{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("\nALL LEDGER NLQ CHECKS PASSED")
