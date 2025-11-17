#!/usr/bin/env python3
"""
Entry Point 023: Combined Cleansing + Segmentation Pipeline
============================================================
Unified pipeline combining data cleansing and document segmentation
with multi-CSV output. Perfect for ETL workflows.

Usage:
    python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx
    python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --scheme segmentation.csv --schema schema.json
    python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --output-dir ./results --preview

Author: Manufacturing Intelligence Team
Purpose: Berkeley Haas AI Strategy - Production ETL for Invoice Processing
"""

import argparse
import json
import sys
from pathlib import Path

from app.combined_pipeline import process_combined_pipeline


def main():
    parser = argparse.ArgumentParser(
        description='Combined Cleansing + Segmentation Pipeline - Output multiple CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default segmentation scheme
  python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx
  
  # Use custom segmentation scheme
  python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --scheme my_scheme.csv
  
  # Add schema enforcement for data types
  python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --schema schema.json
  
  # Specify output directory and preview results
  python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --output-dir ./results --preview
  
Segmentation Scheme Format (CSV):
  Doc,block,upper_left,lower_right,Segment type,Block_output_csv
  1,1,A3,B5,Free-form,identity.csv
  1,2,A8,Doc 1 end,Tabular-form,Data.csv
  
Schema Format (JSON):
  {
    "invoice_number": "text",
    "amount": "numeric",
    "payment_date": "date"
  }
        '''
    )
    
    parser.add_argument('excel_file', help='Path to Excel file to process')
    parser.add_argument('--scheme', help='Path to segmentation scheme CSV (optional)')
    parser.add_argument('--schema', help='Path to JSON schema for data type enforcement (optional)')
    parser.add_argument('--output-dir', help='Directory to save CSV files (default: temp directory)')
    parser.add_argument('--preview', action='store_true', help='Preview first 10 rows of each CSV')
    parser.add_argument('--report-only', action='store_true', help='Only show report, do not save files')
    
    args = parser.parse_args()
    
    excel_path = Path(args.excel_file)
    if not excel_path.exists():
        print(f"❌ Error: Excel file not found: {args.excel_file}")
        sys.exit(1)
    
    segmentation_content = None
    if args.scheme:
        scheme_path = Path(args.scheme)
        if not scheme_path.exists():
            print(f"❌ Error: Segmentation scheme file not found: {args.scheme}")
            sys.exit(1)
        segmentation_content = scheme_path.read_text()
    
    schema_rules = None
    if args.schema:
        schema_path = Path(args.schema)
        if not schema_path.exists():
            print(f"❌ Error: Schema file not found: {args.schema}")
            sys.exit(1)
        with open(schema_path, 'r') as f:
            schema_rules = json.load(f)
    
    print("🚀 Starting Combined Cleansing + Segmentation Pipeline...")
    print(f"📄 Input File: {args.excel_file}")
    if args.scheme:
        print(f"📋 Segmentation Scheme: {args.scheme}")
    else:
        print(f"📋 Segmentation Scheme: Default (invoice format)")
    if args.schema:
        print(f"🔍 Schema Enforcement: {args.schema}")
    print()
    
    try:
        result = process_combined_pipeline(
            excel_file=str(excel_path),
            segmentation_scheme=segmentation_content,
            schema_rules=schema_rules,
            output_dir=args.output_dir
        )
        
        print(result['report'])
        
        if args.preview:
            print("\n" + "=" * 80)
            print("CSV FILE PREVIEWS")
            print("=" * 80)
            
            import pandas as pd
            for csv_name, csv_path in result['csv_files'].items():
                print(f"\n📊 {csv_name}")
                print("-" * 80)
                df = pd.read_csv(csv_path)
                print(df.head(10).to_string(index=False))
                print()
        
        print("\n✅ Pipeline completed successfully!")
        print(f"📁 Output directory: {result['output_dir']}")
        print(f"📊 Generated {len(result['csv_files'])} CSV files")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error processing pipeline: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
