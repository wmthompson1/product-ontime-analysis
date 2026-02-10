#!/usr/bin/env python3
"""List tables and inspect perspective-related tables in manufacturing.db"""
import os
import sqlite3


def main():
    p = os.path.abspath(os.path.join('hf-space-inventory-sqlgen', 'app_schema', 'manufacturing.db'))
    if not os.path.exists(p):
        print('DB not found:', p)
        return 2
    conn = sqlite3.connect(p)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print('Tables:', tables)
        for t in tables:
            if 'perspect' in t or 'perspective' in t or t.lower().startswith('schema_p'):
                print('\n--', t)
                try:
                    rows = conn.execute(f"SELECT * FROM {t} LIMIT 10").fetchall()
                    print('Rows:', rows)
                except Exception as e:
                    print('  (error reading rows)', e)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
