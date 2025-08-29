"""
Database Schema Context for RAG-assisted SQL Generation
Provides metadata and context about database schema for semantic layer
"""

import os
from typing import Dict, List, Any
import psycopg2
from sqlalchemy import create_engine, text, inspect
import json

# Database schema description for prompting
SQL_SCHEMA_DESCRIPTION = """
Manufacturing Intelligence Database Schema:

USERS table:
- id (INTEGER, Primary Key): Unique user identifier
- name (VARCHAR(100), NOT NULL): User's full name
- email (VARCHAR(120), UNIQUE, NOT NULL): User's email address
- created_at (TIMESTAMP): Account creation date

SUPPLIERS table:
- supplier_id (INTEGER, Primary Key): Unique supplier identifier
- supplier_name (VARCHAR(200), NOT NULL): Supplier company name
- contract_value (DECIMAL(12,2)): Annual contract value
- status (VARCHAR(50)): Active, Inactive, Under Review
- country (VARCHAR(100)): Supplier location

DAILY_DELIVERIES table:
- delivery_id (INTEGER, Primary Key): Unique delivery record
- supplier_id (INTEGER, Foreign Key → suppliers.supplier_id)
- date (DATE, NOT NULL): Delivery date
- ontime_rate (DECIMAL(5,4)): On-time delivery rate (0.0-1.0)
- total_shipments (INTEGER): Total shipments for the day
- ontime_shipments (INTEGER): On-time shipments count

PRODUCT_DEFECTS table:
- defect_id (INTEGER, Primary Key): Unique defect record
- product_line (VARCHAR(100), NOT NULL): Product line name
- production_date (DATE, NOT NULL): Production date
- defect_rate (DECIMAL(6,5)): Defect rate (0.0-1.0)
- total_produced (INTEGER): Total units produced
- defect_count (INTEGER): Number of defective units
- defect_type (VARCHAR(100)): Type of defect (NCM, Rework, Scrap)

PRODUCTION_LINES table:
- line_id (INTEGER, Primary Key): Production line identifier
- line_name (VARCHAR(100), NOT NULL): Line name
- theoretical_capacity (INTEGER): Max units per hour
- equipment_type (VARCHAR(50)): Critical, Standard, Support

PRODUCTION_METRICS table:
- metric_id (INTEGER, Primary Key): Unique metric record
- line_id (INTEGER, Foreign Key → production_lines.line_id)
- measurement_date (DATE, NOT NULL): Measurement date
- availability_rate (DECIMAL(5,4)): Equipment availability (0.0-1.0)
- performance_rate (DECIMAL(5,4)): Performance efficiency (0.0-1.0)
- quality_rate (DECIMAL(5,4)): Quality rate (0.0-1.0)
- oee_score (DECIMAL(5,4)): Overall Equipment Effectiveness

EQUIPMENT_METRICS table:
- equipment_id (INTEGER, Primary Key): Equipment identifier
- line_id (VARCHAR(50), NOT NULL): Production line identifier
- equipment_type (VARCHAR(100)): Equipment category
- equipment_name (VARCHAR(255)): Equipment name
- measurement_date (DATE, NOT NULL): Measurement date
- availability_rate (DECIMAL(5,4)): Availability factor
- performance_rate (DECIMAL(5,4)): Performance factor  
- quality_rate (DECIMAL(5,4)): Quality factor
- oee_score (DECIMAL(5,4)): Overall Equipment Effectiveness
- downtime_hours (DECIMAL(8,2)): Equipment downtime

PRODUCTION_QUALITY table:
- quality_id (INTEGER, Primary Key): Quality record identifier
- product_line (VARCHAR(100), NOT NULL): Product line name
- production_date (DATE, NOT NULL): Production date
- defect_rate (DECIMAL(6,5)): Defect rate (0.0-1.0)
- total_produced (INTEGER): Total units produced
- defect_count (INTEGER): Number of defective units
- shift_id (VARCHAR(50)): Production shift identifier

INDUSTRY_BENCHMARKS table:
- benchmark_id (INTEGER, Primary Key): Benchmark record identifier
- metric_name (VARCHAR(100), NOT NULL): KPI metric name
- industry_sector (VARCHAR(100)): Manufacturing sector
- benchmark_value (DECIMAL(10,6)): Benchmark target value
- measurement_unit (VARCHAR(50)): Unit of measurement
- benchmark_class (VARCHAR(50)): World Class, Industry Average, Minimum Acceptable

NON_CONFORMANT_MATERIALS table:
- ncm_id (INTEGER, Primary Key): NCM incident identifier
- product_line (VARCHAR(100), NOT NULL): Affected product line
- incident_date (DATE, NOT NULL): Incident occurrence date
- failure_mode (VARCHAR(200)): Description of failure
- root_cause (VARCHAR(500)): Root cause analysis
- cost_impact (DECIMAL(10,2)): Financial impact
- status (VARCHAR(50)): Open, Under Investigation, Closed

CORRECTIVE_ACTIONS table:
- capa_id (INTEGER, Primary Key): CAPA identifier
- ncm_id (INTEGER, Foreign Key → non_conformant_materials.ncm_id)
- action_description (TEXT): Corrective action description
- target_date (DATE): Target completion date
- actual_date (DATE): Actual completion date
- effectiveness_score (DECIMAL(3,2)): Effectiveness rating (1-5)
- status (VARCHAR(50)): Planning, In Progress, Completed

EQUIPMENT_RELIABILITY table:
- reliability_id (INTEGER, Primary Key): Reliability record identifier
- equipment_id (INTEGER, Foreign Key → equipment_metrics.equipment_id)
- measurement_period (DATE, NOT NULL): Monthly measurement period
- mtbf_hours (DECIMAL(10,2)): Mean Time Between Failures in hours
- target_mtbf (DECIMAL(10,2)): Target MTBF for equipment type
- failure_count (INTEGER): Number of failures in period
- operating_hours (DECIMAL(10,2)): Total operating hours in period
- reliability_score (DECIMAL(5,4)): Overall reliability rating (0.0-1.0)

FAILURE_EVENTS table:
- failure_id (INTEGER, Primary Key): Failure event identifier
- equipment_id (INTEGER, Foreign Key → equipment_metrics.equipment_id)
- failure_date (TIMESTAMP, NOT NULL): Failure occurrence date/time
- failure_type (VARCHAR(100)): Mechanical, Electrical, Software, etc.
- downtime_hours (DECIMAL(8,2)): Hours of downtime caused
- repair_cost (DECIMAL(10,2)): Cost of repair
- severity (VARCHAR(50)): Critical, Major, Minor
- root_cause (TEXT): Root cause analysis

Manufacturing KPIs:
- OTD (On-Time Delivery) = AVG(ontime_rate) from daily_deliveries
- NCM Rate = AVG(defect_rate) from product_defects where defect_type = 'NCM'
- OEE = availability_rate * performance_rate * quality_rate
- DPMO = (defect_count / total_produced) * 1,000,000
- MTBF = operating_hours / failure_count from equipment_reliability
- Industry Standards: OTD ≥95%, NCM ≤2.5%, OEE ≥85% (World Class), MTBF varies by equipment type

Security constraints:
- Only SELECT operations allowed
- Use parameter binding (%s) for user inputs
- No access to system tables
"""

class SchemaInspector:
    """Dynamically inspect database schema for enhanced context"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.engine = create_engine(self.database_url) if self.database_url else None
        self._schema_cache = {}
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific table"""
        if not self.engine:
            return {}
            
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        
        try:
            inspector = inspect(self.engine)
            
            # Get columns
            columns = inspector.get_columns(table_name)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get('constrained_columns', [])
            
            # Get foreign keys
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            # Get indexes
            indexes = inspector.get_indexes(table_name)
            
            schema_info = {
                'table_name': table_name,
                'columns': columns,
                'primary_keys': primary_keys,
                'foreign_keys': foreign_keys,
                'indexes': indexes
            }
            
            self._schema_cache[table_name] = schema_info
            return schema_info
            
        except Exception as e:
            print(f"Error inspecting table {table_name}: {e}")
            return {}
    
    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        if not self.engine:
            return []
            
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except Exception as e:
            print(f"Error getting table names: {e}")
            return []
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict]:
        """Get sample data from a table for context"""
        if not self.engine:
            return []
            
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                columns = result.keys()
                rows = result.fetchall()
                
                return [dict(zip(columns, row)) for row in rows]
                
        except Exception as e:
            print(f"Error getting sample data from {table_name}: {e}")
            return []
    
    def generate_enhanced_schema_description(self) -> str:
        """Generate a comprehensive schema description with real data context"""
        tables = self.get_all_tables()
        descriptions = [SQL_SCHEMA_DESCRIPTION, "\n=== DYNAMIC SCHEMA ANALYSIS ===\n"]
        
        for table in tables:
            schema = self.get_table_schema(table)
            if not schema:
                continue
                
            descriptions.append(f"\nTable: {table.upper()}")
            descriptions.append("-" * (len(table) + 8))
            
            # Column descriptions
            for col in schema.get('columns', []):
                col_type = col.get('type', 'UNKNOWN')
                nullable = "" if col.get('nullable', True) else ", NOT NULL"
                default = f", DEFAULT: {col.get('default')}" if col.get('default') else ""
                
                descriptions.append(f"- {col['name']} ({col_type}{nullable}{default})")
            
            # Primary keys
            if schema.get('primary_keys'):
                descriptions.append(f"Primary Key(s): {', '.join(schema['primary_keys'])}")
            
            # Foreign keys
            for fk in schema.get('foreign_keys', []):
                ref_table = fk.get('referred_table')
                ref_cols = ', '.join(fk.get('referred_columns', []))
                local_cols = ', '.join(fk.get('constrained_columns', []))
                descriptions.append(f"Foreign Key: {local_cols} → {ref_table}({ref_cols})")
            
            # Sample data for context
            samples = self.get_sample_data(table, 3)
            if samples:
                descriptions.append("Sample data:")
                for i, sample in enumerate(samples[:2], 1):
                    sample_str = ", ".join([f"{k}={v}" for k, v in sample.items()])
                    descriptions.append(f"  Example {i}: {sample_str}")
        
        return "\n".join(descriptions)

# Global schema inspector instance
schema_inspector = SchemaInspector()

def get_schema_context(table_names: List[str] = None) -> str:
    """Get schema context for specific tables or all tables"""
    if table_names:
        context = [SQL_SCHEMA_DESCRIPTION]
        for table in table_names:
            schema = schema_inspector.get_table_schema(table)
            if schema:
                context.append(f"\nDetailed schema for {table}: {json.dumps(schema, indent=2, default=str)}")
        return "\n".join(context)
    else:
        return schema_inspector.generate_enhanced_schema_description()

# Security and validation contexts
ALLOWED_OPERATIONS = {
    'SELECT', 'WITH'
}

FORBIDDEN_KEYWORDS = {
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE',
    'EXEC', 'EXECUTE', 'CALL', 'DECLARE', 'SET', 'USE'
}

SENSITIVE_TABLES = {
    'pg_user', 'pg_shadow', 'information_schema', 'pg_catalog'
}

def validate_sql_safety(sql: str) -> tuple[bool, str]:
    """Validate SQL query for safety constraints"""
    if not sql or sql.strip() == "":
        return False, "Empty SQL query"
    
    sql_upper = sql.upper().strip()
    
    # Remove comments and extra whitespace
    sql_cleaned = ' '.join(sql_upper.split())
    
    # Check for forbidden operations (more precise matching)
    forbidden_patterns = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', 
        r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bEXEC\b', 
        r'\bEXECUTE\b', r'\bCALL\b', r'\bDECLARE\b'
    ]
    
    import re
    for pattern in forbidden_patterns:
        if re.search(pattern, sql_cleaned):
            keyword = pattern.replace(r'\b', '').replace(r'\\', '')
            return False, f"Forbidden operation detected: {keyword}"
    
    # Check for sensitive table access
    for table in SENSITIVE_TABLES:
        if table.upper() in sql_upper:
            return False, f"Access to sensitive table not allowed: {table}"
    
    # More flexible start validation - allow common SQL patterns
    valid_starts = ['SELECT', 'WITH', '(SELECT', '(\nSELECT']
    starts_with_valid = any(sql_cleaned.startswith(start) for start in valid_starts)
    
    if not starts_with_valid:
        # Try to find SELECT or WITH anywhere in reasonable positions
        if 'SELECT' in sql_cleaned[:50] or 'WITH' in sql_cleaned[:20]:
            return True, "Query contains valid operations"
        return False, f"Query must start with SELECT or WITH. Found: {sql_cleaned[:30]}..."
    
    return True, "Query passed safety validation"