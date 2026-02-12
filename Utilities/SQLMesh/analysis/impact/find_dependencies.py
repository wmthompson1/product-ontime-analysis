#!/usr/bin/env python3
"""
Find Table Dependencies

Command-line tool to find all SQL files that use a specific table.

Usage:
    python find_dependencies.py --table TABLE_NAME
    python find_dependencies.py --table WORK_ORDER
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class DependencyFinder:
    """Find dependencies for tables in SQL files."""
    
    def __init__(self, lineage_file: Path):
        """
        Initialize dependency finder.
        
        Args:
            lineage_file: Path to table_lineage.json file
        """
        self.lineage_file = lineage_file
        self.lineage_data = None
    
    def load_lineage_data(self):
        """Load lineage data from JSON file."""
        if not self.lineage_file.exists():
            logger.error(f"❌ Lineage file not found: {self.lineage_file}")
            logger.error(f"   Please run extract_tables.py first to generate lineage data")
            sys.exit(1)
        
        with open(self.lineage_file, 'r', encoding='utf-8') as f:
            self.lineage_data = json.load(f)
        
        logger.info(f"✅ Loaded lineage data from: {self.lineage_file}")
    
    def find_table_usage(self, table_name: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Find all files that use a specific table.
        
        Args:
            table_name: Name of the table to search for
            exact_match: If True, require exact match; if False, partial match
            
        Returns:
            List of dictionaries with file information and matching tables
        """
        if not self.lineage_data:
            self.load_lineage_data()
        
        matching_files = []
        search_term = table_name.upper()
        
        for file_info in self.lineage_data.get('files', []):
            matching_tables = []
            
            for table in file_info.get('tables', []):
                table_full_name = table['full_name'].upper()
                table_short_name = table['table'].upper() if table.get('table') else ''
                
                if exact_match:
                    if table_full_name == search_term or table_short_name == search_term:
                        matching_tables.append(table['full_name'])
                else:
                    if search_term in table_full_name or search_term in table_short_name:
                        matching_tables.append(table['full_name'])
            
            if matching_tables:
                matching_files.append({
                    'file_path': file_info.get('relative_path', file_info.get('file_path')),
                    'file_name': file_info['file_name'],
                    'matching_tables': matching_tables,
                    'total_tables': len(file_info.get('tables', []))
                })
        
        return matching_files
    
    def print_results(self, table_name: str, results: List[Dict[str, Any]]):
        """
        Print search results.
        
        Args:
            table_name: Name of the table searched
            results: List of matching files
        """
        print("\n" + "=" * 70)
        print(f"🔍 TABLE DEPENDENCY SEARCH: {table_name}")
        print("=" * 70)
        
        if not results:
            print(f"\n❌ No files found that use table: {table_name}")
            print("\nTips:")
            print("  - Try a partial match (default behavior)")
            print("  - Check spelling and case")
            print("  - Try searching for just the table name without schema/database")
        else:
            print(f"\n✅ Found {len(results)} file(s) that use this table\n")
            
            for i, file_info in enumerate(results, 1):
                print(f"{i}. {file_info['file_path']}")
                print(f"   Matching tables: {', '.join(file_info['matching_tables'])}")
                print(f"   Total tables in file: {file_info['total_tables']}")
                print()
        
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Find SQL files that use a specific table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_dependencies.py --table WORK_ORDER
  python find_dependencies.py --table LIVE.dbo.PART
  python find_dependencies.py --table CUSTOMER_ORDER --exact
        """
    )
    parser.add_argument(
        '--table', '-t',
        required=True,
        help='Table name to search for'
    )
    parser.add_argument(
        '--exact', '-e',
        action='store_true',
        help='Require exact match (default: partial match)'
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).parent.parent
    lineage_file = script_dir / "reports" / "lineage" / "table_lineage.json"
    
    # Create finder and search
    finder = DependencyFinder(lineage_file)
    results = finder.find_table_usage(args.table, exact_match=args.exact)
    
    # Print results
    finder.print_results(args.table, results)
    
    # Exit with appropriate code
    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
