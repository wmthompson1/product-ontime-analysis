#!/usr/bin/env python3
"""
Debug the specific maintenance query that's failing
"""

import sys
sys.path.append('app')

from semantic_layer import SemanticLayer, QueryRequest

def debug_maintenance_query():
    """Debug the MTBF maintenance query specifically"""
    print("🔧 DEBUGGING MAINTENANCE QUERY")
    print("=" * 40)
    
    layer = SemanticLayer()
    query = "Show equipment with MTBF below target requiring immediate attention"
    
    print(f"Query: {query}")
    print()
    
    try:
        request = QueryRequest(natural_language=query)
        
        # Get the raw response from OpenAI
        context = layer._prepare_context(request)
        complexity = layer._classify_query_complexity(query)
        from semantic_layer import QueryComplexity
        template_name = "complex" if complexity != QueryComplexity.SIMPLE else "simple"
        template = layer.templates[template_name]
        
        prompt = template.format(
            user_query=query,
            **context
        )
        
        print("📝 Sending prompt to OpenAI...")
        response = layer._generate_sql_with_openai(prompt)
        
        print(f"🤖 Raw OpenAI Response:")
        print("-" * 30)
        print(response['content'])
        print("-" * 30)
        print()
        
        # Test parsing
        print("🔍 Parsing response...")
        parsed = layer._parse_response(response['content'])
        
        print(f"Parsed SQL: '{parsed['sql']}'")
        print(f"SQL Length: {len(parsed['sql'])}")
        print(f"SQL Empty: {parsed['sql'] == ''}")
        print(f"Explanation: {parsed['explanation']}")
        print(f"Confidence: {parsed['confidence']}")
        print()
        
        # Test safety validation
        from schema_context import validate_sql_safety
        
        if parsed['sql']:
            is_safe, msg = validate_sql_safety(parsed['sql'])
            print(f"Safety Check: {is_safe}")
            print(f"Safety Message: {msg}")
        else:
            print("⚠️ No SQL to validate - this is the problem!")
            print()
            
            # Try to extract SQL manually
            print("🛠️ Attempting manual SQL extraction...")
            content = response['content']
            
            # Look for SQL patterns
            import re
            
            # Remove markdown code blocks
            cleaned = content.replace('```sql', '').replace('```', '')
            
            # Find SELECT statements
            select_pattern = r'(SELECT[\s\S]*?(?=\n\n|\n[A-Z]+:|$))'
            matches = re.findall(select_pattern, cleaned, re.IGNORECASE)
            
            if matches:
                print(f"Found {len(matches)} SELECT statements:")
                for i, match in enumerate(matches, 1):
                    print(f"  {i}: {match.strip()[:100]}...")
            else:
                print("No SELECT statements found in response")
                
                # Check for other SQL keywords
                sql_keywords = ['FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY']
                found_keywords = [kw for kw in sql_keywords if kw in content.upper()]
                print(f"Found SQL keywords: {found_keywords}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_maintenance_query()