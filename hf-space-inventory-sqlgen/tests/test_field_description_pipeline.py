"""Tests for field_description_pipeline.

Uses a temp SQLite file with a small business table plus the two overlay tables
(api_field_descriptions, dab_field_definitions) so no live database is required.

Coverage:
- humanize() expands snake_case + known abbreviations.
- deterministic_draft() returns display_name / description / example_value and
  flags a bounded column as categorical.
- upsert_field_description() is idempotent (second call -> still one row, updated).
- certify_field_definition() writes certified=1 into dab_field_definitions.
- list_business_columns() excludes metadata + staging tables.
- fill_missing() drafts only undescribed columns and preserves existing ones.

Run:
    python hf-space-inventory-sqlgen/tests/test_field_description_pipeline.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

import field_description_pipeline as p  # noqa: E402

_SRC_DB = "test_manufacturing"
_SCHEMA = "dbo"


def _make_db() -> str:
    """Build a temp DB: one business table, one staging table, two overlay tables."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE work_order (
            work_order_id INTEGER PRIMARY KEY,
            status        TEXT,
            quantity      INTEGER
        );
        CREATE TABLE stg_raw (x TEXT);
        CREATE TABLE api_field_descriptions (
            source_database TEXT, schema_name TEXT,
            table_name TEXT, column_name TEXT,
            display_name TEXT, description TEXT, example_value TEXT,
            updated_at TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        CREATE TABLE dab_field_definitions (
            source_database TEXT, schema_name TEXT,
            table_name TEXT, column_name TEXT,
            field_definition TEXT, certified INTEGER DEFAULT 0,
            updated_at TEXT,
            PRIMARY KEY (source_database, schema_name, table_name, column_name)
        );
        INSERT INTO work_order (work_order_id, status, quantity) VALUES
            (1, 'OPEN', 10), (2, 'CLOSED', 5), (3, 'OPEN', 7), (4, 'RELEASED', 1);
        """
    )
    conn.commit()
    conn.close()
    return db_path


def _row_count(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_humanize():
    assert p.humanize("three_way_match_status") == "Three Way Match Status"
    assert p.humanize("order_qty") == "Order Quantity"
    assert p.humanize("customer_id") == "Customer ID"
    print("PASS: humanize expands snake_case + abbreviations")


def test_deterministic_draft_categorical():
    db = _make_db()
    try:
        d = p.deterministic_draft("work_order", "status", db_path=db)
        assert d["display_name"] == "Status", d
        assert d["_source"] == "deterministic"
        assert d["example_value"] in {"OPEN", "CLOSED", "RELEASED"}, d
        # Bounded column -> lists observed values in plain language (no SQL jargon).
        low = d["description"].lower()
        assert "small set of values" in low, d["description"]
        assert "open" in low, d["description"]
        print("PASS: deterministic_draft lists observed values for a bounded column")
    finally:
        os.unlink(db)


def test_deterministic_draft_pk():
    db = _make_db()
    try:
        d = p.deterministic_draft("work_order", "work_order_id", db_path=db)
        assert "unique identifier" in d["description"].lower(), d["description"]
        print("PASS: deterministic_draft describes a PK column")
    finally:
        os.unlink(db)


def test_deterministic_draft_no_sql_jargon():
    """Drafts must read in plain business language — never leak SQL types."""
    db = _make_db()
    try:
        for col in ("status", "quantity", "work_order_id"):
            desc = p.deterministic_draft("work_order", col, db_path=db)["description"]
            low = desc.lower()
            assert desc, f"{col}: description must be non-empty"
            for jargon in ("integer", "text", "real", "varchar", "field on"):
                assert jargon not in low, f"{col}: leaked SQL jargon {jargon!r}: {desc}"
        # quantity is numeric -> a 'numeric ... recorded' measure draft.
        q = p.deterministic_draft("work_order", "quantity", db_path=db)["description"]
        assert "numeric" in q.lower(), q
        print("PASS: deterministic drafts are plain language with no SQL jargon")
    finally:
        os.unlink(db)


def test_upsert_idempotent():
    db = _make_db()
    try:
        r1 = p.upsert_field_description(
            "work_order", "status", "Work Order Status", "first", "OPEN",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r1["ok"], r1
        assert _row_count(db, "api_field_descriptions") == 1
        r2 = p.upsert_field_description(
            "work_order", "status", "Work Order Status", "second", "CLOSED",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert r2["ok"], r2
        assert _row_count(db, "api_field_descriptions") == 1, "upsert must not duplicate"
        conn = sqlite3.connect(db)
        desc = conn.execute(
            "SELECT description FROM api_field_descriptions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()[0]
        conn.close()
        assert desc == "second", f"second upsert must overwrite, got {desc!r}"
        print("PASS: upsert_field_description is idempotent and updates in place")
    finally:
        os.unlink(db)


def test_certify_writes_dab():
    db = _make_db()
    try:
        res = p.certify_field_definition(
            "work_order", "status", "Shop-floor lifecycle stage.", certified=True,
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert res["ok"], res
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT field_definition, certified FROM dab_field_definitions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()
        conn.close()
        assert row is not None, "certify must insert a dab_field_definitions row"
        assert row[0] == "Shop-floor lifecycle stage.", row
        assert row[1] == 1, "certified flag must be 1"
        print("PASS: certify_field_definition writes certified=1 to dab_field_definitions")
    finally:
        os.unlink(db)


def test_list_business_columns_excludes_metadata_and_staging():
    db = _make_db()
    try:
        cols = p.list_business_columns(db_path=db)
        tables = {t for t, _ in cols}
        assert "work_order" in tables, tables
        assert "stg_raw" not in tables, "staging tables must be excluded"
        assert "api_field_descriptions" not in tables, "metadata tables must be excluded"
        assert "dab_field_definitions" not in tables, "metadata tables must be excluded"
        print("PASS: list_business_columns excludes metadata + staging tables")
    finally:
        os.unlink(db)


def test_fill_missing_preserves_existing():
    db = _make_db()
    try:
        # Pre-seed one column with a curated value.
        p.upsert_field_description(
            "work_order", "status", "Curated Status", "DO NOT OVERWRITE", "OPEN",
            db_path=db, source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        filled = p.fill_missing(
            db_path=db, use_ai=False,
            source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        # work_order has 3 columns; status pre-seeded -> 2 newly drafted.
        assert filled == 2, f"expected 2 newly drafted, got {filled}"
        conn = sqlite3.connect(db)
        preserved = conn.execute(
            "SELECT description FROM api_field_descriptions "
            "WHERE table_name='work_order' AND column_name='status'"
        ).fetchone()[0]
        conn.close()
        assert preserved == "DO NOT OVERWRITE", f"curated row must be preserved, got {preserved!r}"
        print("PASS: fill_missing drafts only gaps and preserves existing rows")
    finally:
        os.unlink(db)


def test_compute_field_coverage_overall():
    """compute_field_coverage aggregates described/certified across ALL tables."""
    schema = {
        "work_order": {
            "id": {"description": "Primary key", "certified": True},
            "status": {"description": "State", "certified": False},
            "notes": {"description": "", "certified": False},
        },
        "supplier": {
            "id": {"description": "Primary key", "certified": True},
            "name": {"description": None},
        },
        "empty_table": {},
    }
    cov = p.compute_field_coverage(schema)
    assert cov["tables"] == 3, f"expected 3 tables, got {cov['tables']}"
    assert cov["columns"] == 5, f"expected 5 columns, got {cov['columns']}"
    assert cov["described"] == 3, f"expected 3 described, got {cov['described']}"
    assert cov["certified"] == 2, f"expected 2 certified, got {cov['certified']}"
    # Empty schema must not divide-by-zero or crash.
    empty = p.compute_field_coverage({})
    assert empty == {"tables": 0, "columns": 0, "described": 0, "certified": 0}
    print("PASS: compute_field_coverage aggregates overall coverage correctly")


def test_kb_context_selective():
    """kb_context_for pulls only column-relevant lines, caps length, else ''."""
    fd, doc = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write(
            "Intro line with no column refs.\n"
            "`part.reorder_point` is the level that triggers replenishment.\n"
            "Another note about part:reorder_point and its perspective.\n"
            "Unrelated line about shipping schedules.\n"
        )
    try:
        ctx = p.kb_context_for("part", "reorder_point", doc_paths=(doc,))
        assert "reorder_point" in ctx.lower(), ctx
        assert "shipping schedules" not in ctx, "must not pull unrelated lines"
        # No match -> empty string (prompt stays unchanged / cheap).
        assert p.kb_context_for("invoice_header", "total", doc_paths=(doc,)) == ""
        # Char cap is respected.
        capped = p.kb_context_for("part", "reorder_point", doc_paths=(doc,), max_chars=20)
        assert len(capped) <= 20, capped
        print("PASS: kb_context_for selects column-relevant lines and caps length")
    finally:
        os.unlink(doc)


def test_csv_round_trip():
    """write_descriptions_csv -> read_descriptions_csv preserves rows, sorted."""
    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    os.unlink(csv_path)
    try:
        rows = [
            {"table_name": "work_order", "column_name": "status",
             "display_name": "Work Order Status", "description": "Lifecycle stage.",
             "example_value": "OPEN"},
            {"table_name": "certification", "column_name": "cert_id",
             "display_name": "Certification ID", "description": "Unique id.",
             "example_value": "1"},
        ]
        n = p.write_descriptions_csv(rows, csv_path=csv_path)
        assert n == 2, n
        back = p.read_descriptions_csv(csv_path)
        # Sorted by (table, column): certification before work_order.
        assert [(r["table_name"], r["column_name"]) for r in back] == [
            ("certification", "cert_id"), ("work_order", "status")
        ], back
        assert back[1]["description"] == "Lifecycle stage.", back[1]
        # Missing file -> [] (never raises).
        assert p.read_descriptions_csv(csv_path + ".nope") == []
        print("PASS: CSV write/read round-trips and sorts by (table, column)")
    finally:
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def test_load_descriptions_from_csv_upserts():
    """load_descriptions_from_csv upserts CSV rows into api_field_descriptions."""
    db = _make_db()
    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        p.write_descriptions_csv([
            {"table_name": "work_order", "column_name": "status",
             "display_name": "Work Order Status", "description": "Lifecycle stage.",
             "example_value": "OPEN"},
        ], csv_path=csv_path)
        res = p.load_descriptions_from_csv(
            csv_path=csv_path, db_path=db,
            source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert res["ok"] and res["loaded"] == 1, res
        # Re-loading is idempotent (no duplicate rows).
        p.load_descriptions_from_csv(
            csv_path=csv_path, db_path=db,
            source_database=_SRC_DB, schema_name=_SCHEMA,
        )
        assert _row_count(db, "api_field_descriptions") == 1, "must not duplicate"
        print("PASS: load_descriptions_from_csv upserts idempotently")
    finally:
        os.unlink(db)
        if os.path.exists(csv_path):
            os.unlink(csv_path)


def _graph_metadata_path() -> str:
    return os.path.normpath(
        os.path.join(HF_DIR, "..", "replit_integrations", "graph_metadata.json")
    )


def test_graph_columns_fully_covered():
    """Every canonical-graph column node has a non-empty description in the CSV."""
    graph_path = _graph_metadata_path()
    csv_path = os.path.normpath(os.path.join(HF_DIR, "..", "field_descriptions.csv"))
    if not (os.path.exists(graph_path) and os.path.exists(csv_path)):
        print("SKIP: graph_metadata.json or field_descriptions.csv not present")
        return
    cov = p.compute_graph_coverage(csv_path, graph_path)
    assert cov["described"] == cov["total"], (
        f"missing {len(cov['missing'])} description(s): {cov['missing'][:5]}"
    )
    assert not cov["extra"], f"CSV has non-graph rows: {cov['extra'][:5]}"
    assert not cov["duplicates"], f"CSV has duplicate keys: {cov['duplicates'][:5]}"
    print(f"PASS: all {cov['total']} graph column nodes are described in the CSV")


def test_coverage_flags_duplicate_csv_keys():
    """A duplicated (table,column) row must be reported, not silently de-duped.

    Set-based "exact" coverage could otherwise let a stale/conflicting second row
    slip through. compute_graph_coverage() must surface it in `duplicates`.
    """
    import csv
    import tempfile
    graph_path = _graph_metadata_path()
    if not os.path.exists(graph_path):
        print("SKIP: graph_metadata.json not present")
        return
    keys = p.graph_column_keys(graph_path)
    assert keys, "expected at least one graph column key"
    fd, tmp_csv = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        rows = [
            {"table_name": t, "column_name": c, "description": f"{t} {c} value"}
            for (t, c) in keys
        ]
        rows.append(dict(rows[0]))  # duplicate the first key
        with open(tmp_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=p.CSV_COLUMNS)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in p.CSV_COLUMNS})
        cov = p.compute_graph_coverage(tmp_csv, graph_path)
        assert cov["duplicates"] == [keys[0]], (
            f"expected duplicate {keys[0]!r}, got {cov['duplicates']!r}"
        )
        assert not cov["missing"] and not cov["extra"]
    finally:
        os.remove(tmp_csv)
    print("PASS: compute_graph_coverage flags duplicate CSV keys")


def test_graph_column_nodes_have_no_description_key():
    """GUARDRAIL: descriptions are overlay-only — never written onto graph nodes.

    Column nodes in graph_metadata.json must NOT carry a `description` key (table
    nodes legitimately do). This keeps the canonical graph byte-stable.
    """
    import json
    graph_path = _graph_metadata_path()
    if not os.path.exists(graph_path):
        print("SKIP: graph_metadata.json not present")
        return
    with open(graph_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    offenders = [
        (n.get("table_name"), n.get("column_name"))
        for n in meta.get("nodes", [])
        if n.get("node_type") == "column" and "description" in n
    ]
    assert not offenders, f"column nodes must not carry descriptions: {offenders[:5]}"
    print("PASS: no column node carries a description key (overlay-only guardrail)")


def main() -> int:
    tests = [
        test_humanize,
        test_deterministic_draft_categorical,
        test_deterministic_draft_pk,
        test_deterministic_draft_no_sql_jargon,
        test_upsert_idempotent,
        test_certify_writes_dab,
        test_list_business_columns_excludes_metadata_and_staging,
        test_fill_missing_preserves_existing,
        test_compute_field_coverage_overall,
        test_kb_context_selective,
        test_csv_round_trip,
        test_load_descriptions_from_csv_upserts,
        test_graph_columns_fully_covered,
        test_coverage_flags_duplicate_csv_keys,
        test_graph_column_nodes_have_no_description_key,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            print(f"FAIL: {t.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {t.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    print()
    print(f"{'PASS' if failed == 0 else 'FAIL'}: {len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
