"""Tests for the GET /mcp/tools/get_resolves_to endpoint.

Verifies the M4 read adapter that exposes metric/template variable bindings
(resolves_to) for interface parity with the public fleet, WITHOUT introducing a
new schema_resolves_to table. The endpoint reads the binding rows from the
existing SQLite source of truth (schema_concept_fields where variable_name IS
NOT NULL, joined to schema_concepts) and enriches each with field_key.

Each returned item must carry exactly the cross-repo payload structure:
    concept, variable_name, table_name, field_name, field_key, context_hint

The field_key is the canonical column-node key (table:column:structural:system:
none:none), which is identical whether sourced from the live ArangoDB resolves_to
edge's _from or from the deterministic fallback, so assertions are deterministic
regardless of whether ArangoDB is reachable.

Run: python hf-space-inventory-sqlgen/tests/test_get_resolves_to.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)

ITEM_KEYS = {"concept", "variable_name", "table_name", "field_name", "field_key", "context_hint"}


def _make_client():
    """Return a FastAPI TestClient for the app, or None if unavailable."""
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
        return TestClient(fastapi_app.app, raise_server_exceptions=True)
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return None


def _canonical_field_key(table_name: str, field_name: str) -> str:
    return f"{table_name}:{field_name}:structural:system:none:none"


def test_response_shape():
    """Unfiltered call returns 200 with a resolves_to list and count, and every
    item carries exactly the six cross-repo payload keys."""
    client = _make_client()
    if client is None:
        return

    response = client.get("/mcp/tools/get_resolves_to")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert "resolves_to" in body and isinstance(body["resolves_to"], list), (
        f"Expected 'resolves_to' list, got keys: {list(body.keys())}"
    )
    assert body["count"] == len(body["resolves_to"]), (
        f"count {body['count']} != len(resolves_to) {len(body['resolves_to'])}"
    )
    for item in body["resolves_to"]:
        assert set(item.keys()) == ITEM_KEYS, (
            f"Item keys {set(item.keys())} != expected {ITEM_KEYS}"
        )
    print(f"PASS: shape correct, {body['count']} bindings, item keys exact")


def test_all_m4_bindings_present():
    """All 11 M4 bindings (across the 5 showcase metric concepts) are returned."""
    client = _make_client()
    if client is None:
        return

    body = client.get("/mcp/tools/get_resolves_to").json()
    concepts = {item["concept"] for item in body["resolves_to"]}
    expected = {
        "OEEOperational", "OEEStrategic",
        "DeliveryPerformanceOps", "DeliveryPerformanceSupplier", "DeliveryPerformanceFinance",
    }
    missing = expected - concepts
    assert not missing, f"Missing showcase metric concepts: {missing}"
    assert body["count"] >= 11, f"Expected >= 11 M4 bindings, got {body['count']}"
    print(f"PASS: all 5 showcase metrics present, {body['count']} total bindings")


def test_oee_operational_bindings():
    """OEEOperational returns its two numerator/denominator bindings with the
    correct table/field/field_key."""
    client = _make_client()
    if client is None:
        return

    body = client.get("/mcp/tools/get_resolves_to", params={"concept_name": "OEEOperational"}).json()
    items = body["resolves_to"]
    assert body["count"] == 2, f"Expected 2 OEEOperational bindings, got {body['count']}: {items}"

    by_var = {it["variable_name"]: it for it in items}
    assert set(by_var) == {"act_run_hrs", "run_hrs"}, f"Unexpected variables: {set(by_var)}"
    for var in ("act_run_hrs", "run_hrs"):
        it = by_var[var]
        assert it["concept"] == "OEEOperational"
        assert it["table_name"] == "operation", f"{var}: table {it['table_name']}"
        assert it["field_name"] == var, f"{var}: field {it['field_name']}"
        assert it["field_key"] == _canonical_field_key("operation", var), (
            f"{var}: field_key {it['field_key']}"
        )
        assert it["context_hint"], f"{var}: context_hint should be non-empty"
    print("PASS: OEEOperational -> act_run_hrs + run_hrs, field_keys canonical")


def test_delivery_performance_ops_bindings():
    """DeliveryPerformanceOps returns the shared on-time pair (receipt_date from
    receiving, required_date from purchase_order)."""
    client = _make_client()
    if client is None:
        return

    body = client.get("/mcp/tools/get_resolves_to", params={"concept_name": "DeliveryPerformanceOps"}).json()
    items = body["resolves_to"]
    assert body["count"] == 2, f"Expected 2 DeliveryPerformanceOps bindings, got {body['count']}: {items}"

    by_var = {it["variable_name"]: it for it in items}
    assert set(by_var) == {"receipt_date", "required_date"}, f"Unexpected variables: {set(by_var)}"

    assert by_var["receipt_date"]["table_name"] == "receiving"
    assert by_var["receipt_date"]["field_key"] == _canonical_field_key("receiving", "receipt_date")
    assert by_var["required_date"]["table_name"] == "purchase_order"
    assert by_var["required_date"]["field_key"] == _canonical_field_key("purchase_order", "required_date")
    print("PASS: DeliveryPerformanceOps -> receiving.receipt_date + purchase_order.required_date")


def test_unknown_concept_returns_empty():
    """An unknown concept name returns an empty list and count 0, not an error."""
    client = _make_client()
    if client is None:
        return

    body = client.get("/mcp/tools/get_resolves_to", params={"concept_name": "NoSuchMetric_xyz"}).json()
    assert body.get("count") == 0, f"Expected count 0 for unknown concept, got: {body}"
    assert body.get("resolves_to") == [], f"Expected empty list, got: {body.get('resolves_to')}"
    print("PASS: unknown concept -> empty list, count 0 (no error)")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_response_shape,
        test_all_m4_bindings_present,
        test_oee_operational_bindings,
        test_delivery_performance_ops_bindings,
        test_unknown_concept_returns_empty,
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
