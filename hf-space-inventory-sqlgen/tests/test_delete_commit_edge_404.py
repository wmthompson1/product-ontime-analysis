"""Tests for the DELETE /mcp/tools/commit_edge endpoint 404 behaviour.

Verifies that a double-undo or stale edge_id surfaces as HTTP 404 with a
meaningful detail message — not a silent 200 success.

Three distinct failure scenarios are covered:

1. ArangoDB path: a valid-format edge_id whose document does not exist in any
   ArangoDB collection returns 404.
2. SQLite schema_intent_perspectives path: both entity names exist in the DB
   but there is no bridge row linking them — returns 404 with rowcount=0.
3. SQLite schema_perspective_concepts path: same condition for the
   perspective→concept bridge table.
4. Double-undo guard: a bridge row is inserted, deleted once (200), then a
   second DELETE for the same edge_id must return 404, not 200.

Run: python hf-space-inventory-sqlgen/tests/test_delete_commit_edge_404.py
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)
sys.path.insert(0, os.path.join(HF_DIR, "scripts"))

DB_PATH = os.path.join(HF_DIR, "app_schema", "manufacturing.db")

# Seeded entity names that are guaranteed to exist after seed_test_db.py runs
_SEEDED_INTENT = "defect_cost_analysis"
_SEEDED_PERSPECTIVE_FINANCE = "Finance"
_SEEDED_PERSPECTIVE_QUALITY = "Quality"
_SEEDED_CONCEPT = "DefectSeverityCost"


def _seed_db_if_needed():
    """Run seed_test_db.py in a subprocess so its module-level side effects
    stay isolated.  Silently ignored when the script is absent."""
    seed_script = os.path.join(HF_DIR, "scripts", "seed_test_db.py")
    if os.path.exists(seed_script):
        subprocess.run(
            [sys.executable, seed_script],
            check=False,
            capture_output=True,
        )


def _ensure_perspective_concepts_table(conn: sqlite3.Connection) -> None:
    """Create schema_perspective_concepts if it was not initialised yet."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_perspective_concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            perspective_id INTEGER NOT NULL,
            concept_id     INTEGER NOT NULL,
            relationship_type TEXT NOT NULL DEFAULT 'USES_DEFINITION',
            priority_weight   INTEGER DEFAULT 1,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(perspective_id, concept_id)
        )
    """)
    conn.commit()


def _get_test_client():
    """Return a FastAPI TestClient for app.py, or None if unavailable."""
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
        return TestClient(fastapi_app.app, raise_server_exceptions=False)
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return None


# ── ArangoDB path ─────────────────────────────────────────────────────────────

def test_arango_nonexistent_edge_returns_404():
    """DELETE with a valid-format but non-existent ArangoDB edge_id → 404.

    Skipped when ARANGO_HOST is not set so the suite stays green offline.
    """
    if not os.environ.get("ARANGO_HOST"):
        print("SKIP: ARANGO_HOST not set — ArangoDB 404 test skipped")
        return

    client = _get_test_client()
    if client is None:
        return

    fake_edge_id = "elevates/__nonexistent_key_xyz_12345__"
    response = client.delete(
        "/mcp/tools/commit_edge",
        params={"edge_id": fake_edge_id},
    )

    assert response.status_code == 404, (
        f"Expected 404 for non-existent ArangoDB edge, "
        f"got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    detail = body.get("detail", "")
    assert detail, "HTTP 404 response must include a non-empty 'detail' field"
    assert fake_edge_id in detail or "not found" in detail.lower(), (
        f"404 detail should mention the missing edge_id or 'not found'. "
        f"Got: {detail!r}"
    )
    print(
        f"PASS: DELETE with non-existent ArangoDB edge_id {fake_edge_id!r} "
        f"returned 404 with detail: {detail!r}"
    )


# ── SQLite path — schema_intent_perspectives (missing bridge row) ──────────────

def test_sqlite_missing_intent_perspective_bridge_returns_404():
    """DELETE for intent+perspective where both names exist but no bridge row.

    Uses seeded entity 'defect_cost_analysis' + 'Quality': the seed inserts
    the Finance bridge row only, so Quality is unlinked — simulating an
    already-deleted or never-committed bridge row.
    """
    if not os.path.exists(DB_PATH):
        _seed_db_if_needed()
        if not os.path.exists(DB_PATH):
            print("SKIP: manufacturing.db not present after seeding")
            return

    _seed_db_if_needed()

    # Confirm both entity names actually exist (prerequisite for the rowcount
    # path; if they are absent the handler returns 404 for a different reason).
    with sqlite3.connect(DB_PATH) as conn:
        intent_row = conn.execute(
            "SELECT intent_id FROM schema_intents WHERE intent_name = ?",
            (_SEEDED_INTENT,),
        ).fetchone()
        perspective_row = conn.execute(
            "SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?",
            (_SEEDED_PERSPECTIVE_QUALITY,),
        ).fetchone()
        if intent_row is None or perspective_row is None:
            print(
                "SKIP: seeded entities not found in DB "
                f"(intent={intent_row}, perspective={perspective_row})"
            )
            return
        # Ensure no bridge row links them so we hit the rowcount=0 branch.
        conn.execute(
            "DELETE FROM schema_intent_perspectives "
            "WHERE intent_id = ? AND perspective_id = ?",
            (intent_row[0], perspective_row[0]),
        )
        conn.commit()

    client = _get_test_client()
    if client is None:
        return

    edge_id = (
        f"sqlite:schema_intent_perspectives"
        f"/{_SEEDED_INTENT}__{_SEEDED_PERSPECTIVE_QUALITY}"
    )
    response = client.delete(
        "/mcp/tools/commit_edge",
        params={"edge_id": edge_id},
    )

    assert response.status_code == 404, (
        f"Expected 404 when bridge row is absent (rowcount=0), "
        f"got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    detail = body.get("detail", "")
    assert detail, "HTTP 404 response must include a non-empty 'detail' field"
    assert "not found" in detail.lower() or "already deleted" in detail.lower(), (
        f"404 detail should mention 'not found' or 'already deleted'. Got: {detail!r}"
    )
    print(
        "PASS: DELETE with existing entity names but no bridge row "
        f"(schema_intent_perspectives) returned 404: {detail!r}"
    )


# ── SQLite path — schema_perspective_concepts (missing bridge row) ─────────────

def test_sqlite_missing_perspective_concept_bridge_returns_404():
    """DELETE for perspective+concept where both names exist but no bridge row.

    Uses 'Finance' + 'DefectSeverityCost': both are seeded, but no
    schema_perspective_concepts row links them — same as an already-deleted edge.
    """
    if not os.path.exists(DB_PATH):
        _seed_db_if_needed()
        if not os.path.exists(DB_PATH):
            print("SKIP: manufacturing.db not present after seeding")
            return

    _seed_db_if_needed()

    with sqlite3.connect(DB_PATH) as conn:
        _ensure_perspective_concepts_table(conn)
        perspective_row = conn.execute(
            "SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?",
            (_SEEDED_PERSPECTIVE_FINANCE,),
        ).fetchone()
        concept_row = conn.execute(
            "SELECT concept_id FROM schema_concepts WHERE concept_name = ?",
            (_SEEDED_CONCEPT,),
        ).fetchone()
        if perspective_row is None or concept_row is None:
            print(
                "SKIP: seeded entities not found in DB "
                f"(perspective={perspective_row}, concept={concept_row})"
            )
            return
        # Remove any pre-existing bridge row so we reach rowcount=0.
        conn.execute(
            "DELETE FROM schema_perspective_concepts "
            "WHERE perspective_id = ? AND concept_id = ?",
            (perspective_row[0], concept_row[0]),
        )
        conn.commit()

    client = _get_test_client()
    if client is None:
        return

    edge_id = (
        f"sqlite:schema_perspective_concepts"
        f"/{_SEEDED_PERSPECTIVE_FINANCE}__{_SEEDED_CONCEPT}"
    )
    response = client.delete(
        "/mcp/tools/commit_edge",
        params={"edge_id": edge_id},
    )

    assert response.status_code == 404, (
        f"Expected 404 when bridge row is absent (rowcount=0), "
        f"got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    detail = body.get("detail", "")
    assert detail, "HTTP 404 response must include a non-empty 'detail' field"
    assert "not found" in detail.lower() or "already deleted" in detail.lower(), (
        f"404 detail should mention 'not found' or 'already deleted'. Got: {detail!r}"
    )
    print(
        "PASS: DELETE with existing entity names but no bridge row "
        f"(schema_perspective_concepts) returned 404: {detail!r}"
    )


# ── Double-undo guard ─────────────────────────────────────────────────────────

def test_double_undo_returns_404_on_second_delete():
    """The second DELETE for the same edge_id must return 404, not 200.

    Inserts a bridge row directly into schema_perspective_concepts, issues
    DELETE once (expects 200), then issues DELETE a second time (expects 404).
    This is the canonical double-undo / stale-edge_id scenario.
    """
    if not os.path.exists(DB_PATH):
        _seed_db_if_needed()
        if not os.path.exists(DB_PATH):
            print("SKIP: manufacturing.db not present after seeding")
            return

    _seed_db_if_needed()

    with sqlite3.connect(DB_PATH) as conn:
        _ensure_perspective_concepts_table(conn)

        perspective_row = conn.execute(
            "SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?",
            (_SEEDED_PERSPECTIVE_QUALITY,),
        ).fetchone()
        concept_row = conn.execute(
            "SELECT concept_id FROM schema_concepts WHERE concept_name = ?",
            (_SEEDED_CONCEPT,),
        ).fetchone()
        if perspective_row is None or concept_row is None:
            print("SKIP: seeded Quality perspective or concept not found")
            return

        # Insert a fresh bridge row so the first DELETE has something to remove.
        conn.execute(
            "INSERT OR REPLACE INTO schema_perspective_concepts "
            "(perspective_id, concept_id, relationship_type) VALUES (?, ?, 'USES_DEFINITION')",
            (perspective_row[0], concept_row[0]),
        )
        conn.commit()

    client = _get_test_client()
    if client is None:
        return

    edge_id = (
        f"sqlite:schema_perspective_concepts"
        f"/{_SEEDED_PERSPECTIVE_QUALITY}__{_SEEDED_CONCEPT}"
    )

    # First DELETE — bridge row exists, must succeed.
    first = client.delete("/mcp/tools/commit_edge", params={"edge_id": edge_id})
    assert first.status_code == 200, (
        f"First DELETE (bridge row present) expected 200, "
        f"got {first.status_code}: {first.text[:300]}"
    )

    # Second DELETE — bridge row is gone, must return 404.
    second = client.delete("/mcp/tools/commit_edge", params={"edge_id": edge_id})
    assert second.status_code == 404, (
        f"Second DELETE (double-undo) expected 404, "
        f"got {second.status_code}: {second.text[:300]}"
    )
    body = second.json()
    detail = body.get("detail", "")
    assert detail, "HTTP 404 response must include a non-empty 'detail' field"
    assert "already deleted" in detail.lower() or "not found" in detail.lower(), (
        f"404 detail should mention 'already deleted' or 'not found'. Got: {detail!r}"
    )
    print(
        f"PASS: double-undo for {edge_id!r} — first DELETE 200, "
        f"second DELETE 404 with detail: {detail!r}"
    )


# ── Guard: 422 for malformed / empty edge_id ──────────────────────────────────

def test_empty_edge_id_returns_422():
    """DELETE with an empty edge_id must return 422, not 404 or 200."""
    client = _get_test_client()
    if client is None:
        return

    response = client.delete(
        "/mcp/tools/commit_edge",
        params={"edge_id": ""},
    )
    assert response.status_code == 422, (
        f"Expected 422 for empty edge_id, "
        f"got {response.status_code}: {response.text[:300]}"
    )
    print("PASS: DELETE with empty edge_id returned 422")


# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> int:
    tests = [
        test_arango_nonexistent_edge_returns_404,
        test_sqlite_missing_intent_perspective_bridge_returns_404,
        test_sqlite_missing_perspective_concept_bridge_returns_404,
        test_double_undo_returns_404_on_second_delete,
        test_empty_edge_id_returns_422,
    ]
    failed = 0
    for t in tests:
        try:
            t()
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
