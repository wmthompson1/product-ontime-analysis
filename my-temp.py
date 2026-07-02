import sqlite3

db = "hf-space-inventory-sqlgen/app_schema/manufacturing.db"
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)   # mode=ro = read-only, safe

row = con.execute("""
    SELECT SUM(op.run_hrs) AS total_run_hours,
           COUNT(*)        AS operations
    FROM work_order wo
    JOIN operation op ON op.wo_id = wo.wo_id
""").fetchone()

print(row)   # -> (669.55, 502)
con.close()