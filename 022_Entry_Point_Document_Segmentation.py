#!/usr/bin/env python3
"""
Document Segmentation - Terminal Interface
==========================================
Segment Excel documents into blocks based on cell ranges and segment types.
Perfect for hybrid RAG: unstructured metadata + structured tables.

Author: Manufacturing Intelligence Team
Purpose: Berkeley Haas AI Strategy - Advanced RAG for Invoice Processing

Usage:
    python 022_Entry_Point_Document_Segmentation.py invoice.xlsx
    python 022_Entry_Point_Document_Segmentation.py invoice.xlsx --scheme segmentation.csv
    python 022_Entry_Point_Document_Segmentation.py invoice.xlsx --output result.json
"""

import argparse
import json
import sys
from pathlib import Path
from app.document_segmentation import segment_document, format_segmentation_report


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*70)
    print("📄 DOCUMENT SEGMENTATION FOR HYBRID RAG".center(70))
    print("="*70)


def print_section(title):
    """Print section header."""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


def main():
    parser = argparse.ArgumentParser(
        description='Segment Excel documents based on cell ranges and segment types',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s invoice.xlsx
  %(prog)s invoice.xlsx --scheme segmentation.csv
  %(prog)s invoice.xlsx --output segmented.json --scheme custom_scheme.csv

Default Segmentation Scheme (if not provided):
  Doc,block,upper_left,lower_right,Segment type
  1,1,A3,B5,Free-form
  1,2,A8,Doc 1 end,Tabular-form

Segment Types:
  - Free-form: Extracts as key-value metadata pairs
  - Tabular-form: Extracts as structured table with columns and rows
        """
    )
    
    parser.add_argument('input', 
                        help='Input Excel file (.xlsx)')
    parser.add_argument('-s', '--scheme',
                        help='Segmentation scheme CSV file (optional)')
    parser.add_argument('-o', '--output',
                        help='Output JSON file path (optional)')
    parser.add_argument('--report-only',
                        action='store_true',
                        help='Show formatted report only, no JSON')
    
    args = parser.parse_args()
    
    print_banner()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"\n✗ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    segmentation_content = None
    if args.scheme:
        scheme_path = Path(args.scheme)
        if not scheme_path.exists():
            print(f"\n✗ Error: Scheme file not found: {args.scheme}")
            sys.exit(1)
        
        with open(scheme_path, 'r') as f:
            segmentation_content = f.read()
        print(f"\n✓ Using custom segmentation scheme: {args.scheme}")
    else:
        print(f"\n💡 Using default segmentation scheme")
    
    print(f"\n📁 Input File: {input_path}")
    
    print("\n🚀 Starting document segmentation...")
    
    try:
        result = segment_document(str(input_path), segmentation_content)
        
        print("\n✅ Segmentation completed successfully!")
        
        report = format_segmentation_report(result)
        print("\n" + report)
        
        if not args.report_only:
            print_section("📊 JSON OUTPUT")
            json_output = json.dumps(result, indent=2, default=str)
            print(json_output)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print_section("💾 FILE SAVED")
            print(f"\n  ✓ JSON output saved to: {args.output}")
            
            file_size = Path(args.output).stat().st_size
            print(f"  ✓ File size: {file_size / 1024:.2f} KB")
        
        print("\n" + "="*70)
        print("✅ SUCCESS! Document segmented for hybrid RAG ingestion.".center(70))
        print("="*70 + "\n")
        
        print("💡 Next Steps:")
        print("   1. Ingest free-form blocks as metadata for semantic search")
        print("   2. Load tabular blocks into database for SQL queries")
        print("   3. Use hybrid RAG: vector search + structured queries\n")
        
    except Exception as e:
        print(f"\n✗ Error during segmentation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
