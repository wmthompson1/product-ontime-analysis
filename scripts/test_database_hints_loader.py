#!/usr/bin/env python3
"""Quick test for DatabaseHintsLoader using current DATABASE_URL or default sqlite."""
import os
import json
from app.ARANGO_hints_loader import DatabaseHintsLoader

def main():
    url = os.environ.get('DATABASE_URL')
    print('Using DATABASE_URL:', url)
    loader = DatabaseHintsLoader()
    schema = loader.load_schema_graph()
    print('Nodes:', len(schema.get('nodes', [])))
    print('Edges:', len(schema.get('edges', [])))
    acr = loader.build_acronym_mappings()
    print('Acronyms found:', list(acr.keys())[:20])
    # write small report
    out = {'nodes': len(schema.get('nodes', [])), 'edges': len(schema.get('edges', [])), 'acronyms': list(acr.keys())}
    with open('logs/db_hints_report.json', 'w') as fh:
        json.dump(out, fh, indent=2)
    print('Wrote logs/db_hints_report.json')

if __name__ == '__main__':
    main()
