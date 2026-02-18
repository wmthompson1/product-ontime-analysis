#!/usr/bin/env python3
"""
Schema Catalog Builder for SQLMesh

Extracts column-level metadata from DuckDB information_schema
and builds a schema_catalog seed/table for SQLMesh.

Columns:
  table_name       - Logical table name (staging.stg_*)
  column_name      - Physical field name
  data_type        - DDL type (e.g., VARCHAR, BIGINT, DOUBLE)
  is_nullable      - Whether the column allows NULL
  is_primary_key   - Whether the column appears to be a primary key (NULL for now)
  is_shadow_key    - Flag for Part/Vendor hash problem (NULL for now)
  semantic_concept - Link to the Concept node (NULL for now)

Usage:
    python 19_build_schema_catalog.py
    python 19_build_schema_catalog.py --output seeds/schema_catalog.csv
    python 19_build_schema_catalog.py --schema staging --summary
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Dict
import duckdb


def extract_logical_table_name(physical_name: str) -> str:
    """
    Convert physical table name to logical name.
    staging__stg_daily_deliveries__1269145007 -> stg_daily_deliveries
    """
    if '__' in physical_name:
        parts = physical_name.split('__')
        if len(parts) >= 2:
            # Return the middle part (e.g., stg_daily_deliveries)
            return parts[1]
    return physical_name


def build_catalog_from_duckdb(db_path: Path, target_schemas: List[str]) -> List[Dict]:
    """
    Query information_schema.columns from DuckDB and build catalog.
    """
    conn = duckdb.connect(str(db_path), read_only=True)
    
    # Build WHERE clause for schema filtering
    schema_filter = " OR ".join([f"table_schema = '{s}'" for s in target_schemas])
    
    query = f"""
    SELECT 
        table_schema,
        table_name,
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    FROM information_schema.columns
    WHERE ({schema_filter})
    ORDER BY table_schema, table_name, ordinal_position
    """
    
    df = conn.execute(query).fetchdf()
    conn.close()
    
    if df.empty:
        print(f"No columns found in schemas: {target_schemas}", file=sys.stderr)
        return []
    
    catalog = []
    for _, row in df.iterrows():
        # Extract logical table name
        logical_name = extract_logical_table_name(row['table_name'])
        
        # Convert is_nullable from YES/NO to boolean
        is_nullable = row['is_nullable'] == 'YES'
        
        catalog.append({
            "table_name": logical_name,
            "column_name": row['column_name'],
            "data_type": row['data_type'],
            "is_nullable": is_nullable,
            "is_primary_key": None,  # Could infer from _id columns
            "is_shadow_key": None,
            "semantic_concept": None,
        })
    
    return catalog


def infer_primary_keys(catalog: List[Dict]) -> List[Dict]:
    """
    Simple heuristic: if column_name ends with '_id' and is first column,
    mark as potential primary key.
    """
    # Group by table
    tables = {}
    for row in catalog:
        table = row['table_name']
        if table not in tables:
            tables[table] = []
        tables[table].append(row)
    
    # Check first column of each table
    for table, cols in tables.items():
        if cols:
            first_col = cols[0]
            # If first column ends with _id, likely a PK
            if first_col['column_name'].endswith('_id'):
                first_col['is_primary_key'] = True
            else:
                first_col['is_primary_key'] = False
            
            # Mark rest as False
            for col in cols[1:]:
                col['is_primary_key'] = False
    
    return catalog


def write_csv_seed(catalog: List[Dict], output_path: Path):
    """
    Write catalog as CSV seed file for SQLMesh.
    """
    fieldnames = ["table_name", "column_name", "data_type", "is_nullable",
                  "is_primary_key", "is_shadow_key", "semantic_concept"]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in catalog:
            # Convert None to empty string for CSV
            csv_row = {k: (v if v is not None else '') for k, v in row.items()}
            writer.writerow(csv_row)


def write_json_file(catalog: List[Dict], output_path: Path):
    """
    Write catalog as JSON for inspection.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)


def print_summary(catalog: List[Dict]):
    """
    Print summary statistics.
    """
    tables = {}
    for row in catalog:
        table = row['table_name']
        if table not in tables:
            tables[table] = {'total': 0, 'nullable': 0, 'pk': 0}
        tables[table]['total'] += 1
        if row['is_nullable']:
            tables[table]['nullable'] += 1
        if row.get('is_primary_key'):
            tables[table]['pk'] += 1
    
    total_cols = len(catalog)
    total_nullable = sum(1 for c in catalog if c['is_nullable'])
    total_pk = sum(1 for c in catalog if c.get('is_primary_key'))
    
    print("\n" + "=" * 70)
    print("  SCHEMA CATALOG SUMMARY")
    print("=" * 70)
    print(f"  Tables:             {len(tables)}")
    print(f"  Total columns:      {total_cols}")
    print(f"  Primary key cols:   {total_pk}")
    print(f"  Nullable columns:   {total_nullable}")
    print(f"  NOT NULL columns:   {total_cols - total_nullable}")
    print()
    print(f"  {'Table':<40} {'Cols':<8} {'Nullable':<10} {'PK':<5}")
    print("-" * 70)
    
    for table in sorted(tables.keys()):
        stats = tables[table]
        print(f"  {table:<40} {stats['total']:<8} {stats['nullable']:<10} {stats['pk']:<5}")
    
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Build schema catalog from SQLMesh DuckDB database"
    )
    parser.add_argument("--db", default=None,
                        help="Path to db.db (default: script directory)")
    parser.add_argument("--output", default=None,
                        help="Output CSV path (default: seeds/schema_catalog.csv)")
    parser.add_argument("--schema", nargs='+', default=['sqlmesh__staging'],
                        help="Schemas to catalog (default: sqlmesh__staging)")
    parser.add_argument("--infer-pk", action="store_true",
                        help="Infer primary keys from _id column names")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Print summary statistics")
    parser.add_argument("--json", action="store_true",
                        help="Also emit JSON output")
    
    args = parser.parse_args()
    script_dir = Path(__file__).parent
    
    # Default paths
    db_path = Path(args.db) if args.db else script_dir / "db.db"
    output_path = Path(args.output) if args.output else script_dir / "seeds" / "schema_catalog.csv"
    
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"📊 Extracting schema from: {db_path}")
    print(f"   Target schemas: {', '.join(args.schema)}")
    
    # Build catalog
    catalog = build_catalog_from_duckdb(db_path, args.schema)
    
    if not catalog:
        print("No columns extracted.", file=sys.stderr)
        sys.exit(1)
    
    # Infer primary keys if requested
    if args.infer_pk:
        print("   Inferring primary keys from column names...")
        catalog = infer_primary_keys(catalog)
    
    # Write CSV seed
    write_csv_seed(catalog, output_path)
    print(f"✅ CSV seed: {output_path} ({len(catalog)} rows)")
    
    # Write JSON if requested
    if args.json:
        json_path = output_path.with_suffix('.json')
        write_json_file(catalog, json_path)
        print(f"✅ JSON:     {json_path}")
    
    # Print summary if requested
    if args.summary:
        print_summary(catalog)


if __name__ == "__main__":
    main()
