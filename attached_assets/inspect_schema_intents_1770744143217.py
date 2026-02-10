#!/usr/bin/env python3
"""Inspect key schema tables in manufacturing.db and print their columns and sample rows."""
import os
import sqlite3


def db_path():
    return os.path.abspath(os.path.join('hf-space-inventory-sqlgen', 'app_schema', 'manufacturing.db'))


def print_table_info(conn, table):
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    cols = cur.fetchall()
    if not cols:
        print(f"Table '{table}' does not exist or has no columns.")
        return
    print(f"\nColumns for {table}:")
    for c in cols:
        print('  ', c)
    # show a sample row
    try:
        r = conn.execute(f"SELECT * FROM {table} LIMIT 3").fetchall()
        print(f"Sample rows for {table} (up to 3): {r}")
    except Exception as e:
        print('  (failed to fetch sample rows)', e)


def main():
    p = db_path()
    if not os.path.exists(p):
        print('DB not found at', p)
        return 2
    conn = sqlite3.connect(p)
    try:
        tables = [
            'schema_concepts',
            'schema_intent_concepts',
            'schema_intent_perspectives',
            'schema_concept_fields',
            'schema_intents',
        ]
        for t in tables:
            print_table_info(conn, t)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
import sqlite3, os
db = os.path.join(os.path.dirname(__file__), '..', 'app_schema', 'manufacturing.db')
db = os.path.normpath(db)
print('DB path:', db)
print('Exists:', os.path.exists(db))
conn = sqlite3.connect(db)
cur = conn.cursor()
try:
    rows = cur.execute('PRAGMA table_info(schema_intents)').fetchall()
    print('schema_intents columns:')
    for r in rows:
        print(r)
except Exception as e:
    print('Error:', e)
finally:
    conn.close()
