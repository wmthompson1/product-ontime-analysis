import pandas as pd
from pathlib import Path
from sqlmesh import Context

def discover_with_types(environment="dev"):
    # Use script's directory to find config.yaml
    script_dir = Path(__file__).parent
    ctx = Context(paths=str(script_dir))
    
    # Use the engine adapter to query DuckDB directly, bypassing SQLMesh's logical layer
    engine = ctx.engine_adapter
    
    # Debug: check what we're connected to
    print(f"DEBUG: Default gateway: {ctx.config.default_gateway if ctx.config else 'None'}")
    print(f"DEBUG: Engine adapter type: {type(engine).__name__}")
    print(f"DEBUG: Script dir: {script_dir}")
    
    # Test with a simpler query first - show all schemas
    test_result =engine.fetchdf("SELECT schema_name FROM information_schema.schemata")
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
    WHERE t.table_schema LIKE 'sqlmesh__%'
    ORDER BY t.table_schema, t.table_name, c.ordinal_position
    """
    
    try:
        df = engine.fetchdf(discovery_query)
        
        print(f"DEBUG: Query returned {len(df)} rows")
        if len(df) > 0:
            print(f"DEBUG: Columns: {df.columns.tolist()}")
            print(f"DEBUG: First row: {df.iloc[0].to_dict()}")
        
        if df.empty:
            print("No populated tables found. Verify your seeds and 'sqlmesh plan'.")
            return

        # Group by table for a clean readout
        for (schema, table), group in df.groupby(['schema_name', 'table_name']):
            print(f"\n📂 TABLE: {schema}.{table}")
            print("--------------------------------------------------")
            
            # Print column types - looking for those VARCHAR vs INTEGER traps
            for _, col in group.iterrows():
                print(f"  - {col['column_name']:<20} | {col['data_type']}")
            
            # Get actual row count with error handling
            try:
                count_result = engine.fetchdf(f'SELECT COUNT(*) as cnt FROM "{schema}"."{table}"')
                row_count = count_result['cnt'].iloc[0]
                print(f"\n  Row count: {row_count}")
            except Exception as e:
                print(f"\n  Row count: Unable to query ({str(e)[:50]}...)")
            
            # Render a sample to verify the data
            try:
                sample = engine.fetchdf(f'SELECT * FROM "{schema}"."{table}" LIMIT 2')
                print("\n  SAMPLE DATA:")
                print(sample.to_string(index=False))
            except Exception as e:
                print(f"\n  Sample data unavailable: {str(e)[:50]}...")
            print("\n")

    except Exception as e:
        print(f"Audit failed: {e}")

if __name__ == "__main__":
    discover_with_types()