#!/usr/bin/env python3
"""Create and seed Utilities/SQLMesh/dev.duckdb for local development/tests."""
from pathlib import Path
import duckdb


def main():
    repo_root = Path(__file__).resolve().parents[1]
    db_path = repo_root / "Utilities" / "SQLMesh" / "dev.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, name TEXT, qty INTEGER)")
    # insert sample rows if they don't exist
    con.execute("INSERT INTO items SELECT 1,'widget',10 WHERE NOT EXISTS (SELECT 1 FROM items WHERE id=1)")
    con.execute("INSERT INTO items SELECT 2,'gadget',5 WHERE NOT EXISTS (SELECT 1 FROM items WHERE id=2)")
    con.commit()
    con.close()
    print(f"Created/seeded {db_path}")


if __name__ == '__main__':
    main()
