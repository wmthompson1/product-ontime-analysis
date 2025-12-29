#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import importlib.util

os.environ.setdefault("DATABASE_URL", "sqlite:///data/manufacturing_analytics.sqlite3")

app_path = Path.cwd() / "hf-space-inventory-sqlgen" / "app.py"
spec = importlib.util.spec_from_file_location("hf_space_inventory_app", str(app_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = getattr(mod, "app")

from fastapi.testclient import TestClient

def call(path):
    client = TestClient(app)
    r = client.get(path)
    return r.status_code, r.text[:10000]

def main():
    for path in ["/mcp/discover", "/mcp/tools/get_db_tables", "/mcp/tools/get_all_ddl"]:
        try:
            status, text = call(path)
            print(f"{path} -> {status}\n{text}\n---\n")
        except Exception as e:
            print(f"{path} -> ERROR: {e}")

if __name__ == '__main__':
    main()
