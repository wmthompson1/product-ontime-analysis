#!/usr/bin/env python3
"""
Test client for Manufacturing Inventory SQL Generator MCP Server

This script demonstrates how to:
1. Discover available MCP tools
2. Call the generate_sql tool
3. Retrieve schema and templates
4. Analyze CSV files

Usage:
    python test_client.py [--base-url URL]
"""

import argparse
import json
import requests
from typing import Optional


class MCPClient:
    """Simple MCP client for testing the inventory SQL generator"""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")
        self.tools = {}
        self.discovered = False
    
    def discover(self) -> dict:
        """Call the MCP discovery endpoint"""
        response = requests.get(f"{self.base_url}/mcp/discover")
        response.raise_for_status()
        
        discovery = response.json()
        self.tools = {tool["name"]: tool for tool in discovery.get("tools", [])}
        self.discovered = True
        
        return discovery
    
    def generate_sql(self, query: str, include_explanation: bool = True) -> dict:
        """Generate SQL from natural language query"""
        response = requests.post(
            f"{self.base_url}/mcp/tools/generate_sql",
            json={
                "query": query,
                "include_explanation": include_explanation
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_schema(self) -> dict:
        """Get the database schema"""
        response = requests.get(f"{self.base_url}/mcp/tools/get_schema")
        response.raise_for_status()
        return response.json()
    
    def get_templates(self, template_name: Optional[str] = None) -> dict:
        """Get SQL templates"""
        params = {}
        if template_name:
            params["template_name"] = template_name
        
        response = requests.get(
            f"{self.base_url}/mcp/tools/get_sql_templates",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_csv(self, csv_content: str) -> dict:
        """Analyze CSV content for schema suggestions"""
        response = requests.post(
            f"{self.base_url}/mcp/tools/analyze_csv",
            data={"csv_content": csv_content}
        )
        response.raise_for_status()
        return response.json()


def print_section(title: str, content: any):
    """Pretty print a section"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if isinstance(content, (dict, list)):
        print(json.dumps(content, indent=2))
    else:
        print(content)


def main():
    parser = argparse.ArgumentParser(description="Test MCP Inventory SQL Generator")
    parser.add_argument(
        "--base-url",
        default="http://localhost:7860",
        help="Base URL of the MCP server"
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Custom query to test"
    )
    args = parser.parse_args()
    
    client = MCPClient(args.base_url)
    
    print("\n" + "="*60)
    print("  Manufacturing Inventory SQL Generator - MCP Test Client")
    print("="*60)
    print(f"  Server: {args.base_url}")
    
    print("\n[1/5] Testing MCP Discovery...")
    try:
        discovery = client.discover()
        print(f"  ✓ Server: {discovery['name']} v{discovery['version']}")
        print(f"  ✓ Tools available: {len(discovery['tools'])}")
        for tool in discovery['tools']:
            print(f"    - {tool['name']}: {tool['description'][:50]}...")
    except Exception as e:
        print(f"  ✗ Discovery failed: {e}")
        return
    
    print("\n[2/5] Testing SQL Generation...")
    test_queries = [
        "Show me parts that are low on stock",
        "What is the total inventory value by category?",
        "Which suppliers have the best quality ratings?",
        "Show transaction activity for the last 30 days"
    ]
    
    if args.query:
        test_queries = [args.query]
    
    for query in test_queries:
        try:
            result = client.generate_sql(query)
            print(f"\n  Query: \"{query}\"")
            print(f"  Tables: {', '.join(result['tables_used'])}")
            print(f"  Complexity: {result['estimated_complexity']}")
            print(f"  SQL:\n{'-'*40}")
            for line in result['sql'].split('\n'):
                print(f"    {line}")
        except Exception as e:
            print(f"  ✗ Query failed: {e}")
    
    print("\n[3/5] Testing Schema Retrieval...")
    try:
        schema = client.get_schema()
        tables = list(schema['schema']['tables'].keys())
        print(f"  ✓ Tables: {', '.join(tables)}")
        for table in tables:
            cols = list(schema['schema']['tables'][table]['columns'].keys())
            print(f"    - {table}: {len(cols)} columns")
    except Exception as e:
        print(f"  ✗ Schema retrieval failed: {e}")
    
    print("\n[4/5] Testing SQL Templates...")
    try:
        templates = client.get_templates()
        print(f"  ✓ Templates available: {len(templates['templates'])}")
        for name in templates['templates'].keys():
            print(f"    - {name}")
    except Exception as e:
        print(f"  ✗ Template retrieval failed: {e}")
    
    print("\n[5/5] Testing CSV Analysis...")
    sample_csv = """part_id,part_name,quantity,unit_cost
P001,Widget A,100,25.50
P002,Widget B,50,30.00
P003,Gadget X,200,15.75
P004,Component Y,75,42.00"""
    
    try:
        analysis = client.analyze_csv(sample_csv)
        print(f"  ✓ Rows analyzed: {analysis['row_count']}")
        print(f"  ✓ Columns detected: {len(analysis['columns'])}")
        for col, info in analysis['columns'].items():
            print(f"    - {col}: {info['suggested_type']}")
    except Exception as e:
        print(f"  ✗ CSV analysis failed: {e}")
    
    print("\n" + "="*60)
    print("  Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
