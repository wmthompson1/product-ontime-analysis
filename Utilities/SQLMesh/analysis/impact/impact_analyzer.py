#!/usr/bin/env python3
"""
Impact Analyzer

Analyzes the impact of schema changes (table modifications or deletions).
Provides impact assessment and recommendations.

Usage:
    python impact_analyzer.py --table TABLE_NAME
    python impact_analyzer.py --table PART
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Analyze impact of schema changes."""
    
    # Impact level thresholds
    IMPACT_LEVELS = {
        'none': 0,
        'low': 1,
        'medium': 5,
        'high': 10
    }
    
    def __init__(self, lineage_file: Path):
        """
        Initialize impact analyzer.
        
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
    
    def analyze_table_change(self, table_name: str) -> Dict[str, Any]:
        """
        Assess the impact of changing or dropping a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with impact analysis:
            - table_name: Name of the table
            - impact_level: none, low, medium, or high
            - affected_files: List of files that will be affected
            - file_count: Number of affected files
            - recommendations: List of recommended actions
        """
        if not self.lineage_data:
            self.load_lineage_data()
        
        # Find all files using this table
        affected_files = []
        search_term = table_name.upper()
        
        for file_info in self.lineage_data.get('files', []):
            for table in file_info.get('tables', []):
                table_full_name = table['full_name'].upper()
                table_short_name = table['table'].upper() if table.get('table') else ''
                
                if search_term in table_full_name or search_term == table_short_name:
                    affected_files.append({
                        'file_path': file_info.get('relative_path', file_info.get('file_path')),
                        'file_name': file_info['file_name'],
                        'table_reference': table['full_name']
                    })
                    break  # Only count each file once
        
        # Determine impact level
        file_count = len(affected_files)
        impact_level = self._determine_impact_level(file_count)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(table_name, file_count, impact_level)
        
        return {
            'table_name': table_name,
            'impact_level': impact_level,
            'affected_files': affected_files,
            'file_count': file_count,
            'recommendations': recommendations
        }
    
    def _determine_impact_level(self, file_count: int) -> str:
        """
        Determine impact level based on number of affected files.
        
        Args:
            file_count: Number of affected files
            
        Returns:
            Impact level: 'none', 'low', 'medium', or 'high'
        """
        if file_count == 0:
            return 'none'
        elif file_count < self.IMPACT_LEVELS['medium']:
            return 'low'
        elif file_count < self.IMPACT_LEVELS['high']:
            return 'medium'
        else:
            return 'high'
    
    def _generate_recommendations(self, table_name: str, file_count: int, 
                                   impact_level: str) -> List[str]:
        """
        Generate recommendations based on impact analysis.
        
        Args:
            table_name: Name of the table
            file_count: Number of affected files
            impact_level: Impact level
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if impact_level == 'none':
            recommendations.append(f"✅ No SQL files currently reference table '{table_name}'")
            recommendations.append("Safe to modify or drop this table")
        
        elif impact_level == 'low':
            recommendations.append(f"⚠️  {file_count} SQL file(s) will be affected")
            recommendations.append("Review and update affected files before making changes")
            recommendations.append("Consider creating a backup of current table structure")
            recommendations.append("Test changes in development environment first")
        
        elif impact_level == 'medium':
            recommendations.append(f"⚠️  {file_count} SQL files will be affected - MODERATE IMPACT")
            recommendations.append("Plan a maintenance window for this change")
            recommendations.append("Review all affected files and update queries")
            recommendations.append("Create migration scripts for table changes")
            recommendations.append("Test thoroughly in development and staging environments")
            recommendations.append("Notify report users of potential downtime")
        
        else:  # high
            recommendations.append(f"🚨 {file_count} SQL files will be affected - HIGH IMPACT")
            recommendations.append("This is a critical change requiring careful planning")
            recommendations.append("Schedule extended maintenance window")
            recommendations.append("Create detailed rollback plan")
            recommendations.append("Update all affected SQL files and test extensively")
            recommendations.append("Consider phased migration approach")
            recommendations.append("Notify all stakeholders well in advance")
            recommendations.append("Document all changes comprehensively")
        
        return recommendations
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """
        Print impact analysis results.
        
        Args:
            analysis: Impact analysis dictionary
        """
        impact_icons = {
            'none': '✅',
            'low': '⚠️ ',
            'medium': '⚠️ ',
            'high': '🚨'
        }
        
        impact_colors = {
            'none': 'GREEN',
            'low': 'YELLOW',
            'medium': 'ORANGE',
            'high': 'RED'
        }
        
        print("\n" + "=" * 70)
        print(f"📊 IMPACT ANALYSIS: {analysis['table_name']}")
        print("=" * 70)
        
        icon = impact_icons.get(analysis['impact_level'], '❓')
        color = impact_colors.get(analysis['impact_level'], 'UNKNOWN')
        
        print(f"\n{icon} Impact Level: {analysis['impact_level'].upper()} ({color})")
        print(f"📁 Affected Files: {analysis['file_count']}")
        
        if analysis['affected_files']:
            print(f"\n📋 Affected SQL Files:")
            print("-" * 70)
            for i, file_info in enumerate(analysis['affected_files'], 1):
                print(f"{i:3d}. {file_info['file_path']}")
                print(f"      References: {file_info['table_reference']}")
        
        print(f"\n💡 Recommendations:")
        print("-" * 70)
        for rec in analysis['recommendations']:
            print(f"  {rec}")
        
        print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze impact of table changes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python impact_analyzer.py --table WORK_ORDER
  python impact_analyzer.py --table LIVE.dbo.PART
  python impact_analyzer.py --table CUSTOMER_ORDER
        """
    )
    parser.add_argument(
        '--table', '-t',
        required=True,
        help='Table name to analyze'
    )
    
    args = parser.parse_args()
    
    # Determine paths
    script_dir = Path(__file__).parent.parent
    lineage_file = script_dir / "reports" / "lineage" / "table_lineage.json"
    
    # Create analyzer and run analysis
    analyzer = ImpactAnalyzer(lineage_file)
    analysis = analyzer.analyze_table_change(args.table)
    
    # Print results
    analyzer.print_analysis(analysis)
    
    # Exit code based on impact level
    exit_codes = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
    sys.exit(exit_codes.get(analysis['impact_level'], 0))


if __name__ == "__main__":
    main()
