``` import sqlite3
conn = sqlite3.connect('data/manufacturing_analytics.sqlite3')
cursor = conn.cursor()
edges = [
    (1, 'equipment', 'product', 'PRODUCES', 'part_id', 1, 'part ID', 'equipment to product via part ID', 'e.equipment_id = p.part_id', 'Join equipment and product on part ID'),
    (2, 'product', 'supplier', 'SUPPLIED_BY', 'supplier_id', 1, 'supplier ID', 'product to supplier via supplier ID', 'p.supplier_id = s.supplier_id', 'Join product and supplier on supplier ID'),
    (3, 'equipment', 'production_line', 'OPERATES_ON', 'line_id', 1, 'line ID', 'equipment to production_line via line ID', 'e.line_id = pl.line_id', 'Join equipment and production_line on line ID'),
    (4, 'equipment', 'maintenance_log', 'MAINTAINED_BY', 'equipment_id', 1, 'equipment ID', 'equipment to maintenance_log via equipment ID', 'e.equipment_id = ml.equipment_id', 'Join equipment and maintenance_log on equipment ID'),
    (5, 'production_line', 'quality_control', 'MONITORED_BY', 'line_id', 1, 'line ID', 'production_line to quality_control via line ID', 'pl.line_id = qc.line_id', 'Join production_line and quality_control on line ID'),
    (6, 'product', 'quality_control', 'TESTED_IN', 'product_id', 1, 'product ID', 'product to quality_control via product ID', 'p.product_id = qc.product_id', 'Join product and quality_control on product ID'),
    (7, 'equipment', 'quality_control', 'DEPENDS_ON', 'equipment_id', 2, 'Equipment quality dependency', 'equipment ID', 'e.equipment_id = qc.equipment_id', 'Quality control depends on equipment calibration'),
]
cursor.executemany('''
    INSERT OR REPLACE INTO schema_edges (edge_id, from_table, to_table, relationship_type, join_column, weight, join_column_description, natural_language_alias, few_shot_example, context) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', edges)
conn.commit()
print(f'Inserted {len(edges)} edges')
conn.close()
```

