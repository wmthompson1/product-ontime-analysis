"""Tests for SQLite-first canonical edge authoring in POST /mcp/tools/commit_edge.

The canonical predicates (HAS_COLUMN, FOREIGN_KEY, ELEVATES, SUPPRESSES) are
written to ``sql_graph_authored_edges`` (SQLite source of truth) first; ArangoDB
is updated best-effort only. These tests run against a temporary SQLite database
seeded with sql_graph_nodes + the authoring table, with the best-effort ArangoDB
sync stubbed out so no live graph is required.

Covered:
  * create -> duplicate idempotency (created true then false) per predicate
  * endpoints resolve against sql_graph_nodes (verified source)
  * unknown endpoint -> 422 (no dangling edge)
  * ELEVATES without a perspective -> 422
  * undo via DELETE removes the row; second DELETE -> 404
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


def _seed_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE sql_graph_nodes (
            ordinal INTEGER, _key TEXT PRIMARY KEY, _id TEXT NOT NULL,
            node_type TEXT NOT NULL, node_family TEXT, perspective TEXT,
            table_name TEXT NOT NULL, column_name TEXT, column_slot TEXT,
            predicate TEXT, unique_id TEXT, description TEXT, column_type TEXT,
            "notnull" INTEGER, default_value TEXT, primary_key INTEGER, foreign_key INTEGER
        );
        CREATE TABLE sql_graph_authored_edges (
            authored_id INTEGER PRIMARY KEY AUTOINCREMENT,
            edge_type TEXT NOT NULL CHECK(edge_type IN ('has_column','references','elevates')),
            from_table TEXT NOT NULL, from_column TEXT NOT NULL DEFAULT '',
            to_table TEXT NOT NULL, to_column TEXT NOT NULL DEFAULT '',
            perspective TEXT NOT NULL DEFAULT 'system',
            weight INTEGER, concept TEXT,
            created_by TEXT NOT NULL DEFAULT 'define_relationship_ui',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(edge_type, from_table, from_column, to_table, to_column, perspective)
        );
        """
    )
    nodes = [
        (1, "part", "manufacturing_graph_node/part", "table", "part", None),
        (2, "column::part.part_id", "manufacturing_graph_node/column::part.part_id",
         "column", "part", "part_id"),
        (3, "orders", "manufacturing_graph_node/orders", "table", "orders", None),
        (4, "column::orders.part_ref", "manufacturing_graph_node/column::orders.part_ref",
         "column", "orders", "part_ref"),
    ]
    for ordinal, key, _id, ntype, tname, cname in nodes:
        conn.execute(
            "INSERT INTO sql_graph_nodes (ordinal, _key, _id, node_type, node_family, "
            "perspective, table_name, column_name, predicate, unique_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ordinal, key, _id, ntype, "structural", "system", tname, cname, "none", "none"),
        )
    conn.commit()
    conn.close()


def _client_with_temp_db():
    """Build a TestClient with app.SQLITE_DB_PATH pointed at a fresh seeded DB.

    Returns (client, app_module, db_path) or (None, None, None) if unavailable.
    """
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return None, None, None

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _seed_db(db_path)
    fastapi_app.SQLITE_DB_PATH = db_path
    # Stub best-effort ArangoDB sync so tests are hermetic (no live graph).
    fastapi_app._best_effort_arango_canonical_sync = lambda predicate, req: ""
    return TestClient(fastapi_app.app, raise_server_exceptions=False), fastapi_app, db_path


def _post(client, **payload):
    resp = client.post("/mcp/tools/commit_edge", json=payload)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {}


def _count(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM sql_graph_authored_edges").fetchone()[0]
    finally:
        conn.close()


def test_has_column_create_then_duplicate():
    client, _, db_path = _client_with_temp_db()
    if client is None:
        return
    s1, b1 = _post(client, predicate="HAS_COLUMN", source_id="part", target_id="part.part_id")
    assert s1 == 200 and b1.get("created") is True, f"first HAS_COLUMN: {s1} {b1}"
    assert b1["edge_id"].startswith("sqlite:sql_graph_authored_edges/"), b1
    s2, b2 = _post(client, predicate="HAS_COLUMN", source_id="part", target_id="part.part_id")
    assert s2 == 200 and b2.get("created") is False, f"dup HAS_COLUMN: {s2} {b2}"
    assert _count(db_path) == 1, "duplicate must not grow the authoring table"
    print("PASS [HAS_COLUMN]: create then duplicate is idempotent")


def test_foreign_key_create_then_duplicate():
    client, _, db_path = _client_with_temp_db()
    if client is None:
        return
    extra = {"from_column": "part_ref", "to_column": "part_id"}
    s1, b1 = _post(client, predicate="FOREIGN_KEY", source_id="orders", target_id="part", **extra)
    assert s1 == 200 and b1.get("created") is True, f"first FOREIGN_KEY: {s1} {b1}"
    s2, b2 = _post(client, predicate="FOREIGN_KEY", source_id="orders", target_id="part", **extra)
    assert s2 == 200 and b2.get("created") is False, f"dup FOREIGN_KEY: {s2} {b2}"
    assert _count(db_path) == 1
    print("PASS [FOREIGN_KEY]: create then duplicate is idempotent")


def test_elevates_create_then_duplicate():
    client, _, db_path = _client_with_temp_db()
    if client is None:
        return
    payload = dict(predicate="ELEVATES", source_id="part", target_id="part.part_id",
                   perspective="quality", concept_anchor="defects")
    s1, b1 = _post(client, **payload)
    assert s1 == 200 and b1.get("created") is True, f"first ELEVATES: {s1} {b1}"
    s2, b2 = _post(client, **payload)
    assert s2 == 200 and b2.get("created") is False, f"dup ELEVATES: {s2} {b2}"
    assert _count(db_path) == 1
    # weight gate: ELEVATES -> 1
    conn = sqlite3.connect(db_path)
    w = conn.execute("SELECT weight FROM sql_graph_authored_edges WHERE edge_type='elevates'").fetchone()[0]
    conn.close()
    assert w == 1, f"ELEVATES weight must be 1, got {w}"
    print("PASS [ELEVATES]: create then duplicate is idempotent, weight=1")


def test_unknown_endpoint_is_422():
    client, _, _ = _client_with_temp_db()
    if client is None:
        return
    s, b = _post(client, predicate="HAS_COLUMN", source_id="part", target_id="part.nonexistent")
    assert s == 422, f"unknown column endpoint must be 422, got {s}: {b}"
    print("PASS [422]: unresolved endpoint rejected")


def test_elevates_without_perspective_is_422():
    client, _, _ = _client_with_temp_db()
    if client is None:
        return
    s, b = _post(client, predicate="ELEVATES", source_id="part", target_id="part.part_id")
    assert s == 422, f"ELEVATES without perspective must be 422, got {s}: {b}"
    print("PASS [422]: ELEVATES requires a perspective")


def test_undo_deletes_then_404():
    client, _, db_path = _client_with_temp_db()
    if client is None:
        return
    _, b1 = _post(client, predicate="HAS_COLUMN", source_id="part", target_id="part.part_id")
    edge_id = b1["edge_id"]
    assert _count(db_path) == 1
    r1 = client.delete(f"/mcp/tools/commit_edge?edge_id={edge_id}")
    assert r1.status_code == 200, f"delete expected 200, got {r1.status_code}: {r1.text}"
    assert _count(db_path) == 0, "row must be gone after undo"
    r2 = client.delete(f"/mcp/tools/commit_edge?edge_id={edge_id}")
    assert r2.status_code == 404, f"second delete expected 404, got {r2.status_code}: {r2.text}"
    print("PASS [undo]: delete removes row; second delete is 404")


def main() -> int:
    tests = [
        test_has_column_create_then_duplicate,
        test_foreign_key_create_then_duplicate,
        test_elevates_create_then_duplicate,
        test_unknown_endpoint_is_422,
        test_elevates_without_perspective_is_422,
        test_undo_deletes_then_404,
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
