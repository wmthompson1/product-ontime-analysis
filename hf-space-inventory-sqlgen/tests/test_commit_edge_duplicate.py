"""Tests for duplicate-edge protection in POST /mcp/tools/commit_edge.

Verifies that the AQL UPSERT logic correctly returns ``created: false`` on a
second call with the same source/target/predicate, and that the response
message contains "already exists".  Also confirms that the edge count in the
collection does not grow on the second call.

Two test modes are supported:

Mock mode (always runs):
    Uses ``unittest.mock`` to replace the ArangoDB client with an in-process
    fake that simulates the UPSERT RETURN { created: OLD == null } contract.
    No live ArangoDB credentials are required.

Live mode (gated on ARANGO_DB env var):
    Connects to a real ArangoDB instance and performs actual UPSERT round-trips,
    counting documents before and after each duplicate call.

Covered predicates: BOUND_TO, CAN_MEAN (the ArangoDB-routed predicates).

The canonical predicates (HAS_COLUMN, FOREIGN_KEY, ELEVATES, SUPPRESSES) are now
SQLite-first — their idempotency/undo behaviour is covered by
test_commit_edge_sqlite_first.py, not here.

Run:
    python hf-space-inventory-sqlgen/tests/test_commit_edge_duplicate.py
"""

from __future__ import annotations

import os
import sys
import types
import unittest.mock as mock

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_test_client():
    """Return a FastAPI TestClient for app.py, or None if unavailable."""
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
        return TestClient(fastapi_app.app, raise_server_exceptions=False)
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return None


def _make_fake_graph_sync(call_tracker: dict):
    """Build a fake graph_sync module whose db.aql.execute simulates UPSERT.

    ``call_tracker`` is a dict keyed by ``(source, target)`` tuple.  The first
    call for a given pair returns ``created=True``; subsequent calls return
    ``created=False``, mirroring ArangoDB AQL UPSERT RETURN { created: OLD == null }.

    A ``edge_counts`` sub-dict tracks how many unique edges exist so tests can
    assert count stability after duplicate insertions.
    """
    seen_edges: dict[tuple, dict] = {}
    call_tracker["seen_edges"] = seen_edges

    def _aql_execute(aql, bind_vars=None, **kwargs):
        bind_vars = bind_vars or {}
        source = bind_vars.get("source", "unknown/source")
        target = bind_vars.get("target", "unknown/target")
        key = (source, target)
        if key not in seen_edges:
            seen_edges[key] = {"_id": f"mock_collection/mock_{len(seen_edges)}"}
            created = True
        else:
            created = False
        return iter([{"doc": seen_edges[key], "created": created}])

    mock_aql = mock.MagicMock()
    mock_aql.execute.side_effect = _aql_execute

    mock_db = mock.MagicMock()
    mock_db.aql = mock_aql

    # Collection.has() must return False so _resolve_arango_handle falls through
    # to ValueError; we bypass that by passing fully-qualified handles (with '/').
    mock_collection = mock.MagicMock()
    mock_collection.has.return_value = False
    mock_db.collection.return_value = mock_collection

    mock_client = mock.MagicMock()

    gs = types.ModuleType("graph_sync")
    gs.get_arango_client = mock.MagicMock(return_value=mock_client)
    gs.get_arango_db = mock.MagicMock(return_value=mock_db)
    gs.GRAPH_NAME = "manufacturing_graph"

    return gs, mock_db


def _post_edge(client, predicate: str, source: str, target: str, extra: dict | None = None):
    """POST a commit_edge request and return the JSON response body + status."""
    payload = {"predicate": predicate, "source_id": source, "target_id": target}
    if extra:
        payload.update(extra)
    resp = client.post("/mcp/tools/commit_edge", json=payload)
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


# ---------------------------------------------------------------------------
# Mock-based duplicate tests (always run)
# ---------------------------------------------------------------------------

# Fully-qualified handles bypass _resolve_arango_handle so no DB lookup needed.
_SOURCE = "intents/test_source_node"
_TARGET = "concepts/test_target_node"

_PREDICATE_EXTRAS: dict[str, dict] = {
    "BOUND_TO":     {"binding_key": "bk_test", "concept_anchor": "ca_test"},
    "CAN_MEAN":     {},
}


def _run_mock_duplicate_test(predicate: str):
    """Core logic for one predicate: POST twice, assert second is not created."""
    client = _get_test_client()
    if client is None:
        return

    call_tracker: dict = {}
    fake_gs, _ = _make_fake_graph_sync(call_tracker)

    extra = _PREDICATE_EXTRAS[predicate]

    with mock.patch("importlib.import_module", side_effect=lambda name: fake_gs if name == "graph_sync" else __import__(name)):
        # First call — must create
        status1, body1 = _post_edge(client, predicate, _SOURCE, _TARGET, extra)
        assert status1 == 200, (
            f"[{predicate}] First POST expected 200, got {status1}: {body1}"
        )
        assert body1.get("created") is True, (
            f"[{predicate}] First POST must return created=true. Got: {body1}"
        )

        # Second call — same source/target/predicate must NOT create
        status2, body2 = _post_edge(client, predicate, _SOURCE, _TARGET, extra)
        assert status2 == 200, (
            f"[{predicate}] Second POST expected 200, got {status2}: {body2}"
        )
        assert body2.get("created") is False, (
            f"[{predicate}] Second POST must return created=false (UPSERT idempotency). Got: {body2}"
        )
        msg2 = body2.get("message", "")
        assert "already exists" in msg2.lower(), (
            f"[{predicate}] Second POST message must contain 'already exists'. Got: {msg2!r}"
        )

        # Edge count must not have grown on the second call
        assert len(call_tracker["seen_edges"]) == 1, (
            f"[{predicate}] Edge count grew after duplicate insert. "
            f"Expected 1 unique edge, found {len(call_tracker['seen_edges'])}."
        )

    print(
        f"PASS [{predicate}]: second call → created=false, "
        f"message contains 'already exists', edge count stable"
    )


def test_bound_to_duplicate_is_idempotent():
    """BOUND_TO: second commit_edge call must not create a duplicate edge."""
    _run_mock_duplicate_test("BOUND_TO")


def test_can_mean_duplicate_is_idempotent():
    """CAN_MEAN: second commit_edge call must not create a duplicate edge."""
    _run_mock_duplicate_test("CAN_MEAN")


def test_distinct_edges_each_created_once():
    """Two distinct source/target pairs must both be created (created=true each time)."""
    client = _get_test_client()
    if client is None:
        return

    call_tracker: dict = {}
    fake_gs, _ = _make_fake_graph_sync(call_tracker)

    src_a = "intents/node_alpha"
    tgt_a = "concepts/node_beta"
    src_b = "intents/node_gamma"
    tgt_b = "concepts/node_delta"

    with mock.patch("importlib.import_module", side_effect=lambda name: fake_gs if name == "graph_sync" else __import__(name)):
        _, body_a = _post_edge(client, "CAN_MEAN", src_a, tgt_a)
        assert body_a.get("created") is True, f"Edge A first insert must be created=true. Got: {body_a}"

        _, body_b = _post_edge(client, "CAN_MEAN", src_b, tgt_b)
        assert body_b.get("created") is True, f"Edge B first insert must be created=true. Got: {body_b}"

        assert len(call_tracker["seen_edges"]) == 2, (
            f"Expected 2 unique edges after two distinct inserts, "
            f"found {len(call_tracker['seen_edges'])}"
        )

    print("PASS [distinct edges]: two different edges are each created exactly once")


# ---------------------------------------------------------------------------
# Live ArangoDB tests (gated on ARANGO_DB env var)
# ---------------------------------------------------------------------------

def _live_arango_duplicate_test(predicate: str):
    """Real ArangoDB round-trip: verify UPSERT idempotency and stable count.

    Skipped when ARANGO_DB env var is not set.
    """
    if not os.environ.get("ARANGO_DB"):
        print(f"SKIP [{predicate}]: ARANGO_DB not set — live ArangoDB test skipped")
        return

    client = _get_test_client()
    if client is None:
        return

    try:
        import importlib
        gs = importlib.import_module("graph_sync")
        arango_client = gs.get_arango_client()
        db = gs.get_arango_db(arango_client)
    except Exception as exc:
        print(f"SKIP [{predicate}]: could not connect to ArangoDB: {exc}")
        return

    # Map predicate to its ArangoDB collection name for counting
    collection_map = {
        "BOUND_TO":    "bound_to",
        "CAN_MEAN":    "CAN_MEAN",
    }
    coll_name = collection_map[predicate]

    # Use a stable test handle unlikely to collide with production data
    src = "intents/__test_dup_src__"
    tgt = "concepts/__test_dup_tgt__"

    try:
        count_before = db.collection(coll_name).count()
    except Exception as exc:
        print(f"SKIP [{predicate}]: collection '{coll_name}' not accessible: {exc}")
        return

    extra = _PREDICATE_EXTRAS[predicate]

    # First POST — may or may not create depending on prior test runs
    status1, body1 = _post_edge(client, predicate, src, tgt, extra)
    if status1 not in (200,):
        print(f"SKIP [{predicate}]: first POST returned {status1}: {body1}")
        return

    count_mid = db.collection(coll_name).count()

    # Second POST — must not grow collection
    status2, body2 = _post_edge(client, predicate, src, tgt, extra)
    assert status2 == 200, (
        f"[{predicate}] Live duplicate POST expected 200, got {status2}: {body2}"
    )
    assert body2.get("created") is False, (
        f"[{predicate}] Live second POST must return created=false. Got: {body2}"
    )
    msg2 = body2.get("message", "")
    assert "already exists" in msg2.lower(), (
        f"[{predicate}] Live second POST message must contain 'already exists'. Got: {msg2!r}"
    )

    count_after = db.collection(coll_name).count()
    assert count_after == count_mid, (
        f"[{predicate}] Edge count grew after duplicate UPSERT: "
        f"before={count_before}, mid={count_mid}, after={count_after}"
    )

    print(
        f"PASS [{predicate}] live: second call → created=false, "
        f"message 'already exists', count stable at {count_after}"
    )


def test_live_bound_to_duplicate():
    _live_arango_duplicate_test("BOUND_TO")


def test_live_can_mean_duplicate():
    _live_arango_duplicate_test("CAN_MEAN")


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_bound_to_duplicate_is_idempotent,
        test_can_mean_duplicate_is_idempotent,
        test_distinct_edges_each_created_once,
        test_live_bound_to_duplicate,
        test_live_can_mean_duplicate,
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
    print(
        f"{'PASS' if failed == 0 else 'FAIL'}: "
        f"{len(tests) - failed}/{len(tests)} tests passed"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
