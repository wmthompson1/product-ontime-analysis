#!/usr/bin/env python3
"""
Importable module version of Entry Point 018: Structured RAG Schema Graph

Provides SchemaGraphManager for building database schema graphs
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import networkx as nx
from typing import List, Dict, Any, Tuple, Optional


class SchemaGraphManager:
    """
    Manages database schema as a NetworkX directed graph
    Enables deterministic join pathfinding for RAG applications
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided or set in environment")
    
    def build_graph_from_database(self) -> nx.DiGraph:
        """
        Build schema graph from database metadata tables
        
        Returns:
            NetworkX DiGraph with schema nodes and edges
        """
        print("🔨 Building schema graph from database...")
        
        conn = psycopg2.connect(self.database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        G = nx.DiGraph()
        
        try:
            cursor.execute("SELECT table_name, table_type, description FROM schema_nodes")
            nodes = cursor.fetchall()
            
            for node in nodes:
                G.add_node(
                    node['table_name'],
                    table_type=node['table_type'],
                    description=node['description']
                )
            
            cursor.execute("""
                SELECT from_table, to_table, relationship_type, join_column, weight
                FROM schema_edges
            """)
            edges = cursor.fetchall()
            
            for edge in edges:
                G.add_edge(
                    edge['from_table'],
                    edge['to_table'],
                    relationship=edge['relationship_type'],
                    join_column=edge['join_column'],
                    weight=edge['weight']
                )
            
            print(f"✅ Schema graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            
        finally:
            cursor.close()
            conn.close()
        
        return G
    
    def find_join_path(self, graph: nx.DiGraph, source: str, target: str) -> Optional[List[str]]:
        """
        Find shortest join path between two tables
        
        Args:
            graph: Schema graph
            source: Source table name
            target: Target table name
        
        Returns:
            List of table names in join path, or None if no path exists
        """
        try:
            graph_undirected = graph.to_undirected()
            path = nx.shortest_path(graph_undirected, source=source, target=target)
            return path
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None
