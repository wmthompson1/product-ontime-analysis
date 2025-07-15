
"""
Enhanced Semantic Layer Integration
Now powered by comprehensive LangChain-based semantic layer
"""

import os
from app.semantic_layer import generate_sql_from_nl, QueryRequest
from app.database_executor import execute_safe_query
from app.schema_context import SQL_SCHEMA_DESCRIPTION

# Backward compatibility function
def generate_sql_from_nl_legacy(nl_query: str) -> str:
    """Legacy function for backward compatibility"""
    result = generate_sql_from_nl(nl_query)
    return result.sql_query

# Enhanced function with full capabilities
def process_natural_language_query(
    nl_query: str, 
    user_id: str = None,
    execute: bool = False,
    **kwargs
):
    """
    Process natural language query with full semantic layer capabilities
    
    Args:
        nl_query: Natural language query
        user_id: User identifier for tracking
        execute: Whether to execute the query
        **kwargs: Additional context parameters
    
    Returns:
        Dictionary with query result and optional execution result
    """
    
    # Convert to structured request
    request = QueryRequest(
        natural_language=nl_query,
        user_id=user_id,
        **kwargs
    )
    
    # Process with semantic layer
    query_result = generate_sql_from_nl(request)
    
    result = {
        "sql_query": query_result.sql_query,
        "parameters": query_result.parameters,
        "confidence_score": query_result.confidence_score,
        "complexity": query_result.complexity.value,
        "explanation": query_result.explanation,
        "safety_check": query_result.safety_check
    }
    
    # Execute if requested and safe
    if execute and query_result.safety_check:
        execution_result = execute_safe_query(query_result, user_id=user_id)
        result["execution_result"] = {
            "success": execution_result.success,
            "data": execution_result.data,
            "row_count": execution_result.row_count,
            "execution_time_ms": execution_result.execution_time_ms,
            "error_message": execution_result.error_message
        }
    
    return result

# Example usage and testing
if __name__ == "__main__":
    # Test the enhanced semantic layer
    test_queries = [
        "Show me all users",
        "Find users with gmail email addresses",
        "Count the total number of products",
        "Find products similar to 'wireless headphones'",
        "Get users created in the last month"
    ]
    
    print("Testing Enhanced Semantic Layer")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        
        try:
            result = process_natural_language_query(
                query, 
                user_id="test_user",
                execute=False  # Set to True to actually execute
            )
            
            print(f"   SQL: {result['sql_query']}")
            print(f"   Confidence: {result['confidence_score']:.2f}")
            print(f"   Safe: {result['safety_check']}")
            print(f"   Explanation: {result['explanation']}")
            
        except Exception as e:
            print(f"   Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Semantic layer testing complete!")
