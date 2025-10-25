#!/usr/bin/env python3
"""
018_Entry_Point_Structured_RAG_Graph.py
Structured RAG with NetworkX Graph for Deterministic Join Pathfinding

Implements the principle of logical determinism:
- Graph-theoretic functions (NetworkX) handle join path discovery
- LLM focuses on NL understanding and SQL generation
- Separation of concerns for production-grade semantic layers
"""

import os
import networkx as nx
from typing import List, Dict, Any, Tuple, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

class SchemaGraphManager:
    """Manages schema graph for deterministic join pathfinding"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided or set in environment")
        self.graph = nx.DiGraph()
        self._load_graph_from_database()
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def _load_graph_from_database(self):
        """Load graph structure from schema metadata tables"""
        print("📊 Loading schema graph from metadata tables...")
        
        conn = self._get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Load nodes
            cursor.execute("""
                SELECT table_name, table_type, description 
                FROM schema_nodes
            """)
            nodes = cursor.fetchall()
            
            for node in nodes:
                self.graph.add_node(
                    node['table_name'],
                    table_type=node['table_type'],
                    description=node['description']
                )
            
            # Load edges
            cursor.execute("""
                SELECT from_table, to_table, relationship_type, join_column, weight
                FROM schema_edges
            """)
            edges = cursor.fetchall()
            
            for edge in edges:
                self.graph.add_edge(
                    edge['from_table'],
                    edge['to_table'],
                    relationship=edge['relationship_type'],
                    join_column=edge['join_column'],
                    weight=edge['weight']
                )
            
            print(f"✅ Graph loaded: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            
        finally:
            cursor.close()
            conn.close()
    
    def find_join_path(self, start_table: str, end_table: str) -> Optional[List[str]]:
        """
        Find deterministic join path using NetworkX shortest path algorithm
        
        This is the LOGICAL DETERMINISM component:
        - Graph theory guarantees correct join sequence
        - No LLM inference needed for structural navigation
        """
        try:
            # Convert to undirected for bidirectional path finding
            undirected_graph = self.graph.to_undirected()
            
            path = nx.shortest_path(
                undirected_graph,
                source=start_table,
                target=end_table,
                weight='weight'
            )
            
            return path
            
        except nx.NetworkXNoPath:
            print(f"❌ No path exists between {start_table} and {end_table}")
            return None
        except nx.NodeNotFound as e:
            print(f"❌ Node not found: {e}")
            return None
    
    def get_join_sequence(self, start_table: str, end_table: str) -> Optional[Dict[str, Any]]:
        """
        Get complete join sequence with relationship metadata
        
        Returns augmented context for LLM:
        - Deterministic join path (from NetworkX)
        - Relationship types for each edge
        - Join columns for SQL generation
        """
        path = self.find_join_path(start_table, end_table)
        
        if not path:
            return None
        
        join_sequence = {
            'path': path,
            'joins': [],
            'distance': len(path) - 1
        }
        
        # Extract edge metadata for each join
        for i in range(len(path) - 1):
            from_table = path[i]
            to_table = path[i + 1]
            
            # Get edge data (handle bidirectional)
            edge_data = None
            if self.graph.has_edge(from_table, to_table):
                edge_data = self.graph[from_table][to_table]
            elif self.graph.has_edge(to_table, from_table):
                edge_data = self.graph[to_table][from_table]
                # Swap for correct direction
                from_table, to_table = to_table, from_table
            
            if edge_data:
                join_sequence['joins'].append({
                    'from': from_table,
                    'to': to_table,
                    'relationship': edge_data.get('relationship'),
                    'join_column': edge_data.get('join_column'),
                    'weight': edge_data.get('weight')
                })
        
        return join_sequence
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """Get graph statistics and structure summary"""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'nodes': list(self.graph.nodes()),
            'is_connected': nx.is_weakly_connected(self.graph),
            'density': nx.density(self.graph)
        }
    
    def visualize_path(self, path: List[str]) -> str:
        """Create visual representation of join path"""
        if not path:
            return "No path available"
        
        visualization = []
        for i in range(len(path)):
            visualization.append(path[i])
            if i < len(path) - 1:
                # Get relationship type
                edge_data = self.graph.get_edge_data(path[i], path[i+1])
                if not edge_data:
                    edge_data = self.graph.get_edge_data(path[i+1], path[i])
                
                relationship = edge_data.get('relationship', 'RELATED_TO') if edge_data else 'RELATED_TO'
                visualization.append(f" --[{relationship}]--> ")
        
        return "".join(visualization)


class StructuredRAGEngine:
    """
    Structured RAG Engine with Graph-Theoretic Determinism
    
    Implements separation of concerns:
    - NetworkX: Deterministic join path discovery (logical)
    - LLM: Natural language understanding and SQL generation (inference)
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.schema_graph = SchemaGraphManager(database_url)
    
    def process_query(self, natural_language_query: str, start_table: str, end_table: str) -> Dict[str, Any]:
        """
        Process natural language query with graph-augmented context
        
        Workflow:
        1. RETRIEVAL: Get deterministic join path from NetworkX
        2. AUGMENTATION: Provide structural context to LLM
        3. GENERATION: LLM generates SQL with guaranteed correct joins
        """
        print(f"\n🔍 Processing Query: {natural_language_query}")
        print(f"📍 From: {start_table} → To: {end_table}")
        print("-" * 70)
        
        # PHASE 1: RETRIEVAL & PRE-PROCESSING (Graph-Theoretic)
        join_sequence = self.schema_graph.get_join_sequence(start_table, end_table)
        
        if not join_sequence:
            return {
                'status': 'error',
                'message': f'No join path found between {start_table} and {end_table}'
            }
        
        # PHASE 2: AUGMENTATION (Structured Context)
        augmented_context = {
            'query': natural_language_query,
            'join_path': join_sequence['path'],
            'join_details': join_sequence['joins'],
            'path_visualization': self.schema_graph.visualize_path(join_sequence['path'])
        }
        
        print(f"✅ Deterministic Join Path Found:")
        print(f"   Path: {' → '.join(join_sequence['path'])}")
        print(f"   Visual: {augmented_context['path_visualization']}")
        print(f"   Hops: {join_sequence['distance']}")
        
        # PHASE 3: GROUNDED GENERATION (Would integrate with LLM)
        # In production: Pass augmented_context to LLM for SQL generation
        print(f"\n📋 Augmented Context for LLM:")
        print(json.dumps(augmented_context['join_details'], indent=2))
        
        return {
            'status': 'success',
            'natural_language_query': natural_language_query,
            'augmented_context': augmented_context,
            'join_sequence': join_sequence
        }


def demo_structured_rag_graph():
    """Demonstrate Structured RAG with NetworkX graph determinism"""
    print("🧪 Structured RAG with Graph-Theoretic Determinism Demo")
    print("Separation of Concerns: NetworkX (logic) + LLM (inference)")
    print("=" * 75)
    
    # Initialize Structured RAG Engine
    rag_engine = StructuredRAGEngine()
    
    # Display graph structure
    graph_summary = rag_engine.schema_graph.get_graph_summary()
    print(f"\n📊 Manufacturing Schema Graph:")
    print(f"   Nodes (Tables): {graph_summary['total_nodes']}")
    print(f"   Edges (Relationships): {graph_summary['total_edges']}")
    print(f"   Tables: {', '.join(graph_summary['nodes'])}")
    print(f"   Connected: {graph_summary['is_connected']}")
    
    # Test Cases: Multi-hop manufacturing queries
    test_queries = [
        {
            'query': 'Which suppliers are affected if CNC-001 equipment fails?',
            'start': 'equipment',
            'end': 'supplier'
        },
        {
            'query': 'What quality control measures exist for products from specific equipment?',
            'start': 'equipment',
            'end': 'quality_control'
        },
        {
            'query': 'Find maintenance logs for production lines',
            'start': 'production_line',
            'end': 'maintenance_log'
        },
        {
            'query': 'Which suppliers provide materials for products monitored in quality control?',
            'start': 'supplier',
            'end': 'quality_control'
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 75}")
        print(f"🧪 Test Case {i}")
        
        result = rag_engine.process_query(
            natural_language_query=test['query'],
            start_table=test['start'],
            end_table=test['end']
        )
        
        if result['status'] == 'success':
            print(f"✅ Success: Deterministic path found")
        else:
            print(f"❌ {result['message']}")
    
    print(f"\n{'=' * 75}")
    print("🎯 Structured RAG Implementation Complete!")
    print("📚 Key Achievements:")
    print("   ✓ Graph metadata stored in relational database")
    print("   ✓ NetworkX provides deterministic join pathfinding")
    print("   ✓ Separation of concerns: Logic (graph) vs Inference (LLM)")
    print("   ✓ Ready for Berkeley Haas capstone semantic layer")
    
    return True


if __name__ == "__main__":
    # Run the Structured RAG demonstration
    demo_structured_rag_graph()
