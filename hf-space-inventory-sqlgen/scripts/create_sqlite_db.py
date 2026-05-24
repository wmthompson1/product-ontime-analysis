#!/usr/bin/env python3
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

p = ROOT_DIR / 'app_schema' / 'manufacturing.db'
p.parent.mkdir(parents=True, exist_ok=True)
sql_path = ROOT_DIR / 'app_schema' / 'schema_sqlite.sql'

print('Database path:', p)
if not sql_path.exists():
    raise FileNotFoundError(f"Schema SQL not found: {sql_path}")

with open(sql_path, 'r', encoding='utf-8') as fh:
    sql = fh.read()

conn = sqlite3.connect(str(p))
conn.executescript(sql)
conn.commit()
print('Created sqlite DB at', p)

sys.path.insert(0, str(SCRIPT_DIR))
import install_sync_triggers as ist

print('Installing sync triggers ...')
ist.install(conn)
print('Sync triggers installed.')

conn.close()
