#!/usr/bin/env python3
"""Quick check of current ArangoDB state"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from arango import ArangoClient

host = os.getenv('ARANGO_HOST', 'http://localhost:8529')
user = os.getenv('ARANGO_USER', 'root')
password = os.getenv('ARANGO_ROOT_PASSWORD', '')
db_name = os.getenv('ARANGO_DB', 'manufacturing_semantic_layer')

client = ArangoClient(hosts=host)
db = client.db(db_name, username=user, password=password)

print('=== Current ArangoDB State ===')
print(f'Database: {db_name}')
print(f'Host: {host}')
print()

if db.has_graph('semantic_graph'):
    graph = db.graph('semantic_graph')
    print('✅ Graph: semantic_graph EXISTS')
    print()
    
    print('Vertex Collections:')
    total_vertices = 0
    for v_coll in ['intents', 'perspectives', 'concepts', 'bindings']:
        if db.has_collection(v_coll):
            count = db.collection(v_coll).count()
            total_vertices += count
            print(f'  {v_coll:20s}: {count:3d} documents')
    
    print(f'  {"TOTAL VERTICES":20s}: {total_vertices:3d}')
    print()
    
    print('Edge Collections:')
    total_edges = 0
    for e_coll in ['operates_within', 'elevates', 'uses_definition', 'bound_to']:
        if db.has_collection(e_coll):
            count = db.collection(e_coll).count()
            total_edges += count
            print(f'  {e_coll:20s}: {count:3d} edges')
    
    print(f'  {"TOTAL EDGES":20s}: {total_edges:3d}')
else:
    print('❌ Graph: semantic_graph DOES NOT EXIST')
