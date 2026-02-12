**SQLGlot will be a subfolder of the SQLMesh folder called 'analysis'
└───SQLMesh
    ├───.cache
    │   ├───model_definition
    │   ├───optimized_query
    │   └───snapshot

    └───analysis          # NEW: SQLGlot and lineage & analysis scripts
        ├───lineage       # Table lineage and dependency tracking
        ├───impact        # Impact analysis tools
        ├───reports       # Generated reports and outputs
        └───utils         # Shared utilities

    ├───audits
    ├───logs
    ├───macros
    │   └───__pycache__
    ├───models
    │   ├───intermediate
    │   ├───marts
    │   └───staging
    ├───seeds
    │   └───src
    └───tests


**sqlglot** (which is a core component of SQLMesh) is a powerful SQL parser that can extract structural information from SQL queries, including tables in FROM and JOIN clauses. 

Let me search your repository to see what SQL files you're working with: Yes!  Since you already have SQLMesh set up in your repo, you can absolutely use **sqlglot** (which SQLMesh is built on top of) to parse SQL queries and extract table information from `FROM` and `JOIN` clauses.

## Using sqlglot to Extract Tables

Sqlglot is a powerful SQL parser that can analyze your queries and extract various elements.  Here's how you can use it to get tables from FROM/JOIN clauses:

### Basic Example

```python name=extract_tables. py
import sqlglot

# Example SQL query from your repo
sql = """
SELECT a.[FILE NUMBER], e.[First Name], ADP_HOURS_WORKED as 'ADP Hours'
FROM LIVESupplemental. dbo. ADP_DAILY_HOURS a with (nolock) 
INNER JOIN LIVESupplemental.dbo.ADP_EMP e on a.[FILE NUMBER] = e.[File Number]
LEFT JOIN LIVE.dbo.LABOR_TICKET b on a.[FILE NUMBER] = b. EMPLOYEE
WHERE a.PAYDATE between @date1 and @date2
"""

# Parse the SQL
parsed = sqlglot.parse_one(sql, read='tsql')  # Use 'tsql' for SQL Server

# Extract all table references
tables = [
    table.sql() for table in parsed.find_all(sqlglot.exp.Table)
]

print("Tables found:")
for table in tables:
    print(f"  - {table}")

# Output:
#   - LIVESupplemental. dbo.ADP_DAILY_HOURS
#   - LIVESupplemental.dbo.ADP_EMP
#   - LIVE.dbo.LABOR_TICKET
```

### More Advanced:  Get Table Names with Aliases

```python name=extract_tables_advanced.py
import sqlglot
from sqlglot import exp

def extract_table_info(sql_query, dialect='tsql'):
    """Extract table names, schemas, and aliases from SQL query"""
    parsed = sqlglot.parse_one(sql_query, read=dialect)
    
    table_info = []
    for table in parsed.find_all(exp.Table):
        info = {
            'database': table.catalog or None,
            'schema': table. db or None,
            'table':  table.name,
            'alias': table.alias or None,
            'full_name': table.sql()
        }
        table_info.append(info)
    
    return table_info

# Using one of your SQL files
sql = """
SELECT A. Customer_Order, A.BASE_ID
FROM CTE_CO_WO A
LEFT JOIN (SELECT COUNT(PRIMARY_KEY) AS 'NUM_CHANG', PRIMARY_KEY 
           FROM HISTORY_DATA WITH (NOLOCK)
           WHERE ACTION = 'UPDATE') HC ON A.WO_PK = HC.PRIMARY_KEY
INNER JOIN (SELECT MAX(SHIPPED_DATE) AS 'SHIPPED_DATE', CUST_ORDER_ID 
            FROM SHIPPER WITH (NOLOCK) 
            GROUP BY CUST_ORDER_ID) S ON A.Customer_Order = S.CUST_ORDER_ID
"""

tables = extract_table_info(sql)
for t in tables:
    print(f"Table: {t['table']}, Schema: {t['schema']}, Alias: {t['alias']}")

# Output:
#   Table: CTE_CO_WO, Schema: None, Alias: A
#   Table: HISTORY_DATA, Schema: None, Alias:  None
#   Table: SHIPPER, Schema: None, Alias:  None
```

### Script to Process Your SQL Files

```python name=process_repo_sql.py
import sqlglot
from sqlglot import exp
import os
from pathlib import Path

def extract_tables_from_file(file_path):
    """Extract all tables from a SQL file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        # Parse all statements in the file
        statements = sqlglot.parse(sql_content, read='tsql')
        
        all_tables = set()
        for stmt in statements:
            if stmt:   # Check if statement parsed successfully
                for table in stmt.find_all(exp.Table):
                    # Build full table name with schema/database
                    parts = []
                    if table.catalog:
                        parts.append(table.catalog)
                    if table.db:
                        parts. append(table.db)
                    parts.append(table.name)
                    full_name = '.'.join(parts)
                    all_tables. add(full_name)
        
        return list(all_tables)
    except Exception as e: 
        print(f"Error parsing {file_path}: {e}")
        return []

def scan_repo_for_sql_tables(repo_path):
    """Scan all SQL files in the repo and extract tables"""
    sql_files = Path(repo_path).rglob('*.sql')
    
    results = {}
    for sql_file in sql_files:
        tables = extract_tables_from_file(sql_file)
        if tables:
            results[str(sql_file)] = tables
    
    return results

# Usage
if __name__ == "__main__": 
    # Adjust this path to your repo location
    repo_path = "./SQL_Reports"
    
    table_usage = scan_repo_for_sql_tables(repo_path)
    
    # Print results
    for file, tables in table_usage.items():
        print(f"\n{file}:")
        for table in sorted(tables):
            print(f"  - {table}")
    
    # Create a report of all unique tables
    all_tables = set()
    for tables in table_usage.values():
        all_tables.update(tables)
    
    print(f"\n\n=== Summary ===")
    print(f"Total SQL files: {len(table_usage)}")
    print(f"Unique tables referenced: {len(all_tables)}")
    print(f"\nAll tables:")
    for table in sorted(all_tables):
        print(f"  - {table}")
```

## Integration with SQLMesh

Since you have SQLMesh set up, you can also leverage it directly for lineage and dependency tracking:

```python name=sqlmesh_lineage.py
from sqlmesh import Context

# Load your SQLMesh context
context = Context(paths=["path/to/your/sqlmesh/project"])

# Get lineage for a specific model
model_name = "your_model_name"
model = context.get_model(model_name)

# Get upstream dependencies (tables this model reads from)
upstream = model.depends_on
print(f"Tables used by {model_name}:")
for dep in upstream:
    print(f"  - {dep}")

# You can also get the full lineage graph
lineage = context.get_dag()
```

## Practical Use Cases

1. **Data Lineage Documentation**: Generate a map of which tables are used where
2. **Impact Analysis**: Find all queries that use a specific table
3. **Migration Planning**: Identify dependencies before schema changes
4. **Query Optimization**: Find which queries join to the most tables

Would you like help setting up any of these specific use cases for your repo, or would you like to integrate this into a GitHub Action to automatically document table dependencies? 