"""
FastAPI Application for RAG-assisted SQL Semantic Layer
Provides secure, intelligent natural language to SQL conversion
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import semantic layer components
from app.semantic_layer import (
    SemanticLayer, QueryRequest, QueryResult, QueryComplexity,
    generate_sql_from_nl, semantic_layer
)
from app.ARANGO_executor import (
    DatabaseExecutor, ExecutionResult, execute_safe_query, db_executor
)
from app.schema_context import (
    get_schema_context, schema_inspector, validate_sql_safety
)

# Initialize FastAPI app
app = FastAPI(
    title="RAG-Assisted SQL Semantic Layer",
    description="Secure natural language to SQL conversion with LangChain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class NaturalLanguageQuery(BaseModel):
    query: str = Field(..., description="Natural language query")
    user_id: Optional[str] = Field(None, description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_results: int = Field(100, ge=1, le=10000, description="Maximum results to return")
    tables_hint: Optional[List[str]] = Field(None, description="Hint about which tables to focus on")
    execute: bool = Field(False, description="Whether to execute the query immediately")

class SQLQuery(BaseModel):
    sql: str = Field(..., description="SQL query to validate/execute")
    parameters: List[Any] = Field(default_factory=list, description="Query parameters")
    user_id: Optional[str] = Field(None, description="User identifier")

class QueryResponse(BaseModel):
    query_id: str
    sql_query: str
    parameters: List[Any]
    confidence_score: float
    complexity: str
    explanation: str
    safety_check: bool
    estimated_cost: Optional[float] = None
    execution_result: Optional[Dict[str, Any]] = None
    timestamp: datetime

class ExecutionResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    error_message: Optional[str] = None
    query_id: Optional[str] = None

# Dependency injection
def get_semantic_layer() -> SemanticLayer:
    return semantic_layer

def get_db_executor() -> DatabaseExecutor:
    return db_executor

# API Endpoints

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "RAG-Assisted SQL Semantic Layer",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "convert": "/api/v1/convert",
            "execute": "/api/v1/execute", 
            "validate": "/api/v1/validate",
            "schema": "/api/v1/schema",
            "stats": "/api/v1/stats"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check(db: DatabaseExecutor = Depends(get_db_executor)):
    """Comprehensive health check"""
    
    db_status = db.test_connection()
    
    return {
        "status": "healthy" if db_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "semantic_layer": "operational",
        "timestamp": datetime.now().isoformat(),
        "stats": db.get_execution_stats()
    }

@app.post("/api/v1/convert", response_model=QueryResponse, tags=["Query Conversion"])
async def convert_natural_language_to_sql(
    nl_query: NaturalLanguageQuery,
    semantic: SemanticLayer = Depends(get_semantic_layer),
    db: DatabaseExecutor = Depends(get_db_executor)
):
    """Convert natural language to SQL with optional execution"""
    
    try:
        # Create query request
        request = QueryRequest(
            natural_language=nl_query.query,
            user_id=nl_query.user_id,
            context=nl_query.context,
            max_results=nl_query.max_results,
            tables_hint=nl_query.tables_hint
        )
        
        # Process with semantic layer
        query_result = semantic.process_query(request)
        
        # Generate query ID
        query_id = f"{nl_query.user_id or 'anonymous'}_{int(datetime.now().timestamp())}"
        
        # Prepare response
        response_data = {
            "query_id": query_id,
            "sql_query": query_result.sql_query,
            "parameters": query_result.parameters,
            "confidence_score": query_result.confidence_score,
            "complexity": query_result.complexity.value,
            "explanation": query_result.explanation,
            "safety_check": query_result.safety_check,
            "estimated_cost": query_result.estimated_cost,
            "timestamp": datetime.now()
        }
        
        # Execute if requested
        if nl_query.execute and query_result.safety_check:
            execution_result = db.execute_query(query_result, nl_query.user_id)
            response_data["execution_result"] = {
                "success": execution_result.success,
                "data": execution_result.data,
                "row_count": execution_result.row_count,
                "execution_time_ms": execution_result.execution_time_ms,
                "error_message": execution_result.error_message
            }
        
        return QueryResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query conversion failed: {str(e)}")

@app.post("/api/v1/execute", response_model=ExecutionResponse, tags=["Query Execution"])
async def execute_sql_query(
    sql_query: SQLQuery,
    db: DatabaseExecutor = Depends(get_db_executor)
):
    """Execute a SQL query safely"""
    
    try:
        # Validate safety
        is_safe, safety_message = validate_sql_safety(sql_query.sql)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"Unsafe query: {safety_message}")
        
        # Create query result object
        query_result = QueryResult(
            sql_query=sql_query.sql,
            parameters=sql_query.parameters,
            confidence_score=1.0,  # Direct SQL has full confidence
            complexity=QueryComplexity.SIMPLE,
            explanation="Direct SQL execution",
            safety_check=True
        )
        
        # Execute
        execution_result = db.execute_query(query_result, sql_query.user_id)
        
        return ExecutionResponse(
            success=execution_result.success,
            data=execution_result.data,
            row_count=execution_result.row_count,
            execution_time_ms=execution_result.execution_time_ms,
            error_message=execution_result.error_message,
            query_id=execution_result.query_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@app.post("/api/v1/validate", tags=["Query Validation"])
async def validate_sql_query(sql_query: SQLQuery):
    """Validate a SQL query for safety and syntax"""
    
    try:
        # Safety validation
        is_safe, safety_message = validate_sql_safety(sql_query.sql)
        
        # Syntax validation (basic)
        syntax_issues = []
        sql_upper = sql_query.sql.upper().strip()
        
        if not sql_upper.startswith(('SELECT', 'WITH')):
            syntax_issues.append("Query must start with SELECT or WITH")
        
        if sql_upper.count('(') != sql_upper.count(')'):
            syntax_issues.append("Unmatched parentheses")
        
        return {
            "is_valid": is_safe and len(syntax_issues) == 0,
            "safety_check": is_safe,
            "safety_message": safety_message,
            "syntax_issues": syntax_issues,
            "recommendations": [
                "Use parameterized queries with %s placeholders",
                "Add LIMIT clause for large result sets",
                "Consider indexing for performance"
            ] if is_safe else ["Address safety issues before execution"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.get("/api/v1/schema", tags=["Schema Information"])
async def get_ARANGO_schema(
    table_names: Optional[List[str]] = Query(None, description="Specific tables to inspect"),
    include_samples: bool = Query(False, description="Include sample data"),
):
    """Get database schema information"""
    
    try:
        if table_names:
            schema_context = get_schema_context(table_names)
            
            detailed_info = {}
            for table in table_names:
                schema = schema_inspector.get_table_schema(table)
                if schema:
                    detailed_info[table] = schema
                    
                    if include_samples:
                        samples = schema_inspector.get_sample_data(table, 3)
                        detailed_info[table]["sample_data"] = samples
            
            return {
                "schema_context": schema_context,
                "detailed_schemas": detailed_info,
                "requested_tables": table_names
            }
        else:
            # Get all tables
            all_tables = schema_inspector.get_all_tables()
            schema_context = get_schema_context()
            
            return {
                "schema_context": schema_context,
                "available_tables": all_tables,
                "table_count": len(all_tables)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema retrieval failed: {str(e)}")

@app.get("/api/v1/suggestions", tags=["Query Assistance"])
async def get_query_suggestions(
    partial_query: str = Query(..., description="Partial query to get suggestions for"),
    semantic: SemanticLayer = Depends(get_semantic_layer)
):
    """Get query suggestions based on partial input"""
    
    try:
        suggestions = semantic.get_query_suggestions(partial_query)
        
        return {
            "partial_query": partial_query,
            "suggestions": suggestions,
            "available_tables": schema_inspector.get_all_tables()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")

@app.get("/api/v1/stats", tags=["Monitoring"])
async def get_system_stats(db: DatabaseExecutor = Depends(get_db_executor)):
    """Get system execution statistics"""
    
    try:
        db_stats = db.get_execution_stats()
        
        return {
            "ARANGO_stats": db_stats,
            "system_info": {
                "available_tables": len(schema_inspector.get_all_tables()),
                "openai_api_configured": bool(os.getenv("OPENAI_API_KEY")),
                "ARANGO_connected": db.test_connection()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.post("/api/v1/explain", tags=["Query Analysis"])
async def explain_query_plan(
    sql_query: SQLQuery,
    db: DatabaseExecutor = Depends(get_db_executor)
):
    """Get execution plan for a query"""
    
    try:
        # Validate safety first
        is_safe, safety_message = validate_sql_safety(sql_query.sql)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"Unsafe query: {safety_message}")
        
        # Get execution plan
        plan_result = db.explain_query(sql_query.sql, sql_query.parameters)
        
        return {
            "sql_query": sql_query.sql,
            "execution_plan": plan_result,
            "safety_validated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query explanation failed: {str(e)}")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)