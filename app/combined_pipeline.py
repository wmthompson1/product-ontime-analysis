"""
Combined Cleansing + Segmentation Pipeline
===========================================
Integrates data cleansing and document segmentation into a single pipeline
that outputs multiple CSV files based on segmentation scheme.

Author: Manufacturing Intelligence Team
Purpose: Berkeley Haas AI Strategy - Production ETL for Invoice Processing
"""

import pandas as pd
import openpyxl
from io import BytesIO, StringIO
from typing import Dict, List, Optional
import os
import tempfile

from app.document_segmentation import (
    parse_segmentation_scheme,
    excel_range_to_indices,
    extract_freeform_block,
    extract_tabular_block
)
from app.excel_cleansing import cleanse_dataframe


def process_combined_pipeline(
    excel_file,
    segmentation_scheme: Optional[str] = None,
    schema_rules: Optional[Dict] = None,
    output_dir: Optional[str] = None
) -> Dict:
    """
    Combined pipeline: Segment document, cleanse data, output multiple CSVs.
    
    Args:
        excel_file: File-like object or path to Excel file
        segmentation_scheme: CSV string with columns: Doc, block, upper_left, lower_right, Segment type, Block_output_csv
        schema_rules: Optional JSON schema for data type enforcement
        output_dir: Directory to save output CSV files (default: temp directory)
        
    Returns:
        Dictionary with:
            - blocks: List of processed blocks with CSV paths
            - csv_files: Dictionary mapping CSV names to file paths
            - statistics: Processing statistics per block
            - report: Human-readable report
    """
    default_scheme = """Doc,block,upper_left,lower_right,Segment type,Block_output_csv
1,1,A3,B5,Free-form,identity.csv
1,2,A8,Doc 1 end,Tabular-form,Data.csv"""
    
    scheme = segmentation_scheme if segmentation_scheme else default_scheme
    scheme_df = parse_segmentation_scheme_with_output(scheme)
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)
    
    wb = openpyxl.load_workbook(excel_file)
    sheet = wb.active
    
    result = {
        'document_id': int(scheme_df['Doc'].iloc[0]),
        'total_blocks': len(scheme_df),
        'blocks': [],
        'csv_files': {},
        'statistics': {},
        'output_dir': output_dir
    }
    
    for idx, row in scheme_df.iterrows():
        doc_id = int(row['Doc'])
        block_id = int(row['block'])
        range_str = f"{row['upper_left']}:{row['lower_right']}"
        segment_type = row['Segment type']
        output_csv = row['Block_output_csv']
        
        start_row, end_row, start_col, end_col = excel_range_to_indices(range_str, sheet)
        
        block_data = {
            'block_id': block_id,
            'range': range_str,
            'segment_type': segment_type,
            'output_csv': output_csv
        }
        
        csv_path = os.path.join(output_dir, output_csv)
        
        if segment_type.lower() == 'free-form':
            metadata = extract_freeform_block(sheet, start_row, end_row, start_col, end_col)
            
            df_transposed = transpose_freeform_to_dataframe(metadata)
            
            df_cleaned, stats = cleanse_dataframe(df_transposed, schema_rules)
            
            df_cleaned.to_csv(csv_path, index=False)
            
            block_data['content_type'] = 'metadata'
            block_data['row_count'] = len(df_cleaned)
            block_data['column_count'] = len(df_cleaned.columns)
            block_data['csv_path'] = csv_path
            
            result['statistics'][output_csv] = stats
            
        elif segment_type.lower() == 'tabular-form':
            table_data = extract_tabular_block(sheet, start_row, end_row, start_col, end_col)
            
            df = pd.DataFrame(table_data['data'], columns=table_data['columns'])
            
            df_cleaned, stats = cleanse_dataframe(df, schema_rules)
            
            df_cleaned.to_csv(csv_path, index=False)
            
            block_data['content_type'] = 'table'
            block_data['row_count'] = len(df_cleaned)
            block_data['column_count'] = len(df_cleaned.columns)
            block_data['csv_path'] = csv_path
            
            result['statistics'][output_csv] = stats
        
        result['blocks'].append(block_data)
        result['csv_files'][output_csv] = csv_path
    
    wb.close()
    
    result['report'] = format_combined_report(result)
    
    return result


def parse_segmentation_scheme_with_output(scheme_content: str) -> pd.DataFrame:
    """
    Parse segmentation scheme with Block_output_csv column.
    
    Args:
        scheme_content: CSV string with columns: Doc, block, upper_left, lower_right, Segment type, Block_output_csv
        
    Returns:
        DataFrame with segmentation scheme
    """
    df = pd.read_csv(StringIO(scheme_content))
    
    required_cols = ['Doc', 'block', 'upper_left', 'lower_right', 'Segment type', 'Block_output_csv']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}. Expected: {', '.join(required_cols)}")
    
    return df


def transpose_freeform_to_dataframe(metadata: Dict) -> pd.DataFrame:
    """
    Transpose free-form metadata dict to DataFrame.
    
    Free-form blocks are key-value pairs that need to be transposed:
    Input:  {'supplier invoice #': 'abc123', 'document reference #': '989864'}
    Output: DataFrame with columns ['supplier invoice #', 'document reference #']
            and one row with values ['abc123', '989864']
    
    Args:
        metadata: Dictionary of key-value pairs
        
    Returns:
        Transposed DataFrame with one row
    """
    if not metadata:
        return pd.DataFrame()
    
    df = pd.DataFrame([metadata])
    
    return df


def format_combined_report(result: Dict) -> str:
    """
    Format combined pipeline result as human-readable report.
    
    Args:
        result: Output from process_combined_pipeline()
        
    Returns:
        Formatted text report
    """
    lines = []
    lines.append("=" * 80)
    lines.append("COMBINED CLEANSING + SEGMENTATION PIPELINE REPORT")
    lines.append("=" * 80)
    lines.append(f"\nDocument ID: {result['document_id']}")
    lines.append(f"Total Blocks: {result['total_blocks']}")
    lines.append(f"Output Directory: {result['output_dir']}\n")
    
    lines.append("CSV FILES GENERATED:")
    lines.append("-" * 80)
    for csv_name, csv_path in result['csv_files'].items():
        lines.append(f"  ✓ {csv_name} → {csv_path}")
    lines.append("")
    
    for block in result['blocks']:
        lines.append("-" * 80)
        lines.append(f"Block {block['block_id']}: {block['segment_type']}")
        lines.append(f"Range: {block['range']}")
        lines.append(f"Content Type: {block['content_type']}")
        lines.append(f"Output CSV: {block['output_csv']}")
        lines.append(f"Rows: {block['row_count']}, Columns: {block['column_count']}")
        
        if block['output_csv'] in result['statistics']:
            stats = result['statistics'][block['output_csv']]
            lines.append("\nCleansing Statistics:")
            lines.append(f"  • Original rows: {stats.get('original_rows', 'N/A')}")
            lines.append(f"  • Final rows: {stats.get('final_rows', 'N/A')}")
            lines.append(f"  • Missing values fixed: {stats.get('missing_values_fixed', 0)}")
            lines.append(f"  • Duplicates removed: {stats.get('duplicates_removed', 0)}")
            lines.append(f"  • Outliers detected: {stats.get('outliers_detected', 0)}")
            
            if stats.get('warnings'):
                lines.append("\n  Warnings:")
                for warning in stats['warnings']:
                    lines.append(f"    ⚠ {warning}")
        
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("PIPELINE COMPLETED SUCCESSFULLY")
    lines.append("=" * 80)
    
    return "\n".join(lines)
