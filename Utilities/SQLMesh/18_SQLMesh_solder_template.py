import os
from pathlib import Path
import duckdb
import pandas as pd

class SemanticSolder:
    def __init__(self, db_path=None):
        """Initialize the Solder with direct DuckDB connection."""
        # Default to db.db in the script's directory if no path provided
        if db_path is None:
            db_path = Path(__file__).parent / "db.db"
        else:
            db_path = Path(db_path)
        
        if not db_path.exists():
            raise FileNotFoundError(f"DuckDB database not found at {db_path}")
        
        self.conn = duckdb.connect(str(db_path), read_only=True)
        print(f"✅ Solder initialized with database: {db_path}")

    def execute_semantic_query(self, sql, perspective="Shop_Floor"):
        """
        Executes a query and handles common legacy data hurdles.
        In a full RAG implementation, this is where the ArangoDB 
        'Can Mean' aliases would be injected.
        """
        print(f"--- Executing Query (Perspective: {perspective}) ---")
        try:
            # Execute directly on DuckDB connection
            df = self.conn.execute(sql).fetchdf()
            return df
        except Exception as e:
            if "Binder Error" in str(e):
                print("💡 Solder Tip: Detected a Type Mismatch. Ensure VARCHAR IDs are quoted or CAST.")
            print(f"❌ Query Failed: {e}")
            return None

# --- TEMPLATE USAGE ---
if __name__ == "__main__":
    # 1. Initialize Solder (automatically finds config.yaml in script directory)
    solder = SemanticSolder()

    # 2. Example: Query using physical table name (with version hash)
    # Note: line_id is VARCHAR, so we quote it
    # Physical table: sqlmesh__staging.staging__stg_production_schedule__1966595228
    east_wall_query = """
    SELECT 
        schedule_id,
        line_id,
        scheduled_date,
        status,
        completion_rate
    FROM "sqlmesh__staging"."staging__stg_production_schedule__1966595228"
    WHERE line_id = '6'
    ORDER BY scheduled_date
    LIMIT 5
    """

    results = solder.execute_semantic_query(east_wall_query)
    
    if results is not None:
        print("\n📊 Results (Hydrated):")
        print(results.to_string(index=False))