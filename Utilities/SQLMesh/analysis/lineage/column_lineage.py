#!/usr/bin/env python3
"""
Column Lineage Extraction

Extracts column-level lineage from SQL files.
Detects ambiguous columns (columns without explicit table qualifiers).
Generates report of problematic queries.

NO SQL EXECUTION - Only static analysis using sqlglot.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_parser import SQLParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ColumnLineageExtractor:
    """Extract column-level lineage from SQL files."""
    
    def __init__(self, sql_reports_dir: Path, output_dir: Path):
        """
        Initialize column lineage extractor.
        
        Args:
            sql_reports_dir: Directory containing SQL files
            output_dir: Directory for output reports
        """
        self.sql_reports_dir = sql_reports_dir
        self.output_dir = output_dir
        self.parser = SQLParser(dialect="tsql")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def scan_sql_files(self) -> List[Path]:
        """
        Scan for all SQL files in the SQL_Reports directory.
        
        Returns:
            List of Path objects for SQL files
        """
        sql_files = list(self.sql_reports_dir.rglob("*.sql"))
        logger.info(f"📁 Found {len(sql_files)} SQL files")
        return sql_files
    
    def extract_column_lineage(self) -> Dict[str, Any]:
        """
        Extract column lineage from all SQL files.
        
        Returns:
            Dictionary with column lineage data:
            - files: List of file information with columns
            - ambiguous_files: Files with ambiguous columns
            - summary: Summary statistics
        """
        sql_files = self.scan_sql_files()
        
        all_files_info = []
        ambiguous_files = []
        total_columns = 0
        total_ambiguous = 0
        
        logger.info("📊 Extracting column lineage...")
        
        for i, sql_file in enumerate(sql_files, 1):
            if i % 50 == 0:
                logger.info(f"  Progress: {i}/{len(sql_files)} files processed")
            
            try:
                # Read SQL file
                with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
                    sql = f.read()
                
                # Extract columns
                column_info = self.parser.extract_columns_from_query(sql)
                
                # Get relative path
                try:
                    rel_path = sql_file.relative_to(self.sql_reports_dir)
                except ValueError:
                    rel_path = sql_file
                
                file_info = {
                    'file_path': str(sql_file),
                    'relative_path': str(rel_path),
                    'file_name': sql_file.name,
                    'total_columns': column_info['total_columns'],
                    'ambiguous_count': len(column_info['ambiguous_columns']),
                    'ambiguous_columns': column_info['ambiguous_columns']
                }
                
                all_files_info.append(file_info)
                
                # Track ambiguous files
                if column_info['ambiguous_columns']:
                    ambiguous_files.append(file_info)
                    total_ambiguous += len(column_info['ambiguous_columns'])
                
                total_columns += column_info['total_columns']
                
            except Exception as e:
                logger.error(f"❌ Error processing {sql_file}: {e}")
        
        # Sort ambiguous files by number of ambiguous columns
        ambiguous_files.sort(key=lambda x: x['ambiguous_count'], reverse=True)
        
        summary = {
            'total_files': len(sql_files),
            'total_columns': total_columns,
            'files_with_ambiguous_columns': len(ambiguous_files),
            'total_ambiguous_columns': total_ambiguous,
            'ambiguous_percentage': round(
                (len(ambiguous_files) / len(sql_files) * 100) if sql_files else 0, 2
            )
        }
        
        logger.info(f"✅ Column extraction complete!")
        logger.info(f"  Total files: {summary['total_files']}")
        logger.info(f"  Total columns: {summary['total_columns']}")
        logger.info(f"  Files with ambiguous columns: {summary['files_with_ambiguous_columns']}")
        logger.info(f"  Total ambiguous columns: {summary['total_ambiguous_columns']}")
        
        return {
            'files': all_files_info,
            'ambiguous_files': ambiguous_files,
            'summary': summary
        }
    
    def save_report(self, lineage_data: Dict[str, Any], output_file: Path):
        """
        Save column lineage report to JSON file.
        
        Args:
            lineage_data: Column lineage data dictionary
            output_file: Output file path
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(lineage_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Report saved to: {output_file}")
    
    def print_summary(self, lineage_data: Dict[str, Any]):
        """
        Print summary of column lineage extraction.
        
        Args:
            lineage_data: Column lineage data dictionary
        """
        summary = lineage_data['summary']
        ambiguous_files = lineage_data['ambiguous_files'][:10]
        
        print("\n" + "=" * 60)
        print("📊 COLUMN LINEAGE SUMMARY")
        print("=" * 60)
        print(f"\n📁 Files Analyzed: {summary['total_files']}")
        print(f"📋 Total Columns: {summary['total_columns']}")
        print(f"\n⚠️  Files with Ambiguous Columns: {summary['files_with_ambiguous_columns']}")
        print(f"⚠️  Total Ambiguous Columns: {summary['total_ambiguous_columns']}")
        print(f"📊 Ambiguous Files Percentage: {summary['ambiguous_percentage']}%")
        
        if ambiguous_files:
            print(f"\n🔍 Top 10 Files with Most Ambiguous Columns:")
            print("-" * 60)
            for i, file_info in enumerate(ambiguous_files, 1):
                print(f"{i:2d}. {file_info['relative_path']}")
                print(f"    Ambiguous columns: {file_info['ambiguous_count']}")
                if file_info['ambiguous_columns'][:5]:
                    print(f"    Examples: {', '.join(file_info['ambiguous_columns'][:5])}")
                print()
        
        print("=" * 60)


def main():
    """Main entry point."""
    # Determine paths relative to this script
    script_dir = Path(__file__).parent.parent
    repo_root = script_dir.parent.parent.parent
    
    sql_reports_dir = repo_root / "SQL_Reports"
    output_dir = script_dir / "reports" / "lineage"
    output_file = output_dir / "column_lineage.json"
    
    # Verify SQL_Reports directory exists
    if not sql_reports_dir.exists():
        logger.error(f"❌ SQL_Reports directory not found: {sql_reports_dir}")
        sys.exit(1)
    
    logger.info(f"🚀 Starting column lineage extraction")
    logger.info(f"📁 SQL Reports Directory: {sql_reports_dir}")
    logger.info(f"📁 Output Directory: {output_dir}")
    
    # Create extractor and run
    extractor = ColumnLineageExtractor(sql_reports_dir, output_dir)
    lineage_data = extractor.extract_column_lineage()
    
    # Save report
    extractor.save_report(lineage_data, output_file)
    
    # Print summary
    extractor.print_summary(lineage_data)
    
    logger.info(f"\n✅ Column lineage extraction complete!")
    logger.info(f"📄 Full report available at: {output_file}")


if __name__ == "__main__":
    main()
