#!/usr/bin/env python3
import sqlite3
from pathlib import Path
p = Path(__file__).resolve().parents[1] / 'app_schema' / 'manufacturing.db'
print('PATH=' + str(p))
print('EXISTS', p.exists())
if p.exists():
    try:
        print('SIZE', p.stat().st_size)
        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = cur.fetchall()
        print('TABLE_COUNT', len(rows))
        for r in rows[:50]:
            print('TABLE', r[0])
        conn.close()
    except Exception as e:
        print('OPEN_ERROR', e)
