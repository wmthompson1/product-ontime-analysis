#!/usr/bin/env python3
"""
Debug SQL generation process to identify where it's failing
"""

import sys
import os
sys.path.append('app')

from semantic_layer import SemanticLayer, QueryRequest

def debug_sql_generation():
    """Debug the SQL generation process step by step"""
    print("🔍 DEBUGGING SQL GENERATION PROCESS")
    print("=" * 50)
    
    layer = SemanticLayer()
    query = "Show suppliers with delivery performance below 95%"
    
    print(f"1. Input Query: {query}")
    print()
    
    # Create request
    request = QueryRequest(natural_language=query)
    print(f"2. Request Created: {request}")
    print()
    
    try:
        # Step 1: Classify complexity
        complexity = layer._classify_query_complexity(query)
        print(f"3. Complexity Classification: {complexity}")
        print()
        
        # Step 2: Prepare context
        context = layer._prepare_context(request)
        print(f"4. Context Keys: {list(context.keys())}")
        print(f"   Schema Context Length: {len(context.get('schema_context', ''))}")
        print(f"   Schema Preview: {context.get('schema_context', '')[:100]}...")
        print()
        
        # Step 3: Select template  
        from semantic_layer import QueryComplexity
        template_name = "complex" if complexity != QueryComplexity.SIMPLE else "simple"
        template = layer.templates[template_name]
        print(f"5. Template Selected: {template_name}")
        print(f"   Template Preview: {template[:150]}...")
        print()
        
        # Step 4: Format prompt
        prompt = template.format(
            user_query=query,
            schema_context=context["schema_context"]
        )
        print(f"6. Formatted Prompt Length: {len(prompt)}")
        print(f"   Prompt Preview: {prompt[:200]}...")
        print()
        
        # Step 5: Check if OpenAI API key is available
        openai_key = os.getenv('OPENAI_API_KEY')
        print(f"7. OpenAI API Key Available: {bool(openai_key)}")
        if openai_key:
            print(f"   Key Preview: {openai_key[:8]}...")
        print()
        
        # If no API key, simulate response for testing
        if not openai_key:
            print("⚠️  No OpenAI API key found. Simulating response for testing...")
            simulated_response = """SQL: SELECT supplier_name, AVG(delivery_performance) as avg_performance 
FROM suppliers s 
JOIN deliveries d ON s.supplier_id = d.supplier_id 
WHERE d.delivery_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY s.supplier_name 
HAVING AVG(delivery_performance) < 0.95
ORDER BY avg_performance ASC

EXPLANATION: Shows suppliers with delivery performance below 95% threshold
CONFIDENCE: 0.85"""
            
            print(f"8. Simulated Response: {simulated_response}")
            print()
            
            # Test parsing
            parsed = layer._parse_response(simulated_response)
            print(f"9. Parsed Results:")
            print(f"   SQL Found: {bool(parsed['sql'])}")
            print(f"   SQL: {parsed['sql']}")
            print(f"   Explanation: {parsed['explanation']}")
            print(f"   Confidence: {parsed['confidence']}")
            print()
            
            # Test safety validation
            from schema_context import validate_sql_safety
            is_safe, msg = validate_sql_safety(parsed['sql'])
            print(f"10. Safety Validation:")
            print(f"    Safe: {is_safe}")
            print(f"    Message: {msg}")
            
        else:
            # Try actual generation
            print("8. Attempting actual SQL generation...")
            try:
                response = layer._generate_sql_with_openai(prompt)
                print(f"   Raw Response: {response['content'][:200]}...")
                
                parsed = layer._parse_response(response['content'])
                print(f"   Parsed SQL: {parsed['sql'][:100]}...")
                
                from schema_context import validate_sql_safety
                is_safe, msg = validate_sql_safety(parsed['sql'])
                print(f"   Safety Check: {is_safe} - {msg}")
                
            except Exception as e:
                print(f"   ❌ Generation Error: {e}")
        
    except Exception as e:
        print(f"❌ Debug Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sql_generation()