#!/usr/bin/env python3
"""
Lineage Graph Builder

Creates directed graph from lineage data.
- Nodes: SQL files and database tables
- Edges: "uses" relationships (file -> table)

Provides methods for:
- Finding table dependencies
- Finding common tables between files
- Generating table statistics
- Exporting for visualization

Uses SimpleDiGraph shim (no NetworkX dependency).
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import pickle

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from simple_digraph import SimpleDiGraph

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LineageGraphBuilder:
    """Build and analyze lineage graph using SimpleDiGraph."""

    def __init__(self, lineage_file: Path):
        """
        Initialize graph builder.

        Args:
            lineage_file: Path to table_lineage.json file
        """
        self.lineage_file = lineage_file
        self.graph = SimpleDiGraph()
        self.file_nodes = set()
        self.table_nodes = set()

    def load_lineage_data(self) -> Dict[str, Any]:
        """
        Load lineage data from JSON file.

        Returns:
            Lineage data dictionary
        """
        if not self.lineage_file.exists():
            logger.error(f"Lineage file not found: {self.lineage_file}")
            raise FileNotFoundError(f"Lineage file not found: {self.lineage_file}")

        with open(self.lineage_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def build_graph(self):
        """Build the lineage graph from lineage data."""
        logger.info("Building lineage graph...")

        lineage_data = self.load_lineage_data()
        files = lineage_data.get('files', [])

        for file_info in files:
            file_path = file_info.get('relative_path', file_info.get('file_path'))

            self.graph.add_node(file_path, node_type='file', name=file_info['file_name'])
            self.file_nodes.add(file_path)

            for table in file_info.get('tables', []):
                table_name = table['full_name']

                if not self.graph.has_node(table_name):
                    self.graph.add_node(
                        table_name,
                        node_type='table',
                        database=table.get('database') or '',
                        schema=table.get('schema') or '',
                        table=table.get('table') or ''
                    )
                    self.table_nodes.add(table_name)

                self.graph.add_edge(file_path, table_name, relationship='uses')

        logger.info(f"Graph built successfully!")
        logger.info(f"  File nodes: {len(self.file_nodes)}")
        logger.info(f"  Table nodes: {len(self.table_nodes)}")
        logger.info(f"  Total edges: {self.graph.number_of_edges()}")

    def find_table_dependencies(self, table_name: str) -> List[str]:
        """
        Find all files that depend on (use) a specific table.

        Args:
            table_name: Name of the table

        Returns:
            List of file paths that use this table
        """
        files = []
        for file_node in self.file_nodes:
            if table_name in self.graph._adj.get(file_node, {}):
                files.append(file_node)

        return sorted(files)

    def find_common_tables(self, file1: str, file2: str) -> List[str]:
        """
        Find tables that are used by both files.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            List of table names used by both files
        """
        if not self.graph.has_node(file1) or not self.graph.has_node(file2):
            return []

        tables1 = set(self.graph.successors(file1))
        tables2 = set(self.graph.successors(file2))

        common = tables1 & tables2
        return sorted(list(common))

    def get_table_statistics(self) -> List[Dict[str, Any]]:
        """
        Get usage statistics for all tables.

        Returns:
            List of dictionaries with table statistics:
            - table: Table name
            - usage_count: Number of files using this table
            - files: List of files using this table
        """
        stats = []

        for table in self.table_nodes:
            files = self.find_table_dependencies(table)
            stats.append({
                'table': table,
                'usage_count': len(files),
                'files': files
            })

        stats.sort(key=lambda x: x['usage_count'], reverse=True)
        return stats

    def get_file_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all files.

        Returns:
            List of dictionaries with file statistics:
            - file: File path
            - table_count: Number of tables used by this file
            - tables: List of tables used
        """
        stats = []

        for file_node in self.file_nodes:
            tables = list(self.graph.successors(file_node))
            stats.append({
                'file': file_node,
                'table_count': len(tables),
                'tables': sorted(tables)
            })

        stats.sort(key=lambda x: x['table_count'], reverse=True)
        return stats

    def export_for_visualization(self, output_dir: Path):
        """
        Export graph data for visualization.

        Args:
            output_dir: Directory for output files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting graph for visualization...")

        json_file = output_dir / "lineage_graph.json"
        graph_data = {
            "nodes": [{"id": n, **a} for n, a in self.graph.nodes(data=True)],
            "edges": [{"source": u, "target": v, **a} for u, v, a in self.graph.edges(data=True)],
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2)
        logger.info(f"  JSON: {json_file}")

        pickle_file = output_dir / "lineage_graph.gpickle"
        with open(pickle_file, 'wb') as f:
            pickle.dump(self.graph, f)
        logger.info(f"  Pickle: {pickle_file}")

        stats_file = output_dir / "graph_statistics.json"
        stats = {
            'summary': {
                'file_nodes': len(self.file_nodes),
                'table_nodes': len(self.table_nodes),
                'total_edges': self.graph.number_of_edges()
            },
            'top_tables': self.get_table_statistics()[:20],
            'top_files': self.get_file_statistics()[:20]
        }
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"  Statistics: {stats_file}")

    def print_summary(self):
        """Print summary of the graph."""
        print("\n" + "=" * 60)
        print("LINEAGE GRAPH SUMMARY")
        print("=" * 60)
        print(f"\nFile Nodes: {len(self.file_nodes)}")
        print(f"Table Nodes: {len(self.table_nodes)}")
        print(f"Total Edges: {self.graph.number_of_edges()}")

        print(f"\nTop 10 Most Used Tables:")
        print("-" * 60)
        stats = self.get_table_statistics()[:10]
        for i, stat in enumerate(stats, 1):
            print(f"{i:2d}. {stat['table']:<40} (used by {stat['usage_count']} files)")

        print(f"\nTop 10 Files with Most Table Dependencies:")
        print("-" * 60)
        file_stats = self.get_file_statistics()[:10]
        for i, stat in enumerate(file_stats, 1):
            print(f"{i:2d}. {stat['file']}")
            print(f"    Uses {stat['table_count']} tables")

        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent.parent
    lineage_file = script_dir / "reports" / "lineage" / "table_lineage.json"
    output_dir = script_dir / "reports" / "graphs"

    if not lineage_file.exists():
        logger.error(f"Lineage file not found: {lineage_file}")
        logger.error(f"   Please run extract_tables.py first to generate lineage data")
        sys.exit(1)

    logger.info(f"Starting graph builder")
    logger.info(f"Lineage file: {lineage_file}")
    logger.info(f"Output directory: {output_dir}")

    builder = LineageGraphBuilder(lineage_file)
    builder.build_graph()

    builder.export_for_visualization(output_dir)

    builder.print_summary()

    logger.info(f"\nGraph building complete!")


if __name__ == "__main__":
    main()
