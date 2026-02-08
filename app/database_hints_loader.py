"""
Database-backed Contextual Hints Loader
Dynamically loads enhanced metadata from schema_edges table for production-ready hints
"""

import os
import sqlite3
from typing import Dict, List, Optional
from functools import lru_cache

from config import SQLITE_DB_PATH

class DatabaseHintsLoader:
    """Load contextual hints from database schema metadata"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or SQLITE_DB_PATH
        if not os.path.exists(self.db_path):
            raise ValueError(f"SQLite database not found at: {self.db_path}")
    
    def _get_connection(self):
        """Get a SQLite connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @lru_cache(maxsize=1)
    def load_schema_graph(self) -> Dict:
        """Load complete schema graph with enhanced metadata from database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM schema_nodes ORDER BY table_name")
            nodes = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT 
                    edge_id,
                    from_table,
                    to_table,
                    relationship_type,
                    join_column,
                    weight,
                    join_column_description,
                    natural_language_alias,
                    few_shot_example,
                    context
                FROM schema_edges 
                ORDER BY edge_id
            """)
            edges = [dict(row) for row in cursor.fetchall()]
            
            return {
                'nodes': nodes,
                'edges': edges
            }
        finally:
            cursor.close()
            conn.close()
    
    def get_node_by_name(self, table_name: str) -> Optional[Dict]:
        """Get node metadata by table name"""
        schema = self.load_schema_graph()
        for node in schema['nodes']:
            if node['table_name'].lower() == table_name.lower():
                return node
        return None
    
    def get_edges_for_node(self, table_name: str) -> List[Dict]:
        """Get all edges connected to a specific node"""
        schema = self.load_schema_graph()
        edges = []
        table_lower = table_name.lower()
        
        for edge in schema['edges']:
            if (edge['from_table'].lower() == table_lower or 
                edge['to_table'].lower() == table_lower):
                edges.append(edge)
        
        return edges
    
    def get_edge_by_tables(self, from_table: str, to_table: str) -> Optional[Dict]:
        """Get edge metadata between two specific tables"""
        schema = self.load_schema_graph()
        from_lower = from_table.lower()
        to_lower = to_table.lower()
        
        for edge in schema['edges']:
            if (edge['from_table'].lower() == from_lower and 
                edge['to_table'].lower() == to_lower):
                return edge
        
        return None
    
    def build_acronym_mappings(self) -> Dict:
        """Build acronym mappings from database metadata and user-defined acronyms"""
        schema = self.load_schema_graph()
        acronyms = {}
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT acronym, definition, table_name, category
                FROM manufacturing_acronyms
                ORDER BY acronym
            """)
            user_acronyms = [dict(row) for row in cursor.fetchall()]
            
            for record in user_acronyms:
                acronym_key = record['acronym'].upper()
                acronyms[acronym_key] = {
                    'full_name': record['definition'],
                    'related_fields': [],
                    'related_tables': [record['table_name']] if record['table_name'] else [],
                    'context': f"User-defined acronym for {record['table_name'] or 'general use'}",
                    'example_sql': '',
                    'source': 'user_defined'
                }
        except sqlite3.OperationalError:
            pass
        finally:
            cursor.close()
            conn.close()
        
        for edge in schema['edges']:
            if edge.get('natural_language_alias'):
                context_text = edge.get('context', '')
                
                if 'NCM' in context_text or 'Non-Conformance' in context_text:
                    if 'NCM' not in acronyms:
                        acronyms['NCM'] = {
                            'full_name': 'Non-Conformance Material',
                            'related_fields': [],
                            'related_tables': [],
                            'context': context_text,
                            'example_sql': edge.get('few_shot_example', ''),
                            'source': 'metadata'
                        }
                    if 'source' not in acronyms['NCM'] or acronyms['NCM']['source'] != 'user_defined':
                        acronyms['NCM']['related_fields'].append(edge['join_column'])
                        acronyms['NCM']['related_tables'].extend([edge['from_table'], edge['to_table']])
                
                if 'OTD' in context_text or 'delivery' in context_text.lower():
                    if 'OTD' not in acronyms:
                        acronyms['OTD'] = {
                            'full_name': 'On-Time Delivery',
                            'related_fields': [],
                            'related_tables': [],
                            'context': context_text,
                            'example_sql': edge.get('few_shot_example', ''),
                            'source': 'metadata'
                        }
                    if 'source' not in acronyms['OTD'] or acronyms['OTD']['source'] != 'user_defined':
                        acronyms['OTD']['related_fields'].append(edge['join_column'])
                        acronyms['OTD']['related_tables'].extend([edge['from_table'], edge['to_table']])
        
        for acronym in acronyms:
            acronyms[acronym]['related_tables'] = list(set(acronyms[acronym]['related_tables']))
            acronyms[acronym]['related_fields'] = list(set(acronyms[acronym]['related_fields']))
        
        return acronyms
    
    def get_contextual_hints_for_query(self, query: str, table_name: str = None) -> List[Dict]:
        """Generate contextual hints from database metadata"""
        hints = []
        
        if table_name:
            edges = self.get_edges_for_node(table_name)
            
            for edge in edges:
                if edge.get('context'):
                    hint = {
                        'text': f"{edge['from_table']} -> {edge['to_table']}",
                        'type': 'table_relationship',
                        'confidence': 0.9,
                        'explanation': edge.get('join_column_description', edge['context']),
                        'suggested_fields': [edge['join_column']],
                        'example_query': edge.get('few_shot_example'),
                        'natural_alias': edge.get('natural_language_alias'),
                        'context': edge.get('context')
                    }
                    hints.append(hint)
        
        acronyms = self.build_acronym_mappings()
        for acronym, data in acronyms.items():
            if acronym in query.upper():
                hint = {
                    'text': f"{acronym} = {data['full_name']}",
                    'type': 'acronym',
                    'confidence': 0.95,
                    'explanation': data['context'],
                    'suggested_fields': data['related_fields'][:5],
                    'example_query': data.get('example_sql'),
                    'related_tables': data['related_tables']
                }
                hints.append(hint)
        
        return hints
    
    def clear_cache(self):
        """Clear the cached schema graph (call when database is updated)"""
        self.load_schema_graph.cache_clear()

_loader = None

def get_database_hints_loader() -> DatabaseHintsLoader:
    """Get or create global database hints loader instance"""
    global _loader
    if _loader is None:
        _loader = DatabaseHintsLoader()
    return _loader
