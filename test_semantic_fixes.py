#!/usr/bin/env python3
"""
Test semantic layer fixes for SQL generation and safety validation
"""

import sys
import os
sys.path.append('app')

from semantic_layer import SemanticLayer, QueryRequest
from schema_context import validate_sql_safety

def test_safety_validation():
    """Test the improved safety validation"""
    print("🔒 TESTING SAFETY VALIDATION")
    print("=" * 40)
    
    test_cases = [
        ("SELECT * FROM suppliers", True),
        ("select supplier_name from suppliers where performance > 0.95", True),
        ("WITH ranked_suppliers AS (SELECT * FROM suppliers) SELECT * FROM ranked_suppliers", True),
        ("DROP TABLE suppliers", False),
        ("DELETE FROM suppliers", False),
        ("UPDATE suppliers SET status = 'active'", False),
        ("", False),
        ("   SELECT\n  supplier_name\n  FROM suppliers", True),
        ("(\nSELECT * FROM suppliers)", True),
    ]
    
    for sql, expected in test_cases:
        is_safe, message = validate_sql_safety(sql)
        status = "✅" if is_safe == expected else "❌"
        print(f"{status} SQL: '{sql[:30]}...' -> Safe: {is_safe} ({'Expected' if is_safe == expected else 'UNEXPECTED'})")
        if not is_safe:
            print(f"    Reason: {message}")
    
    print()

def test_semantic_layer():
    """Test semantic layer with manufacturing queries"""
    print("🧠 TESTING SEMANTIC LAYER")
    print("=" * 40)
    
    layer = SemanticLayer()
    
    test_queries = [
        "Show suppliers with delivery performance below 95%",
        "Find products with NCM rates above 2.5%",
        "Calculate OEE for critical equipment"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: {query}")
        
        try:
            request = QueryRequest(natural_language=query)
            result = layer.process_query(request)
            
            print(f"   SQL Generated: {bool(result.sql_query and result.sql_query != '')}")
            print(f"   Safety Check: {'✅' if result.safety_check else '❌'}")
            print(f"   Confidence: {result.confidence_score:.3f}")
            print(f"   SQL Preview: {result.sql_query[:60]}...")
            
            if not result.safety_check:
                print(f"   Issue: {result.explanation}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_sql_parsing():
    """Test SQL parsing from LLM responses"""
    print("📝 TESTING SQL PARSING")
    print("=" * 40)
    
    layer = SemanticLayer()
    
    # Simulate LLM responses
    test_responses = [
        """SQL: SELECT supplier_name, avg_delivery_rate FROM suppliers WHERE avg_delivery_rate < 0.95
EXPLANATION: Shows underperforming suppliers
CONFIDENCE: 0.85""",
        
        """Here's the SQL query:

SELECT 
    product_line,
    AVG(defect_rate) as avg_ncm_rate
FROM production_quality
WHERE defect_rate > 0.025
GROUP BY product_line
ORDER BY avg_ncm_rate DESC

This query finds products with NCM rates above industry standards.""",
        
        """```sql
SELECT 
    equipment_id,
    availability * performance * quality as oee_score
FROM equipment_metrics
WHERE equipment_type = 'critical'
```

The query calculates OEE for critical equipment."""
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n{i}. Parsing response type {i}:")
        try:
            parsed = layer._parse_response(response)
            print(f"   SQL Found: {bool(parsed['sql'])}")
            print(f"   SQL Preview: {parsed['sql'][:50]}...")
            print(f"   Explanation: {parsed['explanation'][:40]}...")
            print(f"   Confidence: {parsed['confidence']}")
            
            # Test safety
            if parsed['sql']:
                is_safe, msg = validate_sql_safety(parsed['sql'])
                print(f"   Safety: {'✅' if is_safe else '❌'} ({msg})")
        except Exception as e:
            print(f"   ❌ Parsing Error: {e}")

def main():
    """Run all tests"""
    print("🔬 SEMANTIC LAYER DIAGNOSTIC TESTS")
    print("=" * 50)
    print()
    
    test_safety_validation()
    test_sql_parsing()
    test_semantic_layer()
    
    print("\n" + "=" * 50)
    print("✅ Diagnostic tests completed!")

if __name__ == "__main__":
    main()