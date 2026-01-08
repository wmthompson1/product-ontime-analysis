import os

# Ensure the app uses the local SQLite DB
os.environ.setdefault("DATABASE_URL", "sqlite:///data/manufacturing_analytics.sqlite3")

from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path

# Import the FastAPI app object by file path (module name contains hyphens)
app_path = Path.cwd() / "hf-space-inventory-sqlgen" / "app.py"
spec = importlib.util.spec_from_file_location("hf_space_inventory_app", str(app_path))
hf_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hf_mod
spec.loader.exec_module(hf_mod)
fastapi_app = getattr(hf_mod, "app")


def test_mcp_discover():
    client = TestClient(fastapi_app)
    r = client.get("/mcp/discover")
    assert r.status_code == 200
    j = r.json()
    assert "tools" in j and isinstance(j["tools"], list)


def test_get_db_tables():
    client = TestClient(fastapi_app)
    r = client.get("/mcp/tools/get_db_tables")
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j.get("tables"), list)
    assert isinstance(j.get("count"), int)
    assert j.get("count") == len(j.get("tables"))
    # Expect at least one table in the test DB
    assert len(j.get("tables")) >= 1


def test_get_all_ddl():
    client = TestClient(fastapi_app)
    r = client.get("/mcp/tools/get_all_ddl")
    assert r.status_code == 200
    j = r.json()
    # Either we have ddl dict or an error message
    assert ("ddl" in j and isinstance(j["ddl"], dict)) or ("error" in j)
