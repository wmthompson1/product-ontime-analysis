"""
Safe Database Executor for RAG-assisted SQL queries
Handles query execution with comprehensive safety and monitoring
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.semantic_layer import QueryResult
from app.schema_context import validate_sql_safety

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Result of query execution with metadata"""
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    error_message: Optional[str] = None
    query_id: Optional[str] = None

@dataclass
class ExecutionLimits:
    """Execution limits for safety"""
    max_execution_time_ms: int = 30000  # 30 seconds
    max_rows_returned: int = 10000
    max_memory_mb: int = 512
    timeout_seconds: int = 45

class DatabaseExecutor:
    """Safe database executor with monitoring and limits"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.limits = ExecutionLimits()
        
        # Initialize connection pool
        self.engine = create_engine(
            self.database_url,
            poolclass=StaticPool,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False  # Set to True for SQL debugging
        )
        
        # Query execution stats
        self.execution_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0,
            "blocked_unsafe_queries": 0
        }
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = self.engine.connect()
            yield conn
        finally:
            if conn:
                conn.close()
    
    def _validate_query_limits(self, sql: str) -> Tuple[bool, str]:
        """Validate query against execution limits"""
        
        # Check for potentially expensive operations
        sql_upper = sql.upper()
        
        expensive_patterns = [
            'CROSS JOIN',
            'CARTESIAN',
            '* FROM',  # Discourage SELECT *
        ]
        
        for pattern in expensive_patterns:
            if pattern in sql_upper:
                return False, f"Potentially expensive operation detected: {pattern}"
        
        # Check for missing LIMIT on potentially large results
        if 'SELECT' in sql_upper and 'LIMIT' not in sql_upper and 'COUNT' not in sql_upper:
            # Auto-add limit for safety
            sql_with_limit = sql.rstrip(';') + f' LIMIT {self.limits.max_rows_returned}'
            return True, f"Auto-added LIMIT clause: {sql_with_limit}"
        
        return True, "Query passed limit validation"
    
    def _execute_with_timeout(self, connection, sql: str, parameters: List[Any]) -> Tuple[List[Dict], float]:
        """Execute query with timeout and monitoring"""
        
        start_time = time.time()
        
        try:
            # Set query timeout
            connection.execute(text(f"SET statement_timeout = {self.limits.timeout_seconds * 1000}"))
            
            # Execute the query
            result = connection.execute(text(sql), parameters)
            
            # Fetch results with row limit
            rows = []
            row_count = 0
            
            for row in result:
                if row_count >= self.limits.max_rows_returned:
                    logger.warning(f"Query returned more than {self.limits.max_rows_returned} rows, truncating")
                    break
                
                rows.append(dict(row._mapping))
                row_count += 1
            
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return rows, execution_time
            
        except psycopg2.OperationalError as e:
            if "timeout" in str(e).lower():
                raise TimeoutError(f"Query exceeded {self.limits.timeout_seconds}s timeout")
            raise
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed after {execution_time:.2f}ms: {str(e)}")
            raise
    
    def execute_query(self, query_result: QueryResult, user_id: str = None) -> ExecutionResult:
        """Execute a SQL query safely with comprehensive monitoring"""
        
        query_id = f"{user_id or 'anonymous'}_{int(time.time())}"
        
        logger.info(f"Executing query {query_id}: {query_result.sql_query[:100]}...")
        
        # Update stats
        self.execution_stats["total_queries"] += 1
        
        try:
            # 1. Final safety validation
            is_safe, safety_message = validate_sql_safety(query_result.sql_query)
            if not is_safe:
                self.execution_stats["blocked_unsafe_queries"] += 1
                return ExecutionResult(
                    success=False,
                    data=[],
                    row_count=0,
                    execution_time_ms=0.0,
                    error_message=f"Safety check failed: {safety_message}",
                    query_id=query_id
                )
            
            # 2. Validate execution limits
            limits_ok, limits_message = self._validate_query_limits(query_result.sql_query)
            if not limits_ok:
                return ExecutionResult(
                    success=False,
                    data=[],
                    row_count=0,
                    execution_time_ms=0.0,
                    error_message=f"Execution limits exceeded: {limits_message}",
                    query_id=query_id
                )
            
            # 3. Execute query
            with self.get_connection() as conn:
                rows, execution_time = self._execute_with_timeout(
                    conn, 
                    query_result.sql_query, 
                    query_result.parameters
                )
            
            # 4. Update success stats
            self.execution_stats["successful_queries"] += 1
            
            # Update average execution time
            total_successful = self.execution_stats["successful_queries"]
            current_avg = self.execution_stats["avg_execution_time"]
            self.execution_stats["avg_execution_time"] = (
                (current_avg * (total_successful - 1) + execution_time) / total_successful
            )
            
            logger.info(f"Query {query_id} completed successfully in {execution_time:.2f}ms, returned {len(rows)} rows")
            
            return ExecutionResult(
                success=True,
                data=rows,
                row_count=len(rows),
                execution_time_ms=execution_time,
                query_id=query_id
            )
            
        except TimeoutError as e:
            self.execution_stats["failed_queries"] += 1
            logger.error(f"Query {query_id} timed out: {str(e)}")
            
            return ExecutionResult(
                success=False,
                data=[],
                row_count=0,
                execution_time_ms=self.limits.timeout_seconds * 1000,
                error_message=f"Query timeout: {str(e)}",
                query_id=query_id
            )
            
        except Exception as e:
            self.execution_stats["failed_queries"] += 1
            logger.error(f"Query {query_id} failed: {str(e)}")
            
            return ExecutionResult(
                success=False,
                data=[],
                row_count=0,
                execution_time_ms=0.0,
                error_message=f"Execution error: {str(e)}",
                query_id=query_id
            )
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get current execution statistics"""
        return self.execution_stats.copy()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def explain_query(self, sql: str, parameters: List[Any] = None) -> Dict[str, Any]:
        """Get query execution plan for optimization"""
        try:
            explain_sql = f"EXPLAIN (ANALYZE false, VERBOSE false, BUFFERS false, FORMAT JSON) {sql}"
            
            with self.get_connection() as conn:
                result = conn.execute(text(explain_sql), parameters or [])
                plan = result.fetchone()[0]
                
                return {
                    "success": True,
                    "execution_plan": plan,
                    "estimated_cost": plan[0].get("Plan", {}).get("Total Cost", 0)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Global database executor instance
db_executor = DatabaseExecutor()

def execute_safe_query(query_result: QueryResult, **kwargs) -> ExecutionResult:
    """Convenience function for query execution"""
    return db_executor.execute_query(query_result, **kwargs)