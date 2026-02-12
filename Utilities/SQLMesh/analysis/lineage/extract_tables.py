#!/usr/bin/env python3
"""
Table Lineage Extraction

Scans all SQL files in SQL_Reports directory and extracts table dependencies.
Generates a JSON report with:
- List of all files analyzed
- Tables used in each file
- Summary statistics
- Most-used tables ranking

NO SQL EXECUTION - Only static analysis using sqlglot.
"""

import json
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_parser import SQLParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class LineageExtractor:
    """Extract table lineage from SQL files."""
    
    def __init__(self, sql_reports_dir: Path, output_dir: Path):
        """
        Initialize lineage extractor.
        
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
    
    def extract_lineage(self) -> Dict[str, Any]:
        """
        Extract lineage from all SQL files.
        
        Returns:
            Dictionary with lineage data:
            - files: List of file information with tables
            - summary: Summary statistics
            - most_used_tables: Ranking of most frequently used tables
        """
        sql_files = self.scan_sql_files()
        
        all_files_info = []
        all_tables = []
        successful_parses = 0
        failed_parses = 0
        
        logger.info("📊 Extracting table lineage...")
        
        for i, sql_file in enumerate(sql_files, 1):
            if i % 50 == 0:
                logger.info(f"  Progress: {i}/{len(sql_files)} files processed")
            
            try:
                # Extract tables from file
                file_info = self.parser.extract_tables_from_file(sql_file)
                
                # Get relative path from SQL_Reports directory
                try:
                    rel_path = sql_file.relative_to(self.sql_reports_dir)
                    file_info['relative_path'] = str(rel_path)
                except ValueError:
                    file_info['relative_path'] = str(sql_file)
                
                all_files_info.append(file_info)
                
                # Collect all tables for statistics
                for table in file_info['tables']:
                    all_tables.append(table['full_name'])
                
                if file_info['parse_success']:
                    successful_parses += 1
                else:
                    failed_parses += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing {sql_file}: {e}")
                failed_parses += 1
        
        # Calculate summary statistics
        table_counter = Counter(all_tables)
        most_used = [
            {'table': table, 'count': count}
            for table, count in table_counter.most_common(50)
        ]
        
        summary = {
            'total_files': len(sql_files),
            'successful_parses': successful_parses,
            'failed_parses': failed_parses,
            'total_tables_referenced': len(all_tables),
            'unique_tables': len(table_counter),
            'most_used_tables': most_used
        }
        
        logger.info(f"✅ Extraction complete!")
        logger.info(f"  Total files: {summary['total_files']}")
        logger.info(f"  Successful: {summary['successful_parses']}")
        logger.info(f"  Failed: {summary['failed_parses']}")
        logger.info(f"  Unique tables: {summary['unique_tables']}")
        
        return {
            'files': all_files_info,
            'summary': summary,
            'most_used_tables': most_used
        }
    
    def save_report(self, lineage_data: Dict[str, Any], output_file: Path):
        """
        Save lineage report to JSON file.
        
        Args:
            lineage_data: Lineage data dictionary
            output_file: Output file path
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(lineage_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Report saved to: {output_file}")
    
    def print_summary(self, lineage_data: Dict[str, Any]):
        """
        Print summary of lineage extraction.
        
        Args:
            lineage_data: Lineage data dictionary
        """
        summary = lineage_data['summary']
        most_used = lineage_data['most_used_tables'][:10]
        
        print("\n" + "=" * 60)
        print("📊 TABLE LINEAGE SUMMARY")
        print("=" * 60)
        print(f"\n📁 Files Analyzed: {summary['total_files']}")
        print(f"✅ Successful Parses: {summary['successful_parses']}")
        print(f"❌ Failed Parses: {summary['failed_parses']}")
        print(f"\n📋 Total Tables Referenced: {summary['total_tables_referenced']}")
        print(f"🔢 Unique Tables: {summary['unique_tables']}")
        
        print(f"\n🏆 Top 10 Most Used Tables:")
        print("-" * 60)
        for i, table_info in enumerate(most_used, 1):
            print(f"{i:2d}. {table_info['table']:<40} (used {table_info['count']} times)")
        
        print("\n" + "=" * 60)


def main():
    """Main entry point."""
    # Determine paths relative to this script
    script_dir = Path(__file__).parent.parent
    repo_root = script_dir.parent.parent.parent
    
    sql_reports_dir = repo_root / "SQL_Reports"
    output_dir = script_dir / "reports" / "lineage"
    output_file = output_dir / "table_lineage.json"
    
    # Verify SQL_Reports directory exists
    if not sql_reports_dir.exists():
        logger.error(f"❌ SQL_Reports directory not found: {sql_reports_dir}")
        logger.error(f"   Current working directory: {Path.cwd()}")
        logger.error(f"   Script directory: {script_dir}")
        logger.error(f"   Repository root: {repo_root}")
        sys.exit(1)
    
    logger.info(f"🚀 Starting table lineage extraction")
    logger.info(f"📁 SQL Reports Directory: {sql_reports_dir}")
    logger.info(f"📁 Output Directory: {output_dir}")
    
    # Create extractor and run
    extractor = LineageExtractor(sql_reports_dir, output_dir)
    lineage_data = extractor.extract_lineage()
    
    # Save report
    extractor.save_report(lineage_data, output_file)
    
    # Print summary
    extractor.print_summary(lineage_data)
    
    logger.info(f"\n✅ Lineage extraction complete!")
    logger.info(f"📄 Full report available at: {output_file}")


if __name__ == "__main__":
    main()
