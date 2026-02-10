#!/usr/bin/env python3
import sqlite3
from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'app_schema' / 'manufacturing.db'
p.parent.mkdir(parents=True, exist_ok=True)
sql_path = Path(__file__).resolve().parents[1] / 'app_schema' / 'schema_sqlite.sql'
print('Database path:', p)
if not sql_path.exists():
    raise FileNotFoundError(f"Schema SQL not found: {sql_path}")
with open(sql_path, 'r', encoding='utf-8') as fh:
    sql = fh.read()
conn = sqlite3.connect(str(p))
conn.executescript(sql)
conn.commit()
conn.close()
print('Created sqlite DB at', p)
