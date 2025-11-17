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
from app.excel_cleansing import cleanse_dataframe, normalize_column_names


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
        segmentation_scheme: CSV string with columns: Doc, block, upper_left, lower_right, Segment type, Block_output_csv, schema_number
        schema_rules: Optional dictionary of schemas indexed by schema_number
                     Example: {0: {}, 1: {"date": "date", "total_received": "numeric"}}
                     When a schema is provided for a block, only columns in the schema are kept
        output_dir: Directory to save output CSV files (default: temp directory)
        
    Returns:
        Dictionary with:
            - blocks: List of processed blocks with CSV paths
            - csv_files: Dictionary mapping CSV names to file paths
            - statistics: Processing statistics per block
            - report: Human-readable report
    """
    default_scheme = """Doc,block,upper_left,lower_right,Segment type,Block_output_csv,schema_number
1,1,A3,B5,Free-form,identity.csv,1
1,2,A8,Doc 1 end,Tabular-form,Data.csv,2"""
    
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
        schema_number = row.get('schema_number', None)
        
        start_row, end_row, start_col, end_col = excel_range_to_indices(range_str, sheet)
        
        block_data = {
            'block_id': block_id,
            'range': range_str,
            'segment_type': segment_type,
            'output_csv': output_csv,
            'schema_number': schema_number if pd.notna(schema_number) else None
        }
        
        csv_path = os.path.join(output_dir, output_csv)
        
        block_schema_num = int(schema_number) if pd.notna(schema_number) else None
        block_schema = get_schema_for_block(schema_rules, block_schema_num)
        
        if segment_type.lower() == 'free-form':
            metadata = extract_freeform_block(sheet, start_row, end_row, start_col, end_col)
            
            df_transposed = transpose_freeform_to_dataframe(metadata)
            
            # Normalize column names BEFORE filtering so schemas can use clean names
            df_transposed.columns = normalize_column_names(df_transposed.columns)
            
            df_filtered, filter_stats = filter_columns_by_schema(df_transposed, block_schema)
            
            df_cleaned, cleanse_stats = cleanse_dataframe(df_filtered, block_schema)
            
            df_cleaned.to_csv(csv_path, index=False)
            
            combined_stats = cleanse_stats.copy()
            combined_stats.update({k: v for k, v in filter_stats.items() if k != 'warnings'})
            combined_stats['warnings'] = cleanse_stats.get('warnings', []) + filter_stats.get('warnings', [])
            
            block_data['content_type'] = 'metadata'
            block_data['row_count'] = len(df_cleaned)
            block_data['column_count'] = len(df_cleaned.columns)
            block_data['csv_path'] = csv_path
            block_data['columns_filtered'] = filter_stats['columns_filtered']
            block_data['columns_dropped'] = filter_stats['columns_dropped']
            
            result['statistics'][output_csv] = combined_stats
            
        elif segment_type.lower() == 'tabular-form':
            table_data = extract_tabular_block(sheet, start_row, end_row, start_col, end_col)
            
            df = pd.DataFrame(table_data['data'], columns=table_data['columns'])
            
            # Normalize column names BEFORE filtering so schemas can use clean names
            df.columns = normalize_column_names(df.columns)
            
            df_filtered, filter_stats = filter_columns_by_schema(df, block_schema)
            
            df_cleaned, cleanse_stats = cleanse_dataframe(df_filtered, block_schema)
            
            df_cleaned.to_csv(csv_path, index=False)
            
            combined_stats = cleanse_stats.copy()
            combined_stats.update({k: v for k, v in filter_stats.items() if k != 'warnings'})
            combined_stats['warnings'] = cleanse_stats.get('warnings', []) + filter_stats.get('warnings', [])
            
            block_data['content_type'] = 'table'
            block_data['row_count'] = len(df_cleaned)
            block_data['column_count'] = len(df_cleaned.columns)
            block_data['csv_path'] = csv_path
            block_data['columns_filtered'] = filter_stats['columns_filtered']
            block_data['columns_dropped'] = filter_stats['columns_dropped']
            
            result['statistics'][output_csv] = combined_stats
        
        result['blocks'].append(block_data)
        result['csv_files'][output_csv] = csv_path
    
    wb.close()
    
    result['report'] = format_combined_report(result)
    
    return result


def get_schema_for_block(schema_rules: Optional[Dict], schema_number: Optional[int]) -> Optional[Dict]:
    """
    Get the schema rules for a specific block based on its schema_number.
    
    Args:
        schema_rules: Dictionary of schemas indexed by schema_number
                     Example: {0: {}, 1: {"date": "date", "total_received": "numeric"}}
        schema_number: The schema number for the block
        
    Returns:
        Schema dict for the block, or None if no schema is defined
    """
    if schema_rules is None or schema_number is None:
        return None
    
    if isinstance(schema_rules, dict) and schema_number in schema_rules:
        return schema_rules[schema_number]
    
    if isinstance(schema_rules, dict) and str(schema_number) in schema_rules:
        return schema_rules[str(schema_number)]
    
    return None


def filter_columns_by_schema(df: pd.DataFrame, schema: Optional[Dict]) -> tuple[pd.DataFrame, Dict]:
    """
    Filter DataFrame columns to keep only those defined in the schema.
    
    If schema is None or empty, returns the original DataFrame unchanged.
    If schema is provided, only keeps columns that appear in the schema.
    
    Args:
        df: DataFrame to filter
        schema: Schema dictionary with column names as keys
                Example: {"date": "date", "total_received": "numeric", "received_late": "numeric"}
        
    Returns:
        Tuple of (filtered_df, filter_stats)
        - filtered_df: DataFrame with only schema-defined columns
        - filter_stats: Dictionary with filtering statistics
    """
    filter_stats = {
        'columns_filtered': 0,
        'columns_dropped': [],
        'columns_missing': [],
        'warnings': []
    }
    
    if schema is None or not schema:
        return df, filter_stats
    
    schema_columns = list(schema.keys())
    available_columns = [col for col in schema_columns if col in df.columns]
    missing_columns = [col for col in schema_columns if col not in df.columns]
    dropped_columns = [col for col in df.columns if col not in schema_columns]
    
    if missing_columns:
        filter_stats['columns_missing'] = missing_columns
        filter_stats['warnings'].append(
            f"Schema requires {len(missing_columns)} columns not found in data: {', '.join(missing_columns)}"
        )
    
    if not available_columns:
        filter_stats['warnings'].append(
            f"No schema columns found in data! Schema expects: {', '.join(schema_columns)}, "
            f"but data has: {', '.join(df.columns.tolist())}"
        )
        return pd.DataFrame(), filter_stats
    
    df_filtered = df[available_columns].copy()
    
    filter_stats['columns_filtered'] = len(dropped_columns)
    filter_stats['columns_dropped'] = dropped_columns
    
    return df_filtered, filter_stats


def parse_segmentation_scheme_with_output(scheme_content: str) -> pd.DataFrame:
    """
    Parse segmentation scheme with Block_output_csv and optional schema_number columns.
    
    Args:
        scheme_content: CSV string with columns: Doc, block, upper_left, lower_right, Segment type, Block_output_csv, schema_number (optional)
        
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
