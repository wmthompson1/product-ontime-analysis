import pandas as pd
import duckdb
from pathlib import Path

def discover_with_types(environment="dev"):
    script_dir = Path(__file__).parent
    db_path = script_dir / "db.db"

    print(f"DEBUG: Script dir: {script_dir}")
    print(f"DEBUG: DuckDB path: {db_path} (exists={db_path.exists()})")

    con = duckdb.connect(str(db_path), read_only=True)

    test_result = con.execute("SELECT schema_name FROM information_schema.schemata").fetchdf()
    print(f"DEBUG: All schemas: {test_result['schema_name'].tolist()}")
    
    # This query uses information_schema to discover tables and columns
    # It shows the 'Physical Reality' of your SQLMesh models
    discovery_query = """
    SELECT 
        t.table_schema AS schema_name,
        t.table_name,
        c.column_name,
        c.data_type
    FROM information_schema.tables t
    JOIN information_schema.columns c 
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE t.table_schema IN ('raw', 'staging')
    ORDER BY t.table_schema, t.table_name, c.ordinal_position
    """
    
    try:
        df = con.execute(discovery_query).fetchdf()

        print(f"DEBUG: Query returned {len(df)} rows")
        if len(df) > 0:
            print(f"DEBUG: Columns: {df.columns.tolist()}")
            print(f"DEBUG: First row: {df.iloc[0].to_dict()}")

        if df.empty:
            print("No populated tables found. Verify your seeds and 'sqlmesh plan'.")
            return

        for (schema, table), group in df.groupby(['schema_name', 'table_name']):
            print(f"\nTABLE: {schema}.{table}")
            print("--------------------------------------------------")

            for _, col in group.iterrows():
                print(f"  - {col['column_name']:<20} | {col['data_type']}")

            try:
                count_result = con.execute(f'SELECT COUNT(*) as cnt FROM "{schema}"."{table}"').fetchdf()
                row_count = count_result['cnt'].iloc[0]
                print(f"\n  Row count: {row_count}")
            except Exception as e:
                print(f"\n  Row count: Unable to query ({str(e)[:50]}...)")

            try:
                sample = con.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 2').fetchdf()
                print("\n  SAMPLE DATA:")
                print(sample.to_string(index=False))
            except Exception as e:
                print(f"\n  Sample data unavailable: {str(e)[:50]}...")
            print()

    except Exception as e:
        print(f"Audit failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    discover_with_types()