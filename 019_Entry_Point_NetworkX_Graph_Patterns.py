#!/usr/bin/env python3
"""
019_Entry_Point_NetworkX_Graph_Patterns.py
NetworkX Graph Loading and Analysis Patterns

Based on "Network Science with Python and NetworkX Quick Start Guide" by Edward L. Platt
Published by Packt Publishing (2019)
GitHub: https://github.com/PacktPublishing/Network-Science-with-Python-and-NetworkX-Quick-Start-Guide

Demonstrates fundamental NetworkX patterns applied to manufacturing intelligence:
- Graph construction (nodes, edges, attributes)
- Graph types (undirected, directed, weighted)
- Network analysis (centrality measures, paths, communities)
- Integration with Entry Point 018 Structured RAG graph metadata
"""

import networkx as nx
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
import json

class ManufacturingNetworkBuilder:
    """
    Build manufacturing intelligence networks using Edward Platt's NetworkX patterns
    
    Patterns demonstrated:
    - Simple graphs (undirected relationships)
    - Directed graphs (supplier chains, production flows)
    - Weighted graphs (distance, cost, time metrics)
    - Multigraphs (multiple relationship types between entities)
    """
    
    def __init__(self):
        self.graphs: Dict[str, nx.Graph] = {}
    
    def create_simple_manufacturing_network(self) -> nx.Graph:
        """
        Pattern 1: Simple Undirected Graph
        From Platt Chapter 2: Creating and Manipulating Networks
        
        Manufacturing context: Equipment collaboration network
        """
        print("📊 Pattern 1: Simple Undirected Graph (Equipment Collaboration)")
        
        G = nx.Graph()
        
        # Add nodes with attributes (Platt pattern)
        equipment_nodes = [
            ("CNC-001", {"type": "machining", "capacity": 100, "dept": "fabrication"}),
            ("PRESS-002", {"type": "forming", "capacity": 200, "dept": "assembly"}),
            ("ROBOT-003", {"type": "automation", "capacity": 150, "dept": "assembly"}),
            ("LINE-A", {"type": "assembly", "capacity": 300, "dept": "assembly"}),
            ("QC-STATION", {"type": "inspection", "capacity": 50, "dept": "quality"})
        ]
        
        G.add_nodes_from(equipment_nodes)
        
        # Add edges (equipment that work together)
        collaboration_edges = [
            ("CNC-001", "PRESS-002"),
            ("PRESS-002", "ROBOT-003"),
            ("ROBOT-003", "LINE-A"),
            ("LINE-A", "QC-STATION"),
            ("CNC-001", "QC-STATION")
        ]
        
        G.add_edges_from(collaboration_edges)
        
        print(f"   Nodes: {G.number_of_nodes()}")
        print(f"   Edges: {G.number_of_edges()}")
        print(f"   Density: {nx.density(G):.3f}")
        
        return G
    
    def create_directed_supply_chain(self) -> nx.DiGraph:
        """
        Pattern 2: Directed Graph
        From Platt Chapter 3: Directed Networks and Multigraphs
        
        Manufacturing context: Supply chain flow
        """
        print("\n📊 Pattern 2: Directed Graph (Supply Chain Flow)")
        
        G = nx.DiGraph()
        
        # Supply chain nodes
        nodes = [
            ("RAW-MATERIALS", {"level": 0, "lead_time": 0}),
            ("SUPPLIER-A", {"level": 1, "lead_time": 5}),
            ("SUPPLIER-B", {"level": 1, "lead_time": 7}),
            ("MANUFACTURER", {"level": 2, "lead_time": 10}),
            ("DISTRIBUTOR", {"level": 3, "lead_time": 3}),
            ("CUSTOMER", {"level": 4, "lead_time": 0})
        ]
        
        G.add_nodes_from(nodes)
        
        # Directed edges (material flow)
        flow_edges = [
            ("RAW-MATERIALS", "SUPPLIER-A"),
            ("RAW-MATERIALS", "SUPPLIER-B"),
            ("SUPPLIER-A", "MANUFACTURER"),
            ("SUPPLIER-B", "MANUFACTURER"),
            ("MANUFACTURER", "DISTRIBUTOR"),
            ("DISTRIBUTOR", "CUSTOMER")
        ]
        
        G.add_edges_from(flow_edges)
        
        print(f"   Nodes: {G.number_of_nodes()}")
        print(f"   Edges: {G.number_of_edges()}")
        print(f"   Is DAG: {nx.is_directed_acyclic_graph(G)}")
        
        return G
    
    def create_weighted_dependency_network(self) -> nx.Graph:
        """
        Pattern 3: Weighted Graph
        From Platt Chapter 4: Visualizing Networks
        
        Manufacturing context: Dependency strength between processes
        """
        print("\n📊 Pattern 3: Weighted Graph (Process Dependencies)")
        
        G = nx.Graph()
        
        # Process nodes
        processes = ["DESIGN", "PROCUREMENT", "FABRICATION", "ASSEMBLY", "TESTING", "SHIPPING"]
        G.add_nodes_from(processes)
        
        # Weighted edges (dependency strength 1-10)
        weighted_edges = [
            ("DESIGN", "PROCUREMENT", {"weight": 8}),
            ("DESIGN", "FABRICATION", {"weight": 10}),
            ("PROCUREMENT", "FABRICATION", {"weight": 9}),
            ("FABRICATION", "ASSEMBLY", {"weight": 10}),
            ("ASSEMBLY", "TESTING", {"weight": 9}),
            ("TESTING", "SHIPPING", {"weight": 7}),
            ("PROCUREMENT", "ASSEMBLY", {"weight": 5})
        ]
        
        G.add_edges_from(weighted_edges)
        
        print(f"   Nodes: {G.number_of_nodes()}")
        print(f"   Edges: {G.number_of_edges()}")
        print(f"   Total weight: {sum(d['weight'] for u, v, d in G.edges(data=True))}")
        
        return G
    
    def load_from_ARANGO_metadata(self, ARANGO_url: Optional[str] = None) -> nx.DiGraph:
        """
        Pattern 4: Loading Graph from Database
        Integration with Entry Point 018 schema metadata
        
        Demonstrates loading graph structure from relational database
        """
        print("\n📊 Pattern 4: Load from Database (Schema Metadata)")
        
        db_url = ARANGO_url or os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL must be provided or set in environment")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        G = nx.DiGraph()
        
        try:
            # Load nodes from schema_nodes table
            cursor.execute("SELECT table_name, table_type, description FROM schema_nodes")
            nodes = cursor.fetchall()
            
            for node in nodes:
                G.add_node(
                    node['table_name'],
                    table_type=node['table_type'],
                    description=node['description']
                )
            
            # Load edges from schema_edges table
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
            
            print(f"   Nodes: {G.number_of_nodes()}")
            print(f"   Edges: {G.number_of_edges()}")
            print(f"   Loaded from: schema_nodes, schema_edges tables")
            
        finally:
            cursor.close()
            conn.close()
        
        return G


class NetworkAnalyzer:
    """
    Network analysis patterns from Edward Platt's book
    Chapters 5-8: Centrality, Communities, Paths, Resilience
    """
    
    @staticmethod
    def analyze_centrality(G: nx.Graph, graph_name: str = "Graph") -> Dict[str, Any]:
        """
        Pattern: Centrality Analysis
        From Platt Chapter 5: Finding Important Nodes
        
        Key centrality measures:
        - Degree: Number of connections
        - Betweenness: Nodes on shortest paths between others
        - Closeness: Average distance to all other nodes
        - Eigenvector: Influence based on connected nodes' importance
        """
        print(f"\n🔍 Centrality Analysis: {graph_name}")
        
        results = {}
        
        # Degree centrality
        degree_cent = nx.degree_centrality(G)
        top_degree = max(degree_cent.items(), key=lambda x: x[1])
        results['degree_centrality'] = {
            'top_node': top_degree[0],
            'score': top_degree[1],
            'measure': 'Most connected node'
        }
        print(f"   Degree Centrality: {top_degree[0]} ({top_degree[1]:.3f})")
        
        # Betweenness centrality (for connected graphs)
        if nx.is_connected(G.to_undirected() if G.is_directed() else G):
            betweenness_cent = nx.betweenness_centrality(G)
            top_betweenness = max(betweenness_cent.items(), key=lambda x: x[1])
            results['betweenness_centrality'] = {
                'top_node': top_betweenness[0],
                'score': top_betweenness[1],
                'measure': 'Most critical bridge node'
            }
            print(f"   Betweenness Centrality: {top_betweenness[0]} ({top_betweenness[1]:.3f})")
        
        # Closeness centrality
        try:
            closeness_cent = nx.closeness_centrality(G)
            top_closeness = max(closeness_cent.items(), key=lambda x: x[1])
            results['closeness_centrality'] = {
                'top_node': top_closeness[0],
                'score': top_closeness[1],
                'measure': 'Most central node (shortest paths)'
            }
            print(f"   Closeness Centrality: {top_closeness[0]} ({top_closeness[1]:.3f})")
        except:
            print(f"   Closeness Centrality: Not applicable (disconnected graph)")
        
        return results
    
    @staticmethod
    def find_shortest_paths(G: nx.Graph, source: str, target: str) -> Optional[List[str]]:
        """
        Pattern: Shortest Path Finding
        From Platt Chapter 6: Paths and Routing
        
        Critical for Entry Point 018's deterministic join pathfinding
        """
        print(f"\n🛣️ Shortest Path: {source} → {target}")
        
        try:
            # Convert to undirected for pathfinding if needed
            graph_for_path = G.to_undirected() if G.is_directed() else G
            
            path = nx.shortest_path(graph_for_path, source=source, target=target)
            path_length = len(path) - 1
            
            print(f"   Path: {' → '.join(path)}")
            print(f"   Hops: {path_length}")
            
            return path
            
        except nx.NetworkXNoPath:
            print(f"   ❌ No path exists")
            return None
        except nx.NodeNotFound as e:
            print(f"   ❌ Node not found: {e}")
            return None
    
    @staticmethod
    def analyze_communities(G: nx.Graph) -> Dict[str, Any]:
        """
        Pattern: Community Detection
        From Platt Chapter 7: Finding Communities
        
        Manufacturing context: Identify equipment clusters or process groups
        """
        print(f"\n👥 Community Detection")
        
        # Convert to undirected for community detection
        G_undirected = G.to_undirected() if G.is_directed() else G
        
        # Use greedy modularity communities
        communities = list(nx.community.greedy_modularity_communities(G_undirected))
        
        results = {
            'num_communities': len(communities),
            'communities': []
        }
        
        for i, community in enumerate(communities, 1):
            community_list = list(community)
            results['communities'].append({
                'id': i,
                'size': len(community_list),
                'members': community_list
            })
            print(f"   Community {i}: {len(community_list)} nodes - {', '.join(community_list[:3])}{'...' if len(community_list) > 3 else ''}")
        
        return results
    
    @staticmethod
    def measure_graph_properties(G: nx.Graph) -> Dict[str, Any]:
        """
        Pattern: Graph-level Metrics
        From Platt Chapter 8: Network Properties
        """
        print(f"\n📐 Graph Properties")
        
        properties = {
            'nodes': G.number_of_nodes(),
            'edges': G.number_of_edges(),
            'density': nx.density(G),
            'is_directed': G.is_directed()
        }
        
        # Check connectivity
        if G.is_directed():
            properties['is_weakly_connected'] = nx.is_weakly_connected(G)
            properties['is_strongly_connected'] = nx.is_strongly_connected(G)
        else:
            properties['is_connected'] = nx.is_connected(G)
        
        # Average clustering (for undirected graphs)
        if not G.is_directed():
            properties['avg_clustering'] = nx.average_clustering(G)
        
        for key, value in properties.items():
            print(f"   {key}: {value}")
        
        return properties


def demo_networkx_patterns():
    """
    Comprehensive demonstration of NetworkX patterns from Edward Platt's book
    Applied to manufacturing intelligence context
    """
    print("🧪 NetworkX Graph Patterns Demo")
    print("Based on: 'Network Science with Python and NetworkX Quick Start Guide'")
    print("By Edward L. Platt (Packt Publishing, 2019)")
    print("=" * 75)
    
    builder = ManufacturingNetworkBuilder()
    analyzer = NetworkAnalyzer()
    
    # Pattern 1: Simple Graph
    simple_graph = builder.create_simple_manufacturing_network()
    analyzer.measure_graph_properties(simple_graph)
    analyzer.analyze_centrality(simple_graph, "Equipment Collaboration")
    analyzer.analyze_communities(simple_graph)
    
    # Pattern 2: Directed Graph
    directed_graph = builder.create_directed_supply_chain()
    analyzer.measure_graph_properties(directed_graph)
    analyzer.analyze_centrality(directed_graph, "Supply Chain")
    analyzer.find_shortest_paths(directed_graph, "RAW-MATERIALS", "CUSTOMER")
    
    # Pattern 3: Weighted Graph
    weighted_graph = builder.create_weighted_dependency_network()
    analyzer.measure_graph_properties(weighted_graph)
    analyzer.find_shortest_paths(weighted_graph, "DESIGN", "SHIPPING")
    
    # Pattern 4: Load from Database (Entry Point 018 integration)
    try:
        db_graph = builder.load_from_ARANGO_metadata()
        analyzer.measure_graph_properties(db_graph)
        analyzer.analyze_centrality(db_graph, "Database Schema")
        
        # Demonstrate shortest path (same as Entry Point 018)
        analyzer.find_shortest_paths(db_graph, "equipment", "supplier")
        
    except Exception as e:
        print(f"\n⚠️  Database graph loading skipped: {e}")
    
    print(f"\n{'=' * 75}")
    print("🎯 NetworkX Patterns Successfully Demonstrated!")
    print("📚 Key Learnings:")
    print("   ✓ Graph construction (nodes, edges, attributes)")
    print("   ✓ Graph types (undirected, directed, weighted)")
    print("   ✓ Centrality analysis (degree, betweenness, closeness)")
    print("   ✓ Shortest path algorithms")
    print("   ✓ Community detection")
    print("   ✓ Graph properties and metrics")
    print("   ✓ Database integration (Entry Point 018)")
    print("\n📖 Reference: Edward L. Platt - Network Science with Python and NetworkX")
    print("🔗 GitHub: PacktPublishing/Network-Science-with-Python-and-NetworkX-Quick-Start-Guide")
    
    return True


if __name__ == "__main__":
    # Run the NetworkX patterns demonstration
    demo_networkx_patterns()
