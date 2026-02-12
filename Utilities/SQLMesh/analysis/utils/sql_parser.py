"""
SQL Parser for analyzing SQL queries using sqlglot.

This module provides comprehensive SQL parsing capabilities for:
- Table extraction from queries
- Column extraction with ambiguity detection
- JOIN analysis
- Query complexity metrics

NO SQL EXECUTION - Only static analysis using sqlglot.
"""

import sqlglot
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SQLParser:
    """
    Parse SQL queries and extract metadata using sqlglot.
    
    This class provides methods for analyzing SQL queries without executing them.
    All operations are static analysis only - no database connections required.
    """
    
    def __init__(self, dialect: str = "tsql"):
        """
        Initialize the SQL parser.
        
        Args:
            dialect: SQL dialect (default: tsql for SQL Server)
        """
        self.dialect = dialect
    
    def extract_tables_from_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Extract all table references from a SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of dictionaries with table information:
            - full_name: Fully qualified table name
            - database: Database name (if present)
            - schema: Schema name (if present)
            - table: Table name
            - alias: Table alias (if used)
        """
        tables = []
        
        try:
            # Parse the SQL query
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            
            # Extract tables from the parsed query
            for table in parsed.find_all(sqlglot.exp.Table):
                table_info = {
                    'full_name': table.sql(dialect=self.dialect),
                    'database': table.catalog if hasattr(table, 'catalog') and table.catalog else None,
                    'schema': table.db if hasattr(table, 'db') and table.db else None,
                    'table': table.name,
                    'alias': table.alias if hasattr(table, 'alias') and table.alias else None
                }
                tables.append(table_info)
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing query: {e}")
            # Try to extract table names using fallback method
            tables = self._fallback_table_extraction(sql)
        
        return tables
    
    def _fallback_table_extraction(self, sql: str) -> List[Dict[str, Any]]:
        """
        Fallback method for extracting table names when parsing fails.
        Uses simple pattern matching.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of table dictionaries with basic information
        """
        import re
        tables = []
        
        # Pattern to match table references: [database].[schema].[table] or [schema].[table] or [table]
        # Also handles WITH (NOLOCK) and other table hints
        pattern = r'(?:FROM|JOIN)\s+(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?)(?:\s+(?:WITH\s*\([^)]+\)|\s+as\s+)?(?:\[?(\w+)\]?)?)?'
        
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        
        for match in matches:
            groups = match.groups()
            if len(groups) >= 3:
                db_or_schema1, schema_or_table, table_name, alias = groups[0], groups[1], groups[2], groups[3] if len(groups) > 3 else None
                
                # Determine structure based on presence of parts
                if db_or_schema1 and schema_or_table and table_name:
                    # database.schema.table
                    table_info = {
                        'full_name': f"{db_or_schema1}.{schema_or_table}.{table_name}",
                        'database': db_or_schema1,
                        'schema': schema_or_table,
                        'table': table_name,
                        'alias': alias
                    }
                elif schema_or_table and table_name:
                    # schema.table or database.table
                    table_info = {
                        'full_name': f"{schema_or_table}.{table_name}",
                        'database': None,
                        'schema': schema_or_table,
                        'table': table_name,
                        'alias': alias
                    }
                else:
                    # just table
                    table_info = {
                        'full_name': table_name,
                        'database': None,
                        'schema': None,
                        'table': table_name,
                        'alias': alias
                    }
                
                tables.append(table_info)
        
        return tables
    
    def extract_tables_from_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract table references from a SQL file.
        
        Args:
            file_path: Path to SQL file
            
        Returns:
            Dictionary with:
            - file_path: Path to the file
            - file_name: Name of the file
            - tables: List of table dictionaries
            - parse_success: Whether parsing was successful
            - error: Error message if parsing failed
        """
        result = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'tables': [],
            'parse_success': True,
            'error': None
        }
        
        try:
            # Read SQL file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sql = f.read()
            
            # Extract tables
            result['tables'] = self.extract_tables_from_query(sql)
            
        except Exception as e:
            result['parse_success'] = False
            result['error'] = str(e)
            logger.error(f"❌ Error reading file {file_path}: {e}")
        
        return result
    
    def extract_columns_from_query(self, sql: str) -> Dict[str, Any]:
        """
        Extract column references from a SQL query.
        Detects ambiguous columns (columns without explicit table qualifiers).
        
        Args:
            sql: SQL query string
            
        Returns:
            Dictionary with:
            - columns: List of column dictionaries
            - ambiguous_columns: List of column names that lack table qualifiers
            - total_columns: Total number of columns found
        """
        columns = []
        ambiguous = set()
        
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            
            # Extract columns from SELECT, WHERE, JOIN, etc.
            for column in parsed.find_all(sqlglot.exp.Column):
                col_info = {
                    'name': column.name,
                    'table': column.table if hasattr(column, 'table') and column.table else None,
                    'full_name': column.sql(dialect=self.dialect)
                }
                columns.append(col_info)
                
                # Check for ambiguity (no table qualifier)
                if not col_info['table']:
                    ambiguous.add(col_info['name'])
        
        except Exception as e:
            logger.warning(f"⚠️ Error extracting columns: {e}")
        
        return {
            'columns': columns,
            'ambiguous_columns': sorted(list(ambiguous)),
            'total_columns': len(columns)
        }
    
    def extract_joins_from_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Extract JOIN information from a SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            List of JOIN dictionaries with:
            - join_type: Type of join (INNER, LEFT, RIGHT, etc.)
            - left_table: Left table in join
            - right_table: Right table in join
            - condition: Join condition
        """
        joins = []
        
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            
            # Extract JOIN expressions
            for join in parsed.find_all(sqlglot.exp.Join):
                join_info = {
                    'join_type': join.side if hasattr(join, 'side') else 'INNER',
                    'right_table': join.this.sql(dialect=self.dialect) if hasattr(join, 'this') else None,
                    'condition': join.on.sql(dialect=self.dialect) if hasattr(join, 'on') and join.on else None
                }
                joins.append(join_info)
        
        except Exception as e:
            logger.warning(f"⚠️ Error extracting joins: {e}")
        
        return joins
    
    def analyze_query_complexity(self, sql: str) -> Dict[str, Any]:
        """
        Analyze the complexity of a SQL query.
        
        Args:
            sql: SQL query string
            
        Returns:
            Dictionary with complexity metrics:
            - num_tables: Number of tables referenced
            - num_joins: Number of JOIN operations
            - num_subqueries: Number of subqueries
            - num_ctes: Number of CTEs (WITH clauses)
            - has_aggregation: Whether query uses aggregation
            - has_window_functions: Whether query uses window functions
            - complexity_score: Overall complexity score (0-100)
        """
        complexity = {
            'num_tables': 0,
            'num_joins': 0,
            'num_subqueries': 0,
            'num_ctes': 0,
            'has_aggregation': False,
            'has_window_functions': False,
            'complexity_score': 0
        }
        
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            
            # Count tables
            complexity['num_tables'] = len(list(parsed.find_all(sqlglot.exp.Table)))
            
            # Count joins
            complexity['num_joins'] = len(list(parsed.find_all(sqlglot.exp.Join)))
            
            # Count subqueries
            complexity['num_subqueries'] = len(list(parsed.find_all(sqlglot.exp.Subquery)))
            
            # Count CTEs
            complexity['num_ctes'] = len(list(parsed.find_all(sqlglot.exp.CTE)))
            
            # Check for aggregation
            complexity['has_aggregation'] = any(parsed.find_all(sqlglot.exp.AggFunc))
            
            # Check for window functions
            complexity['has_window_functions'] = any(parsed.find_all(sqlglot.exp.Window))
            
            # Calculate complexity score (0-100)
            score = 0
            score += min(complexity['num_tables'] * 5, 20)  # Max 20 points for tables
            score += min(complexity['num_joins'] * 8, 30)   # Max 30 points for joins
            score += min(complexity['num_subqueries'] * 10, 25)  # Max 25 points for subqueries
            score += min(complexity['num_ctes'] * 8, 15)    # Max 15 points for CTEs
            score += 5 if complexity['has_aggregation'] else 0
            score += 5 if complexity['has_window_functions'] else 0
            
            complexity['complexity_score'] = min(score, 100)
        
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing complexity: {e}")
        
        return complexity


# Example usage and testing
if __name__ == "__main__":
    parser = SQLParser(dialect="tsql")
    
    # Test query
    test_query = """
    SELECT a.[FILE NUMBER], e.[First Name], sum(b.Visual_Hours) as 'Visual Hours'
    FROM LIVESupplemental.dbo.ADP_DAILY_HOURS a WITH (NOLOCK)
    INNER JOIN LIVESupplemental.dbo.ADP_EMP e ON a.[FILE NUMBER] = e.[File Number]
    LEFT JOIN (
        SELECT EMPLOYEE_ID, sum(HOURS_WORKED) as Visual_Hours
        FROM LIVE.dbo.LABOR_TICKET
        WHERE transaction_date BETWEEN @date1 AND @date2
        GROUP BY EMPLOYEE_ID
    ) b ON a.[FILE NUMBER] = b.EMPLOYEE
    WHERE a.PAYDATE BETWEEN @date1 AND @date2
    """
    
    print("📊 Testing SQL Parser")
    print("=" * 60)
    
    # Test table extraction
    print("\n✅ Tables:")
    tables = parser.extract_tables_from_query(test_query)
    for table in tables:
        print(f"  - {table['full_name']}")
    
    # Test complexity analysis
    print("\n✅ Complexity:")
    complexity = parser.analyze_query_complexity(test_query)
    print(f"  - Tables: {complexity['num_tables']}")
    print(f"  - Joins: {complexity['num_joins']}")
    print(f"  - Subqueries: {complexity['num_subqueries']}")
    print(f"  - Complexity Score: {complexity['complexity_score']}/100")
