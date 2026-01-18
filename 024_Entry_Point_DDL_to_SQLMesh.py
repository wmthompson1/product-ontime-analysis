"""
024 - DDL to SQLMesh Model Generator
=====================================
Parses manufacturing DDL (SQLite/PostgreSQL) and generates SQLMesh models
for creating a "digital twin" of the production schema.

Usage:
    python 024_Entry_Point_DDL_to_SQLMesh.py [--preview] [--output-dir PATH]

Features:
    - Parses CREATE TABLE statements from schema files
    - Generates staging models (stg_*) for raw data access
    - Generates seed models for reference/lookup tables
    - Applies column-level documentation
    - Maps SQLite types to DuckDB-compatible types
"""

import re
import os
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Column:
    """Represents a table column with metadata."""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    description: Optional[str] = None


@dataclass
class Table:
    """Represents a parsed table definition."""
    name: str
    columns: list[Column] = field(default_factory=list)
    is_reference_table: bool = False
    description: Optional[str] = None


# Reference/lookup tables that should be SEED models
REFERENCE_TABLES = {
    'suppliers', 'users', 'products', 'product_lines', 'production_lines',
    'industry_benchmarks', 'maintenance_targets', 'manufacturing_acronyms',
    'schema_nodes', 'schema_edges', 'schema_concepts', 
    'schema_concept_fields', 'schema_perspectives', 'schema_intents',
    'schema_intent_perspectives', 'schema_intent_concepts'
}

# Tables with time-series data suitable for INCREMENTAL
INCREMENTAL_TABLES = {
    'daily_deliveries': 'delivery_date',
    'downtime_events': 'event_start_time',
    'equipment_metrics': 'measurement_date',
    'equipment_reliability': 'measurement_period',
    'failure_events': 'failure_date',
    'financial_impact': 'event_date',
    'non_conformant_materials': 'incident_date',
    'product_defects': 'production_date',
    'production_quality': 'production_date',
    'production_schedule': 'planned_start',
    'quality_costs': 'cost_date',
    'quality_incidents': 'incident_date',
    'corrective_actions': 'target_date',
    'effectiveness_metrics': 'measurement_date'
}

# Column descriptions for manufacturing domain
COLUMN_DESCRIPTIONS = {
    'oee_score': 'Overall Equipment Effectiveness (0-100%)',
    'mtbf_hours': 'Mean Time Between Failures in hours',
    'ontime_rate': 'On-time delivery rate (0-1 scale)',
    'quality_score': 'Quality score from supplier evaluation',
    'defect_rate': 'Defect rate as percentage',
    'availability_rate': 'Equipment availability (OEE component)',
    'performance_rate': 'Equipment performance (OEE component)',
    'quality_rate': 'Equipment quality rate (OEE component)',
    'severity': 'Severity classification (Critical/Major/Minor)',
    'severity_level': 'Severity level for prioritization',
    'cost_impact': 'Financial impact in dollars',
    'downtime_hours': 'Downtime duration in hours',
    'reliability_score': 'Reliability score (0-100)',
    'efficiency_rating': 'Efficiency rating (0-100%)',
    'effectiveness_score': 'CAPA effectiveness score'
}

# Type mapping from SQLite to DuckDB
TYPE_MAP = {
    'INTEGER': 'INTEGER',
    'REAL': 'DOUBLE',
    'TEXT': 'VARCHAR',
    'BLOB': 'BLOB',
    'DATETIME': 'TIMESTAMP',
    'DATE': 'DATE',
    'BOOLEAN': 'BOOLEAN',
    'text': 'VARCHAR',  # lowercase variant
}


def parse_ddl(ddl_content: str) -> list[Table]:
    """Parse DDL content and extract table definitions."""
    tables = []
    
    # Match CREATE TABLE statements
    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);',
        re.IGNORECASE | re.DOTALL
    )
    
    for match in create_pattern.finditer(ddl_content):
        table_name = match.group(1).lower()
        columns_block = match.group(2)
        
        # Skip INSERT statements that might be in the same block
        if 'INSERT INTO' in columns_block:
            columns_block = columns_block.split('INSERT INTO')[0]
        
        table = Table(
            name=table_name,
            is_reference_table=table_name in REFERENCE_TABLES
        )
        
        # Parse column definitions
        for line in columns_block.split('\n'):
            line = line.strip().rstrip(',')
            if not line or line.startswith('--'):
                continue
            
            # Skip constraints
            if any(kw in line.upper() for kw in ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE(', 'CHECK(']):
                if not line.upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK')):
                    pass  # Column definition with inline constraint
                else:
                    continue
            
            # Parse column: name TYPE [constraints]
            col_match = re.match(r'(\w+)\s+(\w+(?:\([^)]+\))?)(.*)', line)
            if col_match:
                col_name = col_match.group(1).lower()
                col_type = col_match.group(2).upper()
                constraints = col_match.group(3).upper() if col_match.group(3) else ''
                
                # Skip if it's a constraint keyword
                if col_name.upper() in ('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT'):
                    continue
                
                column = Column(
                    name=col_name,
                    data_type=map_type(col_type),
                    nullable='NOT NULL' not in constraints,
                    is_primary_key='PRIMARY KEY' in constraints or col_name.endswith('_id'),
                    default=extract_default(constraints),
                    description=COLUMN_DESCRIPTIONS.get(col_name)
                )
                table.columns.append(column)
        
        if table.columns:
            tables.append(table)
    
    return tables


def map_type(sqlite_type: str) -> str:
    """Map SQLite type to DuckDB type."""
    # Remove size constraints like VARCHAR(255)
    base_type = re.sub(r'\(.*\)', '', sqlite_type).upper()
    return TYPE_MAP.get(base_type, 'VARCHAR')


def extract_default(constraints: str) -> Optional[str]:
    """Extract DEFAULT value from constraints."""
    match = re.search(r'DEFAULT\s+([^\s,]+)', constraints, re.IGNORECASE)
    return match.group(1) if match else None


def generate_staging_model(table: Table, schema: str = 'staging') -> str:
    """Generate a SQLMesh staging model for a table."""
    
    # Determine model kind
    if table.name in INCREMENTAL_TABLES:
        time_col = INCREMENTAL_TABLES[table.name]
        kind_block = f"""kind INCREMENTAL_BY_TIME_RANGE (
    time_column {time_col}
  ),
  cron '@daily',"""
    elif table.is_reference_table:
        kind_block = "kind FULL,"
    else:
        kind_block = "kind FULL,"
    
    # Build column descriptions
    col_docs = []
    for col in table.columns:
        if col.description:
            col_docs.append(f"    {col.name} '{col.description}'")
    
    newline = '\n'
    columns_block = ""
    if col_docs:
        col_docs_str = (',' + newline).join(col_docs)
        columns_block = f""",
  columns (
{col_docs_str}
  )"""
    
    # Determine grain (primary key)
    pk_cols = [c.name for c in table.columns if c.is_primary_key]
    grain = pk_cols[0] if len(pk_cols) == 1 else f"({', '.join(pk_cols)})" if pk_cols else None
    grain_block = f"grain {grain}" if grain else ""
    
    # Build audits
    audits = []
    for col in table.columns:
        if col.is_primary_key and not col.nullable:
            audits.append(f"UNIQUE_VALUES(columns = ({col.name}))")
            audits.append(f"NOT_NULL(columns = ({col.name}))")
            break
    
    audit_block = ""
    if audits:
        audit_sep = ',\n    '
        audit_block = f""",
  audits (
    {audit_sep.join(audits)}
  )"""
    
    # Build SELECT columns
    select_cols = []
    for col in table.columns:
        # Apply type casting where needed
        if col.data_type == 'TIMESTAMP' and 'CURRENT_TIMESTAMP' in (col.default or ''):
            select_cols.append(f"  COALESCE({col.name}, CURRENT_TIMESTAMP) AS {col.name}")
        elif col.data_type == 'DATE' and 'CURRENT_DATE' in (col.default or ''):
            select_cols.append(f"  COALESCE({col.name}, CURRENT_DATE) AS {col.name}")
        else:
            select_cols.append(f"  {col.name}")
    
    # Build WHERE clause for incremental
    where_clause = ""
    if table.name in INCREMENTAL_TABLES:
        time_col = INCREMENTAL_TABLES[table.name]
        where_clause = f"\nWHERE {time_col} BETWEEN @start_ds AND @end_ds"
    
    # Assemble MODEL block parts
    model_parts = [f"name {schema}.stg_{table.name}", kind_block.rstrip(',')]
    if grain_block:
        model_parts.append(grain_block)
    
    comma_newline = ',\n'
    comma_newline_indent = ',\n  '
    select_cols_str = comma_newline.join(select_cols)
    model_parts_str = comma_newline_indent.join(model_parts)
    
    model = f"""MODEL (
  {model_parts_str}{audit_block}{columns_block}
);

SELECT
{select_cols_str}
FROM raw.{table.name}{where_clause};
"""
    return model


def generate_seed_csv_placeholder(table: Table) -> str:
    """Generate a placeholder CSV header for seed tables."""
    headers = [col.name for col in table.columns]
    return ','.join(headers) + '\n'


def generate_all_models(
    ddl_path: str,
    output_dir: str = 'Utilities/SQLMesh/models/staging',
    preview: bool = False
) -> dict[str, str]:
    """Parse DDL and generate all SQLMesh models."""
    
    with open(ddl_path, 'r') as f:
        ddl_content = f.read()
    
    tables = parse_ddl(ddl_content)
    models = {}
    
    print(f"Parsed {len(tables)} tables from {ddl_path}")
    print("-" * 60)
    
    for table in tables:
        model_content = generate_staging_model(table)
        model_filename = f"stg_{table.name}.sql"
        models[model_filename] = model_content
        
        kind = "INCREMENTAL" if table.name in INCREMENTAL_TABLES else "FULL"
        print(f"  {table.name:35} -> {model_filename:40} [{kind}]")
    
    print("-" * 60)
    print(f"Generated {len(models)} models")
    
    if not preview:
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for filename, content in models.items():
            filepath = Path(output_dir) / filename
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  Wrote: {filepath}")
    else:
        print("\n[PREVIEW MODE - No files written]")
        print("\nSample model (stg_daily_deliveries.sql):")
        print("=" * 60)
        sample = models.get('stg_daily_deliveries.sql', list(models.values())[0])
        print(sample)
    
    return models


def main():
    parser = argparse.ArgumentParser(
        description='Convert manufacturing DDL to SQLMesh models'
    )
    parser.add_argument(
        '--ddl', '-d',
        default='schema/schema_sqlite.sql',
        help='Path to DDL file (default: schema/schema_sqlite.sql)'
    )
    parser.add_argument(
        '--output', '-o',
        default='Utilities/SQLMesh/models/staging',
        help='Output directory for models'
    )
    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='Preview mode - show output without writing files'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ddl):
        print(f"Error: DDL file not found: {args.ddl}")
        return 1
    
    generate_all_models(args.ddl, args.output, args.preview)
    return 0


if __name__ == '__main__':
    exit(main())
