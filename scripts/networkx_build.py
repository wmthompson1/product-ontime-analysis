#!/usr/bin/env python3
"""
NetworkX Graph Builder (Python)

This script builds a supply chain graph using NetworkX from the product on-time analysis database.
It provides an alternative to the Node.js graphology builder with Python-native graph analytics.

Usage:
    python scripts/networkx_build.py [options]

Options:
    --output <file>     Output file path (default: graph_networkx.json)
    --format <type>     Output format: json, gexf, graphml, pickle (default: json)
    --analyze           Run graph analytics (centrality, communities, paths)
    --visualize         Generate a visualization (requires matplotlib)
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any

try:
    import psycopg2
    import networkx as nx
    print("✅ NetworkX and psycopg2 loaded successfully")
except ImportError as e:
    print(f"❌ Missing required library: {e}")
    print("Install with: pip install networkx psycopg2-binary")
    sys.exit(1)

# Optional: matplotlib for visualization
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Database configuration
DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('PGDATABASE', 'product_ontime'),
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', 'postgres'),
}


def build_supply_chain_graph(cursor) -> nx.DiGraph:
    """
    Build a directed graph representing the supply chain.
    
    Returns:
        NetworkX DiGraph with suppliers, parts, and products as nodes
    """
    print("\n🔨 Building supply chain graph...")
    
    graph = nx.DiGraph()
    
    # Add supplier nodes
    print("  📦 Adding supplier nodes...")
    cursor.execute("""
        SELECT supplier_id, supplier_name, supplier_code, country
        FROM suppliers
        ORDER BY supplier_id
    """)
    suppliers = cursor.fetchall()
    
    for supplier in suppliers:
        node_id = f"supplier_{supplier[0]}"
        graph.add_node(node_id, 
                      type='supplier',
                      name=supplier[1],
                      code=supplier[2],
                      country=supplier[3],
                      label=supplier[1])
    print(f"  ✅ Added {len(suppliers)} supplier nodes")
    
    # Add part nodes
    print("  🔩 Adding part nodes...")
    cursor.execute("""
        SELECT p.part_id, p.part_number, p.part_name, p.supplier_id, p.unit_cost, p.lead_time_days
        FROM parts p
        ORDER BY p.part_id
    """)
    parts = cursor.fetchall()
    
    for part in parts:
        node_id = f"part_{part[0]}"
        graph.add_node(node_id,
                      type='part',
                      number=part[1],
                      name=part[2],
                      cost=float(part[4]) if part[4] else None,
                      lead_time=part[5],
                      label=part[2])
        
        # Add edge from supplier to part
        if part[3]:
            supplier_id = f"supplier_{part[3]}"
            graph.add_edge(supplier_id, node_id,
                          type='supplies',
                          cost=float(part[4]) if part[4] else None,
                          lead_time=part[5])
    print(f"  ✅ Added {len(parts)} part nodes")
    
    # Add product nodes
    print("  📦 Adding product nodes...")
    cursor.execute("""
        SELECT product_id, product_code, product_name, product_family, target_cycle_time_hours
        FROM products
        ORDER BY product_id
    """)
    products = cursor.fetchall()
    
    for product in products:
        node_id = f"product_{product[0]}"
        graph.add_node(node_id,
                      type='product',
                      code=product[1],
                      name=product[2],
                      family=product[3],
                      cycle_time=product[4],
                      label=product[2])
    print(f"  ✅ Added {len(products)} product nodes")
    
    # Add assembly edges (part -> product)
    print("  🔗 Adding assembly relationships...")
    cursor.execute("""
        SELECT product_id, part_id, quantity_required
        FROM assemblies
        ORDER BY product_id, part_id
    """)
    assemblies = cursor.fetchall()
    
    for assembly in assemblies:
        part_id = f"part_{assembly[1]}"
        product_id = f"product_{assembly[0]}"
        graph.add_edge(part_id, product_id,
                      type='used_in',
                      quantity=assembly[2])
    print(f"  ✅ Added {len(assemblies)} assembly relationships")
    
    return graph


def analyze_graph(graph: nx.DiGraph) -> Dict[str, Any]:
    """
    Perform graph analytics and return metrics.
    """
    print("\n📊 Graph Analysis:")
    print(f"  Nodes: {graph.number_of_nodes()}")
    print(f"  Edges: {graph.number_of_edges()}")
    
    if graph.number_of_nodes() > 1:
        density = nx.density(graph)
        print(f"  Density: {density:.4f}")
    
    # Count by node type
    node_types = {}
    for node, attrs in graph.nodes(data=True):
        node_type = attrs.get('type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("\n  Node types:")
    for node_type, count in node_types.items():
        print(f"    {node_type}: {count}")
    
    # Calculate centrality metrics
    print("\n  🎯 Calculating centrality metrics...")
    try:
        degree_centrality = nx.degree_centrality(graph)
        
        # Find top nodes by degree centrality
        top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("  Top 5 most connected nodes:")
        for node_id, centrality_score in top_nodes:
            attrs = graph.nodes[node_id]
            print(f"    {attrs.get('label', node_id)} ({attrs.get('type', 'unknown')}): {centrality_score:.4f}")
        
        # Calculate betweenness centrality for critical supply chain points
        print("\n  🎯 Calculating betweenness centrality...")
        betweenness = nx.betweenness_centrality(graph)
        top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
        
        print("  Top 5 critical supply chain nodes (betweenness):")
        for node_id, betweenness_score in top_betweenness:
            if betweenness_score > 0:
                attrs = graph.nodes[node_id]
                print(f"    {attrs.get('label', node_id)} ({attrs.get('type', 'unknown')}): {betweenness_score:.4f}")
        
    except Exception as e:
        print(f"  ⚠️  Centrality calculation error: {e}")
    
    return {
        'nodes': graph.number_of_nodes(),
        'edges': graph.number_of_edges(),
        'density': nx.density(graph) if graph.number_of_nodes() > 1 else 0,
        'node_types': node_types
    }


def export_to_json(graph: nx.DiGraph) -> str:
    """
    Export graph to JSON format.
    """
    data = {
        'nodes': [],
        'edges': []
    }
    
    # Export nodes
    for node_id, attrs in graph.nodes(data=True):
        node_data = {'id': node_id}
        node_data.update(attrs)
        data['nodes'].append(node_data)
    
    # Export edges
    for source, target, attrs in graph.edges(data=True):
        edge_data = {
            'source': source,
            'target': target
        }
        edge_data.update(attrs)
        data['edges'].append(edge_data)
    
    return json.dumps(data, indent=2)


def visualize_graph(graph: nx.DiGraph, output_file: str = 'graph_visualization.png'):
    """
    Create a visualization of the graph (requires matplotlib).
    """
    if not MATPLOTLIB_AVAILABLE:
        print("⚠️  Matplotlib not installed. Skipping visualization.")
        print("    Install with: pip install matplotlib")
        return
    
    print(f"\n📊 Creating visualization...")
    
    # Create figure
    plt.figure(figsize=(16, 12))
    
    # Use hierarchical layout
    pos = nx.spring_layout(graph, k=2, iterations=50)
    
    # Color nodes by type
    node_colors = []
    for node in graph.nodes():
        node_type = graph.nodes[node].get('type', 'unknown')
        if node_type == 'supplier':
            node_colors.append('#3498db')  # Blue
        elif node_type == 'part':
            node_colors.append('#2ecc71')  # Green
        elif node_type == 'product':
            node_colors.append('#e74c3c')  # Red
        else:
            node_colors.append('#95a5a6')  # Gray
    
    # Draw graph
    nx.draw(graph, pos,
           node_color=node_colors,
           node_size=800,
           with_labels=False,
           arrows=True,
           arrowsize=10,
           edge_color='#7f8c8d',
           alpha=0.7)
    
    # Add legend
    legend_elements = [
        Patch(facecolor='#3498db', label='Supplier'),
        Patch(facecolor='#2ecc71', label='Part'),
        Patch(facecolor='#e74c3c', label='Product')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.title('Supply Chain Graph', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Build supply chain graph using NetworkX')
    parser.add_argument('--output', default='graph_networkx.json', help='Output file path')
    parser.add_argument('--format', default='json', choices=['json', 'gexf', 'graphml', 'pickle'],
                       help='Output format')
    parser.add_argument('--analyze', action='store_true', help='Run graph analytics')
    parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    
    args = parser.parse_args()
    
    print('🚀 Supply Chain Graph Builder (NetworkX)\n')
    print('Database configuration:')
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Port: {DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    
    try:
        # Connect to database
        print('\n🔌 Connecting to database...')
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print('✅ Connected to database')
        
        # Build graph
        graph = build_supply_chain_graph(cursor)
        
        # Analyze if requested
        if args.analyze:
            metrics = analyze_graph(graph)
        
        # Export graph
        print(f"\n💾 Exporting graph to {args.output}...")
        
        if args.format == 'json':
            graph_data = export_to_json(graph)
            with open(args.output, 'w') as f:
                f.write(graph_data)
        elif args.format == 'gexf':
            nx.write_gexf(graph, args.output)
        elif args.format == 'graphml':
            nx.write_graphml(graph, args.output)
        elif args.format == 'pickle':
            nx.write_gpickle(graph, args.output)
        
        print(f"✅ Graph exported successfully")
        print(f"   File: {os.path.abspath(args.output)}")
        
        # Visualize if requested
        if args.visualize:
            viz_file = args.output.replace('.json', '.png').replace('.gexf', '.png')
            visualize_graph(graph, viz_file)
        
        print('\n✨ Graph building completed successfully!')
        
    except Exception as e:
        print(f'\n❌ Error: {e}')
        if os.getenv('DEBUG', '').lower() in ('true', '1', 'yes'):
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print('🔌 Database connection closed')


if __name__ == '__main__':
    main()
