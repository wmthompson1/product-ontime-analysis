# Database Setup & Loading Guide

This guide documents how to set up, load, and update the SQLite database for the Manufacturing Inventory SQL Generator.

## File Locations

```
schema/
├── manufacturing.db          # SQLite database (auto-created)
├── schema_sqlite.sql         # DDL - CREATE TABLE statements
└── queries/
    ├── index.json            # Category definitions
    ├── quality_control.sql   # Ground truth SQL by category
    ├── supplier_performance.sql
    ├── equipment_reliability.sql
    └── production_analytics.sql
```

## Loading the Database

### Option 1: Automatic Initialization (Default)

The app automatically initializes the database on startup:

```python
# In app.py - init_sqlite_db()
# Reads schema/schema_sqlite.sql and creates tables in schema/manufacturing.db
```

Just run the app:
```bash
cd hf-space-inventory-sqlgen
python app.py
```

### Option 2: Manual Schema Load

To manually recreate the database from schema:

```bash
# Delete existing database (if any)
rm -f schema/manufacturing.db

# Load schema using sqlite3
sqlite3 schema/manufacturing.db < schema/schema_sqlite.sql
```

### Option 3: Load Sample Data

If you have sample data CSV files:

```bash
sqlite3 schema/manufacturing.db
.mode csv
.import suppliers.csv suppliers
.import product_defects.csv product_defects
.quit
```

## Updating the Schema

### Step 1: Edit the DDL File

Modify `schema/schema_sqlite.sql` with your new table definitions:

```sql
-- Example: Add a new table
CREATE TABLE IF NOT EXISTS new_table (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Step 2: Regenerate Database

```bash
rm -f schema/manufacturing.db
sqlite3 schema/manufacturing.db < schema/schema_sqlite.sql
```

### Step 3: Restart the App

```bash
# If running locally
python app.py

# If on Replit, restart the HF Space Inventory SQL workflow
```

## Managing Table Relationships (schema_edges)

The `schema_edges` table defines foreign key relationships for the schema graph:

### View Current Edges

```bash
sqlite3 schema/manufacturing.db "SELECT * FROM schema_edges"
```

### Add New Relationship

```sql
INSERT INTO schema_edges 
(from_table, to_table, relationship_type, join_column, weight, 
 join_column_description, natural_language_alias, context)
VALUES 
('order_items', 'products', 'REFERENCES', 'product_id', 1,
 'Links order items to products', 'ordered product', 
 'Use for order fulfillment queries');
```

### Using schema_graph.py

Build a NetworkX graph from schema_edges:

```bash
cd hf-space-inventory-sqlgen
python schema_graph.py
```

Import from GraphML file:

```bash
python schema_graph.py --import data/schema.graphml
```

## Ground Truth SQL Queries

### File Format

Each category SQL file contains queries in this format:

```sql
-- Name: Query Title Here
-- Description: What this query does
SELECT 
    column1,
    column2
FROM table_name
WHERE condition;

-- Name: Another Query
-- Description: Another description
SELECT * FROM another_table;
```

### Adding a New Category

1. Create new SQL file: `schema/queries/new_category.sql`

2. Update `schema/queries/index.json`:

```json
{
  "version": "1.0.0",
  "categories": [
    {
      "id": "new_category",
      "name": "New Category",
      "file": "new_category.sql",
      "description": "Description of new category"
    }
  ]
}
```

3. Restart the app to load new queries.

### Verify Queries Loaded

```bash
curl http://localhost:5000/mcp/tools/get_saved_categories
curl "http://localhost:5000/mcp/tools/get_saved_queries?category_id=new_category"
```

## Quick Reference Commands

| Task | Command |
|------|---------|
| View all tables | `sqlite3 schema/manufacturing.db ".tables"` |
| View table schema | `sqlite3 schema/manufacturing.db ".schema table_name"` |
| Count rows | `sqlite3 schema/manufacturing.db "SELECT COUNT(*) FROM table_name"` |
| Export to CSV | `sqlite3 -csv schema/manufacturing.db "SELECT * FROM table_name" > out.csv` |
| Rebuild database | `rm -f schema/manufacturing.db && sqlite3 schema/manufacturing.db < schema/schema_sqlite.sql` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///schema/manufacturing.db` | Database connection string |
| `QUERY_API_KEY` | (none) | API key for `/mcp/tools/save_query` endpoint |

## Troubleshooting

### Database Locked Error

```bash
# Find and kill any processes using the database
fuser -k schema/manufacturing.db
```

### Schema Changes Not Reflected

1. Delete the database file
2. Restart the app (it will recreate from schema_sqlite.sql)

### Missing Tables

Check that `schema/schema_sqlite.sql` contains all required CREATE TABLE statements.

```bash
sqlite3 schema/manufacturing.db ".tables"
```

Compare with expected tables in `schema_sqlite.sql`.
