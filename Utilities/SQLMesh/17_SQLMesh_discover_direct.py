"""
Direct Duck DB connection to discover table schemas and types
Bypasses SQLMesh Context to connect directly to db.db
"""
import pandas as pd
import duckdb
from pathlib import Path

def discover_tables():
    # Find db.db in same directory as this script
    script_dir = Path(__file__).parent
    db_path = script_dir / "db.db"
    
    if not db_path.exists():
        print(f"❌ ERROR: Database not found at {db_path}")
        return
    
    print(f"✅ Connecting to {db_path}\n")
    
    # Connect directly to DuckDB (read-only to be safe)
    conn = duckdb.connect(str(db_path), read_only=True)
    
    # Show all schemas
    schemas_df = conn.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name").fetchdf()
    print(f"📋 All schemas in database: {schemas_df['schema_name'].tolist()}\n")
    
    # Discovery query: get all tables in sqlmesh schemas with their columns
    discovery_query = """
    SELECT 
        t.table_schema AS schema_name,
        t.table_name,
        c.column_name,
        c.data_type,
        c.ordinal_position
    FROM information_schema.tables t
    JOIN information_schema.columns c 
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE t.table_schema LIKE 'sqlmesh__%'
    ORDER BY t.table_schema, t.table_name, c.ordinal_position
    """
    
    df = conn.execute(discovery_query).fetchdf()
    
    if df.empty:
        print("⚠️  No tables found in sqlmesh schemas.")
        print("Run 'sqlmesh plan' and apply backfill to populate tables.\n")
        conn.close()
        return
    
    print(f"📊 Found {len(df)} columns across {df.groupby(['schema_name', 'table_name']).ngroups} tables\n")
    print("="*80)
    
    # Group by table and display
    for (schema, table), group in df.groupby(['schema_name', 'table_name']):
        # Clean up the table name for display (remove version hash if present)
        display_name = table.split('__')[1] if '__' in table else table
        
        print(f"\n📂 TABLE: {schema}.{display_name}")
        print(f"   Physical name: {table}")
        print("-" * 80)
        
        # Print columns with types
        for _, col in group.iterrows():
            print(f"  {col['ordinal_position']:>2}. {col['column_name']:<25} | {col['data_type']}")
        
        # Get row count
        try:
            count_result = conn.execute(f'SELECT COUNT(*) as cnt FROM "{schema}"."{table}"').fetchdf()
            row_count = count_result['cnt'].iloc[0]
            print(f"\n   ✓ Row count: {row_count:,}")
        except Exception as e:
            print(f"\n   ✗ Row count unavailable: {str(e)[:60]}")
        
        # Show sample data (first 2 rows)
        try:
            sample = conn.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 2').fetchdf()
            if not sample.empty:
                print(f"\n   Sample data (first 2 rows):")
                print("   " + sample.to_string(index=False).replace('\n', '\n   '))
        except Exception as e:
            print(f"\n   ✗ Sample data unavailable: {str(e)[:60]}")
        
        print()
    
    conn.close()
    print("="*80)
    print("✅ Discovery complete\n")

if __name__ == "__main__":
    discover_tables()
