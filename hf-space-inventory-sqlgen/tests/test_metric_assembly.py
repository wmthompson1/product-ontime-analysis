"""Tests for metric computation templates and SolderEngine metric assembly.

A metric is an existing *concept* node (concept_type='metric') that stores a
dialect-agnostic ``computation_template`` with named ``{variable}`` placeholders
— never static SQL. Each variable binds to a physical column via a
``schema_concept_fields`` row carrying ``variable_name`` (the SQLite source of
the graph's ``resolves_to`` edges). ``SolderEngine.assemble_metric_sql`` swaps
the variables for real table-qualified columns and transpiles.

Two layers:
1. Hermetic fixture tests — a tiny temp SQLite DB exercises every rule of the
   assembler (template storage, binding/lineage, define-once identical SQL,
   perspective fan-out → identical SQL, cross-dialect transpile, and the
   fail-closed paths) without touching the gitignored app DB.
2. Real-DB integration — if the app DB is present, the 5 showcase metrics must
   exist with templates and assemble to runnable SQL, and the 3 delivery metrics
   must share one byte-identical computation expression (define-once).
3. Meta-context overlay — the table_descriptions CSV ↔ api_table_descriptions
   round-trip, and the off-physical-node guardrail (no node in
   graph_metadata.json ever carries the overlay's ai_context).

Run: python hf-space-inventory-sqlgen/tests/test_metric_assembly.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(HF_DIR)
sys.path.insert(0, HF_DIR)

from solder_engine import SolderEngine, MetricAssemblyError  # noqa: E402

# The approved on-time delivery template, shared verbatim by all delivery metrics.
DELIVERY_TEMPLATE = (
    "AVG(CASE WHEN {receipt_date} IS NOT NULL AND {receipt_date} <= {required_date} "
    "THEN 1.0 WHEN {receipt_date} IS NOT NULL AND {receipt_date} > {required_date} "
    "THEN 0.0 ELSE NULL END)"
)
OEE_TEMPLATE = "SUM({act_run_hrs}) / NULLIF(SUM({run_hrs}), 0)"


def _build_fixture_db(path: str) -> None:
    """Create a minimal metric graph in a fresh SQLite DB."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE schema_concepts (
            concept_id           INTEGER PRIMARY KEY,
            concept_name         TEXT,
            concept_type         TEXT,
            description          TEXT,
            domain               TEXT,
            computation_template TEXT
        );
        CREATE TABLE schema_concept_fields (
            id            INTEGER PRIMARY KEY,
            concept_id    INTEGER,
            table_name    TEXT,
            field_name    TEXT,
            variable_name TEXT
        );
        CREATE TABLE schema_perspectives (
            perspective_id   INTEGER PRIMARY KEY,
            perspective_name TEXT
        );
        CREATE TABLE schema_perspective_concepts (
            perspective_id INTEGER,
            concept_id     INTEGER
        );
        CREATE TABLE api_field_descriptions (
            source_database TEXT NOT NULL,
            schema_name     TEXT NOT NULL,
            table_name      TEXT NOT NULL,
            column_name     TEXT NOT NULL,
            display_name    TEXT,
            description     TEXT,
            example_value   TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        -- Physical tables, declaring the FK the join resolver derives from.
        CREATE TABLE purchase_order (
            po_id         INTEGER PRIMARY KEY,
            required_date TEXT
        );
        CREATE TABLE receiving (
            recv_id      INTEGER PRIMARY KEY,
            po_id        INTEGER REFERENCES purchase_order(po_id),
            receipt_date TEXT
        );
        CREATE TABLE operation (
            op_id       INTEGER PRIMARY KEY,
            run_hrs     REAL,
            act_run_hrs REAL
        );
    """)

    concepts = [
        # id, name, type, description, domain, template
        (1, "DelFanout", "metric", "Delivery metric with perspective fan-out.", "Delivery", DELIVERY_TEMPLATE),
        (2, "DelSingle", "metric", "Same delivery metric, single perspective.", "Delivery", DELIVERY_TEMPLATE),
        (3, "OEEish", "metric", "Single-table efficiency ratio.", "Manufacturing", OEE_TEMPLATE),
        (4, "StaticMetric", "metric", "Illegal static template.", "Bad", "SUM(1)"),
        (5, "MissingBind", "metric", "Template var with no binding.", "Bad", "SUM({orphan})"),
        (6, "ConflictMetric", "metric", "Var bound to two columns.", "Bad", "SUM({x})"),
        (7, "NotAMetric", "dimension", "A non-metric concept.", "Other", None),
    ]
    conn.executemany(
        "INSERT INTO schema_concepts "
        "(concept_id, concept_name, concept_type, description, domain, computation_template) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        concepts,
    )

    fields = [
        # DelFanout — each binding row DUPLICATED (fan-out across 2 perspectives).
        (1, "receiving", "receipt_date", "receipt_date"),
        (1, "purchase_order", "required_date", "required_date"),
        (1, "receiving", "receipt_date", "receipt_date"),
        (1, "purchase_order", "required_date", "required_date"),
        # DelSingle — single rows (no fan-out).
        (2, "receiving", "receipt_date", "receipt_date"),
        (2, "purchase_order", "required_date", "required_date"),
        # OEEish — single table.
        (3, "operation", "run_hrs", "run_hrs"),
        (3, "operation", "act_run_hrs", "act_run_hrs"),
        # MissingBind — intentionally no binding for {orphan}.
        # ConflictMetric — {x} resolves to two different columns.
        (6, "receiving", "receipt_date", "x"),
        (6, "purchase_order", "required_date", "x"),
    ]
    conn.executemany(
        "INSERT INTO schema_concept_fields "
        "(concept_id, table_name, field_name, variable_name) VALUES (?, ?, ?, ?)",
        fields,
    )

    conn.executemany(
        "INSERT INTO schema_perspectives (perspective_id, perspective_name) VALUES (?, ?)",
        [(1, "Manufacturing"), (2, "Work_Orders"), (3, "Finance")],
    )
    conn.executemany(
        "INSERT INTO schema_perspective_concepts (perspective_id, concept_id) VALUES (?, ?)",
        [(1, 1), (2, 1), (3, 2)],  # DelFanout under 2 perspectives, DelSingle under 1
    )

    conn.executemany(
        "INSERT INTO api_field_descriptions "
        "(source_database, schema_name, table_name, column_name, display_name, description) "
        "VALUES ('manufacturing', 'dbo', ?, ?, ?, ?)",
        [
            ("receiving", "receipt_date", "Receipt Date", "Date goods actually arrived."),
            ("purchase_order", "required_date", "Required Date", "Date goods were needed."),
        ],
    )
    conn.commit()
    conn.close()


# ── hermetic fixture tests ──────────────────────────────────────────────────

def test_template_storage_lists_only_metrics_with_templates():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        names = {m["concept_name"] for m in eng.list_metrics()}
        # Metrics with a template are listed; the dimension and template-less rows are not.
        assert "DelFanout" in names and "OEEish" in names, names
        assert "NotAMetric" not in names, "non-metric concept must not be listed"
        # Template round-trips verbatim (dialect-agnostic, with {placeholders}).
        tmpl = eng.get_metric_template("DelSingle")
        assert tmpl == DELIVERY_TEMPLATE, tmpl
        assert "{receipt_date}" in tmpl and "{required_date}" in tmpl


def test_bindings_dedup_and_lineage():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        # Fan-out (4 rows) collapses to 2 distinct variable bindings.
        binds = eng.get_metric_bindings("DelFanout")
        assert len(binds) == 2, [(b.variable_name, b.table_name, b.column_name) for b in binds]
        bymap = {b.variable_name: (b.table_name, b.column_name) for b in binds}
        assert bymap["receipt_date"] == ("receiving", "receipt_date")
        assert bymap["required_date"] == ("purchase_order", "required_date")
        # Lineage carries the SME meaning from api_field_descriptions.
        lin = eng.get_metric_lineage("DelFanout")
        meanings = {v["variable"]: v["meaning"] for v in lin["variables"]}
        assert meanings["receipt_date"] == "Date goods actually arrived."
        assert sorted(lin["tables"]) == ["purchase_order", "receiving"]
        assert sorted(lin["perspectives"]) == ["Manufacturing", "Work_Orders"]


def test_define_once_and_fanout_yield_identical_sql():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        # DelFanout (duplicated fan-out rows) and DelSingle (single rows) share the
        # same template + bindings → identical computation expression and join.
        a = eng.assemble_metric_sql("DelFanout", "sqlite")
        b = eng.assemble_metric_sql("DelSingle", "sqlite")
        assert a.expression == b.expression, (a.expression, b.expression)
        assert a.join_path == b.join_path == ["receiving.po_id = purchase_order.po_id"]
        # The substituted expression uses real table-qualified columns, no {vars}.
        assert "{" not in a.expression and "}" not in a.expression
        assert "receiving.receipt_date" in a.expression
        assert "purchase_order.required_date" in a.expression
        # Re-assembling is deterministic.
        assert eng.assemble_metric_sql("DelFanout", "sqlite").sql == a.sql


def test_single_table_has_no_join():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        r = eng.assemble_metric_sql("OEEish", "sqlite")
        assert r.tables == ["operation"], r.tables
        assert r.join_path == [], r.join_path
        assert "FROM operation" in r.sql
        assert "JOIN" not in r.sql.upper()


def test_cross_dialect_transpile_is_valid_and_stable():
    import sqlglot
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        lite = eng.assemble_metric_sql("DelSingle", "sqlite")
        # Every target dialect parses cleanly and keeps the qualified columns.
        for dialect in ("tsql", "postgres", "mysql", "bigquery"):
            r = eng.assemble_metric_sql("DelSingle", dialect)
            assert r.sql, f"empty SQL for {dialect}"
            sqlglot.parse_one(r.sql, read=dialect)  # raises on invalid SQL
            assert "receiving.receipt_date" in r.sql
        # The SQLite form also parses as SQLite.
        sqlglot.parse_one(lite.sql, read="sqlite")


def test_static_template_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        try:
            eng.assemble_metric_sql("StaticMetric", "sqlite")
        except MetricAssemblyError as e:
            assert "static" in str(e).lower() or "placeholder" in str(e).lower()
            return
        raise AssertionError("static (variable-free) template must fail closed")


def test_missing_binding_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        try:
            eng.assemble_metric_sql("MissingBind", "sqlite")
        except MetricAssemblyError as e:
            assert "missing" in str(e).lower()
            return
        raise AssertionError("a placeholder with no binding must fail closed")


def test_conflicting_binding_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "fx.db")
        _build_fixture_db(db)
        eng = SolderEngine(db_path=db)
        try:
            eng.assemble_metric_sql("ConflictMetric", "sqlite")
        except MetricAssemblyError as e:
            assert "conflict" in str(e).lower()
            return
        raise AssertionError("one variable bound to two columns must fail closed")


# ── meta-context overlay tests ──────────────────────────────────────────────

def test_table_description_overlay_roundtrip():
    import table_description_pipeline as tdp
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "ov.db")
        csv_path = os.path.join(d, "table_descriptions.csv")
        rows = [{
            "table_name": "receiving",
            "display_name": "Goods Receipt",
            "description": "One row per goods receipt.",
            "ai_context": "Fulfillment side of delivery performance.",
        }]
        tdp.write_descriptions_csv(rows, csv_path=csv_path)
        res = tdp.load_descriptions_from_csv(csv_path=csv_path, db_path=db)
        assert res.get("ok") and res.get("loaded") == 1, res
        got = tdp.get_table_description("receiving", db_path=db)
        assert got["display_name"] == "Goods Receipt"
        assert got["ai_context"] == "Fulfillment side of delivery performance."
        # Idempotent: loading twice does not duplicate or change the row.
        tdp.load_descriptions_from_csv(csv_path=csv_path, db_path=db)
        again = tdp.get_table_description("receiving", db_path=db)
        assert again == got


def test_overlay_never_written_to_graph_nodes():
    """The overlay is meta-context only: no graph node may carry ai_context, and
    graph_metadata.json must not gain table-description fields."""
    gm_path = os.path.join(REPO_ROOT, "replit_integrations", "graph_metadata.json")
    if not os.path.exists(gm_path):
        print("SKIP: graph_metadata.json not present")
        return
    with open(gm_path, encoding="utf-8") as fh:
        gm = json.load(fh)
    nodes = gm.get("nodes", [])
    assert nodes, "graph_metadata.json has no nodes"
    for n in nodes:
        assert "ai_context" not in n, f"node leaked overlay field ai_context: {n.get('unique_id')}"


# ── real-DB integration (skips when the gitignored app DB is absent) ─────────

SHOWCASE = [
    "DeliveryPerformanceOps",
    "DeliveryPerformanceSupplier",
    "DeliveryPerformanceFinance",
    "OEEOperational",
    "OEEStrategic",
]


def _real_db_path():
    p = os.path.join(HF_DIR, "app_schema", "manufacturing.db")
    return p if os.path.exists(p) else None


def test_showcase_metrics_assemble_on_real_db():
    db = _real_db_path()
    if not db:
        print("SKIP: app DB not present")
        return
    eng = SolderEngine(db_path=db)
    listed = {m["concept_name"] for m in eng.list_metrics()}
    for name in SHOWCASE:
        assert name in listed, f"showcase metric {name} missing from real DB"
        r = eng.assemble_metric_sql(name, "sqlite")
        assert r.sql.strip().upper().startswith("SELECT"), r.sql
        assert "{" not in r.expression, r.expression


def test_real_delivery_metrics_define_once():
    db = _real_db_path()
    if not db:
        print("SKIP: app DB not present")
        return
    eng = SolderEngine(db_path=db)
    exprs = {n: eng.assemble_metric_sql(n, "sqlite").expression
             for n in SHOWCASE[:3]}
    distinct = set(exprs.values())
    assert len(distinct) == 1, f"delivery metrics diverged: {exprs}"


def main() -> int:
    tests = [
        test_template_storage_lists_only_metrics_with_templates,
        test_bindings_dedup_and_lineage,
        test_define_once_and_fanout_yield_identical_sql,
        test_single_table_has_no_join,
        test_cross_dialect_transpile_is_valid_and_stable,
        test_static_template_fails_closed,
        test_missing_binding_fails_closed,
        test_conflicting_binding_fails_closed,
        test_table_description_overlay_roundtrip,
        test_overlay_never_written_to_graph_nodes,
        test_showcase_metrics_assemble_on_real_db,
        test_real_delivery_metrics_define_once,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
