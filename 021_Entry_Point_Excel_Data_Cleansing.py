#!/usr/bin/env python3
"""
Excel Data Cleansing - Terminal Interface
==========================================
Command-line interface for cleansing Excel data with optional schema enforcement.
Provides the same functionality as the web interface in /excel-cleansing

Author: Manufacturing Intelligence Team
Purpose: Berkeley Haas AI Strategy - Data Preparation for Analytics

Usage:
    python 021_Entry_Point_Excel_Data_Cleansing.py input.xlsx
    python 021_Entry_Point_Excel_Data_Cleansing.py input.xlsx --schema schema.json
    python 021_Entry_Point_Excel_Data_Cleansing.py input.xlsx --output cleansed.xlsx
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from app.excel_cleansing import cleanse_uploaded_excel


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*70)
    print("🔧 EXCEL DATA CLEANSING FOR MANUFACTURING QUALITY CONTROL 🔧".center(70))
    print("="*70)


def print_section(title):
    """Print section header."""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


def print_statistics(stats):
    """Print cleansing statistics in a nice table format."""
    print_section("📊 CLEANSING STATISTICS")
    
    print(f"\n  Original Data:")
    print(f"    • Rows: {stats.get('original_rows', 0)}")
    print(f"    • Columns: {stats.get('original_cols', 0)}")
    
    print(f"\n  Final Data:")
    print(f"    • Rows: {stats.get('final_rows', 0)}")
    print(f"    • Columns: {stats.get('final_cols', 0)}")
    
    print(f"\n  Data Quality:")
    print(f"    • Missing values fixed: {stats.get('missing_values_before', 0)}")
    print(f"    • Duplicates removed: {stats.get('duplicates_before', 0)}")
    
    if stats.get('outliers'):
        print(f"    • Outliers detected in: {len(stats['outliers'])} columns")
    
    if stats.get('text_format_columns'):
        print(f"    • Text columns preserved: {len(stats['text_format_columns'])}")
        for col in stats['text_format_columns']:
            print(f"        - {col}")


def print_report(report):
    """Print the full processing report."""
    print_section("⚙️  PROCESSING STEPS")
    for step in report['steps']:
        print(f"  {step}")
    
    if report.get('warnings'):
        print_section("⚠️  WARNINGS")
        for warning in report['warnings']:
            print(f"  • {warning}")
    
    if report.get('statistics', {}).get('outliers'):
        print_section("🔍 OUTLIER ANALYSIS")
        for col, info in report['statistics']['outliers'].items():
            print(f"  • {col}: {info['count']} outliers detected")
            print(f"    Valid range: {info['range']}")
    
    print_statistics(report['statistics'])


def load_schema(schema_path):
    """Load schema from JSON file."""
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        print(f"\n✓ Loaded schema from {schema_path}")
        print(f"  Schema rules for {len(schema)} columns:")
        for col, dtype in schema.items():
            print(f"    • {col}: {dtype}")
        return schema
    except Exception as e:
        print(f"\n✗ Error loading schema: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Cleanse Excel files for manufacturing analytics with optional schema enforcement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data.xlsx
  %(prog)s payments.xlsx --schema schema.json
  %(prog)s data.xlsx --output clean_data.xlsx --schema my_schema.json

Schema Format (JSON):
  {
    "customer_reference": "text",
    "invoice_number": "text",
    "amount": "numeric",
    "payment_date": "date"
  }

Supported Types: text, numeric, date
        """
    )
    
    parser.add_argument('input', 
                        help='Input Excel file (.xlsx or .xls)')
    parser.add_argument('-o', '--output',
                        help='Output file path (default: input_cleaned.xlsx)')
    parser.add_argument('-s', '--schema',
                        help='JSON schema file to enforce column data types')
    parser.add_argument('-p', '--preview',
                        action='store_true',
                        help='Show data preview (first 20 rows)')
    parser.add_argument('--no-save',
                        action='store_true',
                        help='Process but do not save output file')
    
    args = parser.parse_args()
    
    print_banner()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"\n✗ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    
    schema_dict = None
    if args.schema:
        schema_dict = load_schema(args.schema)
    
    print(f"\n📁 Input:  {input_path}")
    print(f"💾 Output: {output_path}")
    if schema_dict:
        print(f"📋 Schema: Enforcing {len(schema_dict)} column type rules")
    else:
        print(f"📋 Schema: Auto-detection mode (use --schema to enforce types)")
    
    print("\n🚀 Starting data cleansing pipeline...")
    
    try:
        with open(input_path, 'rb') as f:
            df, report, cleansed_bytes = cleanse_uploaded_excel(f, schema_dict)
        
        print("\n✅ Cleansing completed successfully!")
        
        print_report(report)
        
        if args.preview:
            print_section("📋 DATA PREVIEW (First 20 Rows)")
            print("\n" + df.head(20).to_string())
        
        if not args.no_save:
            with open(output_path, 'wb') as f:
                f.write(cleansed_bytes)
            print_section("💾 FILE SAVED")
            print(f"\n  ✓ Cleansed data saved to: {output_path}")
            print(f"  ✓ File size: {len(cleansed_bytes) / 1024:.2f} KB")
        
        print("\n" + "="*70)
        print("✅ SUCCESS! Your data is clean and ready for analysis.".center(70))
        print("="*70 + "\n")
        
        if schema_dict:
            print("💡 TIP: Schema enforcement ensures consistent data types across uploads!")
            print("         Perfect for weekly ETL pipelines with varying data formats.\n")
        
    except Exception as e:
        print(f"\n✗ Error during cleansing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
