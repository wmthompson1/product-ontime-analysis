"""Tests for the GET /mcp/config endpoint.

Task #59: Verifies that the /mcp/config endpoint returns the correct JSON
shape and correctly reflects ERP_INSTANCE_NAME and QUERY_API_KEY env vars.

Four cases:
1. ERP_INSTANCE_NAME unset  → erp_instance_name_source == "default"
2. ERP_INSTANCE_NAME set    → erp_instance_name_source == "env"
3. QUERY_API_KEY unset      → query_api_key_set == False
4. QUERY_API_KEY set        → query_api_key_set == True

Run: python hf-space-inventory-sqlgen/tests/test_mcp_config.py
"""

from __future__ import annotations

import os
import sys
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


def _make_client():
    """Return a FastAPI TestClient for the app, or None if unavailable."""
    try:
        from fastapi.testclient import TestClient
        import app as fastapi_app
        return TestClient(fastapi_app.app, raise_server_exceptions=True)
    except ImportError as exc:
        print(f"SKIP: could not import app or TestClient: {exc}")
        return None


def test_erp_name_default_when_env_unset():
    """When ERP_INSTANCE_NAME is not set, source must be 'default'."""
    client = _make_client()
    if client is None:
        return

    import app as fastapi_app

    env_patch = {"ERP_INSTANCE_NAME": None}
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ERP_INSTANCE_NAME", None)
        response = client.get("/mcp/config")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert body["erp_instance_name_source"] == "default", (
        f"Expected source='default' when ERP_INSTANCE_NAME unset, got: {body!r}"
    )
    assert body["erp_instance_name"] == "ERP_Instance_1", (
        f"Expected default name 'ERP_Instance_1', got: {body['erp_instance_name']!r}"
    )
    print(f"PASS: erp_instance_name_source='default' when ERP_INSTANCE_NAME unset")


def test_erp_name_env_when_env_set():
    """When ERP_INSTANCE_NAME is set, source must be 'env' and name must match."""
    client = _make_client()
    if client is None:
        return

    with unittest.mock.patch.dict(os.environ, {"ERP_INSTANCE_NAME": "SAP_Prod"}, clear=False):
        response = client.get("/mcp/config")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert body["erp_instance_name_source"] == "env", (
        f"Expected source='env' when ERP_INSTANCE_NAME is set, got: {body!r}"
    )
    assert body["erp_instance_name"] == "SAP_Prod", (
        f"Expected erp_instance_name='SAP_Prod', got: {body['erp_instance_name']!r}"
    )
    print(f"PASS: erp_instance_name_source='env' and name matches when ERP_INSTANCE_NAME set")


def test_query_api_key_set_false_when_unset():
    """When QUERY_API_KEY is not set, query_api_key_set must be False."""
    client = _make_client()
    if client is None:
        return

    import app as fastapi_app

    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("QUERY_API_KEY", None)
        original = fastapi_app.QUERY_API_KEY
        fastapi_app.QUERY_API_KEY = ""
        try:
            response = client.get("/mcp/config")
        finally:
            fastapi_app.QUERY_API_KEY = original

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert body["query_api_key_set"] is False, (
        f"Expected query_api_key_set=False when QUERY_API_KEY is empty, got: {body!r}"
    )
    print(f"PASS: query_api_key_set=False when QUERY_API_KEY is empty")


def test_query_api_key_set_true_when_set():
    """When QUERY_API_KEY is non-empty, query_api_key_set must be True."""
    client = _make_client()
    if client is None:
        return

    import app as fastapi_app

    original = fastapi_app.QUERY_API_KEY
    fastapi_app.QUERY_API_KEY = "secret-key-123"
    try:
        response = client.get("/mcp/config")
    finally:
        fastapi_app.QUERY_API_KEY = original

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    assert body["query_api_key_set"] is True, (
        f"Expected query_api_key_set=True when QUERY_API_KEY is set, got: {body!r}"
    )
    print(f"PASS: query_api_key_set=True when QUERY_API_KEY is non-empty")


def test_response_shape():
    """The /mcp/config endpoint must return 200 with the expected JSON keys."""
    client = _make_client()
    if client is None:
        return

    response = client.get("/mcp/config")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:200]}"
    )
    body = response.json()
    required_keys = {
        "erp_instance_name",
        "erp_instance_name_source",
        "sqlite_db_path",
        "query_api_key_set",
    }
    missing = required_keys - set(body.keys())
    assert not missing, (
        f"Response is missing required keys: {missing}. Present keys: {list(body.keys())}"
    )
    assert isinstance(body["erp_instance_name"], str), (
        f"erp_instance_name must be a string, got: {type(body['erp_instance_name'])}"
    )
    assert body["erp_instance_name_source"] in ("env", "default"), (
        f"erp_instance_name_source must be 'env' or 'default', got: {body['erp_instance_name_source']!r}"
    )
    assert isinstance(body["sqlite_db_path"], str), (
        f"sqlite_db_path must be a string, got: {type(body['sqlite_db_path'])}"
    )
    assert isinstance(body["query_api_key_set"], bool), (
        f"query_api_key_set must be a bool, got: {type(body['query_api_key_set'])}"
    )
    print(f"PASS: /mcp/config returns 200 with correct JSON shape: {list(body.keys())}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_erp_name_default_when_env_unset,
        test_erp_name_env_when_env_set,
        test_query_api_key_set_false_when_unset,
        test_query_api_key_set_true_when_set,
        test_response_shape,
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
