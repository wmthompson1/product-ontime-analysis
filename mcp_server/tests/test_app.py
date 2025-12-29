import json
from fastapi.testclient import TestClient
from mcp_server.app import app


client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "space" in data


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_handshake_echo():
    payload = {"client": "pytest"}
    r = client.post("/mcp/handshake", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("received") == payload
    assert data.get("status") == "accepted"


def test_resource_file():
    # Use an existing repository file
    payload = {"resource": {"type": "git:repo_path", "path": "mcp_server/app.py"}}
    r = client.post("/mcp/resource", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("type") == "file"
    assert data.get("path") == "mcp_server/app.py"
    assert isinstance(data.get("size"), int)
    assert isinstance(data.get("sample"), str)


def test_resource_directory():
    # Request the mcp_server directory and expect entries
    payload = {"resource": {"type": "git:repo_path", "path": "mcp_server"}}
    r = client.post("/mcp/resource", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("type") == "directory"
    assert data.get("path") == "mcp_server"
    assert isinstance(data.get("count"), int)
    assert isinstance(data.get("entries"), list)
    assert data.get("count") == len(data.get("entries"))
