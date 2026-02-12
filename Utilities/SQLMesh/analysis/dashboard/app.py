#!/usr/bin/env python3
"""
SQL Lineage Analysis Dashboard

Interactive Gradio web dashboard for exploring SQL lineage data.

Features:
- Overview with summary statistics
- Search for table dependencies
- View file details
- Browse all tables
- Identify ambiguous columns
- Real-time query analysis

Runs on port 5000 by default.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging

try:
    import gradio as gr
except ImportError:
    print("❌ Gradio not installed. Please install: pip install gradio")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ Pandas not installed. Please install: pip install pandas")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_parser import SQLParser
from graph.networkx_builder import LineageGraphBuilder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LineageDashboard:
    """Interactive dashboard for SQL lineage analysis."""
    
    def __init__(self, analysis_dir: Path):
        """
        Initialize dashboard.
        
        Args:
            analysis_dir: Path to analysis directory
        """
        self.analysis_dir = analysis_dir
        self.lineage_file = analysis_dir / "reports" / "lineage" / "table_lineage.json"
        self.column_file = analysis_dir / "reports" / "lineage" / "column_lineage.json"
        self.graph_file = analysis_dir / "reports" / "graphs" / "lineage_graph.gpickle"
        
        self.lineage_data = None
        self.column_data = None
        self.graph_builder = None
        self.parser = SQLParser(dialect="tsql")
        
        self.load_data()
    
    def load_data(self):
        """Load lineage data from files."""
        # Load table lineage
        if self.lineage_file.exists():
            with open(self.lineage_file, 'r', encoding='utf-8') as f:
                self.lineage_data = json.load(f)
            logger.info(f"✅ Loaded table lineage data")
        else:
            logger.warning(f"⚠️  Table lineage file not found: {self.lineage_file}")
        
        # Load column lineage
        if self.column_file.exists():
            with open(self.column_file, 'r', encoding='utf-8') as f:
                self.column_data = json.load(f)
            logger.info(f"✅ Loaded column lineage data")
        else:
            logger.warning(f"⚠️  Column lineage file not found: {self.column_file}")
        
        # Load graph
        if self.lineage_file.exists():
            try:
                self.graph_builder = LineageGraphBuilder(self.lineage_file)
                self.graph_builder.build_graph()
                logger.info(f"✅ Built lineage graph")
            except Exception as e:
                logger.warning(f"⚠️  Could not build graph: {e}")
    
    def refresh_data(self) -> str:
        """Refresh all data from files."""
        self.load_data()
        return "✅ Data refreshed successfully!"
    
    def get_overview_stats(self) -> Tuple[str, pd.DataFrame]:
        """
        Get overview statistics.
        
        Returns:
            Tuple of (summary_text, top_tables_dataframe)
        """
        if not self.lineage_data:
            return "❌ No lineage data available", pd.DataFrame()
        
        summary = self.lineage_data.get('summary', {})
        
        stats_text = f"""
## 📊 SQL Lineage Analysis Overview

### Summary Statistics
- **Total SQL Files**: {summary.get('total_files', 0)}
- **Successfully Parsed**: {summary.get('successful_parses', 0)}
- **Failed Parses**: {summary.get('failed_parses', 0)}
- **Unique Tables**: {summary.get('unique_tables', 0)}
- **Total Table References**: {summary.get('total_tables_referenced', 0)}
        """
        
        # Create DataFrame for top tables
        most_used = self.lineage_data.get('most_used_tables', [])[:20]
        df = pd.DataFrame(most_used)
        
        return stats_text, df
    
    def search_table(self, table_name: str) -> Tuple[str, pd.DataFrame]:
        """
        Search for files using a specific table.
        
        Args:
            table_name: Name of table to search
            
        Returns:
            Tuple of (summary_text, files_dataframe)
        """
        if not table_name:
            return "⚠️  Please enter a table name", pd.DataFrame()
        
        if not self.graph_builder:
            return "❌ Graph data not available", pd.DataFrame()
        
        # Find dependencies
        files = self.graph_builder.find_table_dependencies(table_name.upper())
        
        # Also try partial match
        if not files:
            all_tables = list(self.graph_builder.table_nodes)
            matching_tables = [t for t in all_tables if table_name.upper() in t.upper()]
            
            if matching_tables:
                # Use first matching table
                table_name = matching_tables[0]
                files = self.graph_builder.find_table_dependencies(table_name)
        
        if not files:
            return f"❌ No files found using table: {table_name}", pd.DataFrame()
        
        summary = f"## ✅ Found {len(files)} file(s) using table: {table_name}\n"
        
        # Create DataFrame
        df = pd.DataFrame({
            'File Path': files
        })
        
        return summary, df
    
    def get_file_details(self, file_path: str) -> Tuple[str, pd.DataFrame]:
        """
        Get details for a specific file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (summary_text, tables_dataframe)
        """
        if not file_path:
            return "⚠️  Please select or enter a file path", pd.DataFrame()
        
        if not self.lineage_data:
            return "❌ Lineage data not available", pd.DataFrame()
        
        # Find file in lineage data
        file_info = None
        for f in self.lineage_data.get('files', []):
            if file_path in f.get('relative_path', '') or file_path in f.get('file_path', ''):
                file_info = f
                break
        
        if not file_info:
            return f"❌ File not found: {file_path}", pd.DataFrame()
        
        tables = file_info.get('tables', [])
        summary = f"## 📄 File: {file_info['file_name']}\n\n"
        summary += f"**Path**: {file_info.get('relative_path', file_info.get('file_path'))}\n\n"
        summary += f"**Total Tables**: {len(tables)}\n"
        
        # Create DataFrame
        df = pd.DataFrame(tables)
        if not df.empty:
            df = df[['full_name', 'database', 'schema', 'table']]
        
        return summary, df
    
    def get_all_tables(self) -> pd.DataFrame:
        """
        Get all tables with usage counts.
        
        Returns:
            DataFrame with all tables
        """
        if not self.graph_builder:
            return pd.DataFrame()
        
        stats = self.graph_builder.get_table_statistics()
        df = pd.DataFrame([
            {'Table': s['table'], 'Usage Count': s['usage_count']}
            for s in stats
        ])
        
        return df
    
    def get_ambiguous_columns(self) -> Tuple[str, pd.DataFrame]:
        """
        Get files with ambiguous columns.
        
        Returns:
            Tuple of (summary_text, ambiguous_files_dataframe)
        """
        if not self.column_data:
            return "❌ Column lineage data not available", pd.DataFrame()
        
        summary_info = self.column_data.get('summary', {})
        ambiguous_files = self.column_data.get('ambiguous_files', [])[:50]
        
        summary = f"""
## ⚠️  Ambiguous Column Analysis

Files with columns lacking explicit table qualifiers.

**Total Files with Issues**: {summary_info.get('files_with_ambiguous_columns', 0)}
**Total Ambiguous Columns**: {summary_info.get('total_ambiguous_columns', 0)}
**Percentage of Files**: {summary_info.get('ambiguous_percentage', 0)}%

*Showing top 50 files*
        """
        
        df = pd.DataFrame([
            {
                'File': f['relative_path'],
                'Ambiguous Count': f['ambiguous_count'],
                'Examples': ', '.join(f['ambiguous_columns'][:5])
            }
            for f in ambiguous_files
        ])
        
        return summary, df
    
    def analyze_query(self, sql_query: str) -> Tuple[str, pd.DataFrame, str]:
        """
        Analyze a SQL query in real-time.
        
        Args:
            sql_query: SQL query to analyze
            
        Returns:
            Tuple of (tables_text, tables_df, complexity_text)
        """
        if not sql_query.strip():
            return "⚠️  Please enter a SQL query", pd.DataFrame(), ""
        
        # Extract tables
        tables = self.parser.extract_tables_from_query(sql_query)
        
        if tables:
            tables_text = f"## 📋 Tables Found: {len(tables)}\n"
            tables_df = pd.DataFrame(tables)
        else:
            tables_text = "❌ No tables found in query"
            tables_df = pd.DataFrame()
        
        # Analyze complexity
        complexity = self.parser.analyze_query_complexity(sql_query)
        
        complexity_text = f"""
## 📊 Query Complexity Analysis

- **Complexity Score**: {complexity['complexity_score']}/100
- **Tables**: {complexity['num_tables']}
- **Joins**: {complexity['num_joins']}
- **Subqueries**: {complexity['num_subqueries']}
- **CTEs**: {complexity['num_ctes']}
- **Has Aggregation**: {'Yes' if complexity['has_aggregation'] else 'No'}
- **Has Window Functions**: {'Yes' if complexity['has_window_functions'] else 'No'}
        """
        
        return tables_text, tables_df, complexity_text
    
    def build_interface(self) -> gr.Blocks:
        """
        Build Gradio interface.
        
        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(title="SQL Lineage Analysis Dashboard") as demo:
            gr.Markdown("# 📊 SQL Lineage Analysis Dashboard")
            gr.Markdown("Explore SQL file dependencies, table usage, and query complexity")
            
            with gr.Tabs():
                # Tab 1: Overview
                with gr.Tab("📊 Overview"):
                    gr.Markdown("## Summary Statistics")
                    
                    refresh_btn = gr.Button("🔄 Refresh Data", variant="primary")
                    refresh_status = gr.Textbox(label="Status", interactive=False)
                    
                    overview_text = gr.Markdown()
                    overview_table = gr.Dataframe(label="Top 20 Most Used Tables")
                    
                    # Load initial data
                    stats_text, stats_df = self.get_overview_stats()
                    overview_text.value = stats_text
                    overview_table.value = stats_df
                    
                    refresh_btn.click(
                        fn=self.refresh_data,
                        outputs=refresh_status
                    ).then(
                        fn=self.get_overview_stats,
                        outputs=[overview_text, overview_table]
                    )
                
                # Tab 2: Search Tables
                with gr.Tab("🔍 Search Tables"):
                    gr.Markdown("## Find Files Using a Table")
                    gr.Markdown("Search for a table name to see which SQL files reference it")
                    
                    table_search = gr.Textbox(
                        label="Table Name",
                        placeholder="e.g., WORK_ORDER, PART, LIVE.dbo.CUSTOMER_ORDER"
                    )
                    search_btn = gr.Button("Search", variant="primary")
                    
                    search_result_text = gr.Markdown()
                    search_result_table = gr.Dataframe(label="Files Using This Table")
                    
                    search_btn.click(
                        fn=self.search_table,
                        inputs=table_search,
                        outputs=[search_result_text, search_result_table]
                    )
                
                # Tab 3: File Details
                with gr.Tab("📄 File Details"):
                    gr.Markdown("## View Tables Used by a File")
                    
                    file_search = gr.Textbox(
                        label="File Path",
                        placeholder="e.g., AMLA/AMLA_Hours.sql"
                    )
                    file_btn = gr.Button("Get Details", variant="primary")
                    
                    file_result_text = gr.Markdown()
                    file_result_table = gr.Dataframe(label="Tables Used")
                    
                    file_btn.click(
                        fn=self.get_file_details,
                        inputs=file_search,
                        outputs=[file_result_text, file_result_table]
                    )
                
                # Tab 4: All Tables
                with gr.Tab("📋 All Tables"):
                    gr.Markdown("## Complete Table Listing")
                    gr.Markdown("Sortable list of all tables with usage counts")
                    
                    all_tables_btn = gr.Button("Load All Tables", variant="primary")
                    all_tables_df = gr.Dataframe(
                        label="All Tables",
                        interactive=False
                    )
                    
                    # Load initial data
                    all_tables_df.value = self.get_all_tables()
                    
                    all_tables_btn.click(
                        fn=self.get_all_tables,
                        outputs=all_tables_df
                    )
                
                # Tab 5: Ambiguous Columns
                with gr.Tab("⚠️  Ambiguous Columns"):
                    gr.Markdown("## Files with Ambiguous Columns")
                    gr.Markdown("Columns that lack explicit table qualifiers may cause issues")
                    
                    ambiguous_btn = gr.Button("Load Ambiguous Columns", variant="primary")
                    ambiguous_text = gr.Markdown()
                    ambiguous_df = gr.Dataframe(label="Files with Ambiguous Columns")
                    
                    # Load initial data
                    amb_text, amb_df = self.get_ambiguous_columns()
                    ambiguous_text.value = amb_text
                    ambiguous_df.value = amb_df
                    
                    ambiguous_btn.click(
                        fn=self.get_ambiguous_columns,
                        outputs=[ambiguous_text, ambiguous_df]
                    )
                
                # Tab 6: Query Analyzer
                with gr.Tab("🔬 Query Analyzer"):
                    gr.Markdown("## Analyze SQL Query")
                    gr.Markdown("Paste a SQL query to analyze its dependencies and complexity")
                    
                    query_input = gr.Textbox(
                        label="SQL Query",
                        placeholder="Paste your SQL query here...",
                        lines=10
                    )
                    analyze_btn = gr.Button("Analyze Query", variant="primary")
                    
                    with gr.Row():
                        with gr.Column():
                            query_tables_text = gr.Markdown()
                            query_tables_df = gr.Dataframe(label="Tables Used")
                        
                        with gr.Column():
                            query_complexity_text = gr.Markdown()
                    
                    analyze_btn.click(
                        fn=self.analyze_query,
                        inputs=query_input,
                        outputs=[query_tables_text, query_tables_df, query_complexity_text]
                    )
            
            gr.Markdown("---")
            gr.Markdown("*SQL Lineage Analysis Dashboard - Read-only static analysis*")
        
        return demo
    
    def launch(self, port: int = 5000, share: bool = False):
        """
        Launch the dashboard.
        
        Args:
            port: Port number (default: 5000)
            share: Create public share link (default: False)
        """
        logger.info(f"🚀 Launching dashboard on port {port}")
        demo = self.build_interface()
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=share
        )


def main():
    """Main entry point."""
    # Determine paths
    script_dir = Path(__file__).parent.parent
    
    logger.info("🚀 Starting SQL Lineage Analysis Dashboard")
    logger.info(f"📁 Analysis directory: {script_dir}")
    
    # Create and launch dashboard
    dashboard = LineageDashboard(script_dir)
    dashboard.launch(port=5000, share=False)


if __name__ == "__main__":
    main()
