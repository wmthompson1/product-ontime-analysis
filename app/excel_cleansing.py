"""
Excel Data Cleansing Module for Web Upload
==========================================
Provides data cleansing functionality for uploaded Excel files.
"""

import pandas as pd
import numpy as np
import re
from io import BytesIO


def cleanse_uploaded_excel(file_stream):
    """
    Cleanse Excel data from uploaded file stream.
    
    Args:
        file_stream: File-like object from request.files
        
    Returns:
        tuple: (cleansed_df, report_dict, cleansed_excel_bytes)
    """
    
    report = {
        'steps': [],
        'warnings': [],
        'statistics': {}
    }
    
    df = pd.read_excel(file_stream)
    original_shape = df.shape
    
    nbsp_in_headers = any('\xa0' in str(col) for col in df.columns)
    if nbsp_in_headers:
        df.columns = [str(col).replace('\xa0', ' ') for col in df.columns]
        report['steps'].append("✓ Removed NBSP characters from column headers")
    
    report['steps'].append(f"✓ Loaded {len(df)} rows and {len(df.columns)} columns")
    report['statistics']['original_rows'] = len(df)
    report['statistics']['original_cols'] = len(df.columns)
    report['statistics']['original_columns'] = list(df.columns)
    
    missing_before = df.isnull().sum().sum()
    report['statistics']['missing_values_before'] = int(missing_before)
    
    if missing_before > 0:
        missing_details = []
        for col in df.columns:
            missing = df[col].isnull().sum()
            if missing > 0:
                pct = (missing / len(df)) * 100
                missing_details.append(f"{col}: {missing} ({pct:.1f}%)")
        
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
            elif df[col].dtype == 'object':
                df[col] = df[col].fillna('Unknown')
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].fillna(pd.NaT)
        
        report['steps'].append(f"✓ Filled {missing_before} missing values")
        report['warnings'].extend(missing_details)
    
    duplicates_before = df.duplicated().sum()
    report['statistics']['duplicates_before'] = int(duplicates_before)
    
    if duplicates_before > 0:
        df = df.drop_duplicates()
        report['steps'].append(f"✓ Removed {duplicates_before} duplicate rows")
        report['warnings'].append(f"Removed {duplicates_before} duplicate rows")
    
    text_columns = df.select_dtypes(include=['object']).columns
    nbsp_count = 0
    for col in text_columns:
        df[col] = df[col].astype(str).str.replace('\xa0', ' ', regex=False)
        nbsp_count += df[col].str.contains('\xa0').sum()
        df[col] = df[col].str.strip()
        df[col] = df[col].str.replace(r'\s+', ' ', regex=True)
    
    if nbsp_count > 0:
        report['steps'].append(f"✓ Removed NBSP characters from data cells")
    report['steps'].append(f"✓ Standardized text in {len(text_columns)} columns")
    
    original_cols = df.columns.tolist()
    df.columns = [
        re.sub(r'[^\w\s]', '', col)
        .strip()
        .replace(' ', '_')
        .lower()
        for col in df.columns
    ]
    
    col_changes = [f"'{old}' → '{new}'" for old, new in zip(original_cols, df.columns) if old != new]
    if col_changes:
        report['steps'].append(f"✓ Standardized {len(col_changes)} column names")
        report['statistics']['column_changes'] = col_changes
    
    outliers = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
        if outlier_count > 0:
            outliers[col] = {
                'count': int(outlier_count),
                'range': f"[{lower_bound:.2f}, {upper_bound:.2f}]"
            }
    
    if outliers:
        report['steps'].append(f"✓ Detected outliers in {len(outliers)} columns")
        report['statistics']['outliers'] = outliers
    
    text_column_patterns = ['invoice', 'id', 'number', 'code', 'sku', 'part', 'serial', 'account', 'ref']
    text_format_cols = []
    
    for col in df.columns:
        is_id_like = any(pattern in col.lower() for pattern in text_column_patterns)
        
        if df[col].dtype == 'object' and not is_id_like:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        elif is_id_like:
            df[col] = df[col].astype(str)
            text_format_cols.append(col)
    
    if text_format_cols:
        report['steps'].append(f"✓ Preserved {len(text_format_cols)} ID/invoice columns as text format")
        report['statistics']['text_format_columns'] = text_format_cols
    
    report['statistics']['final_rows'] = len(df)
    report['statistics']['final_cols'] = len(df.columns)
    report['statistics']['missing_values_after'] = int(df.isnull().sum().sum())
    report['statistics']['duplicates_after'] = int(df.duplicated().sum())
    
    report['steps'].append(f"✓ Final shape: {df.shape}")
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        for idx, col in enumerate(df.columns, 1):
            if col in text_format_cols:
                for row in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row, column=idx)
                    cell.number_format = '@'
    
    output.seek(0)
    cleansed_bytes = output.getvalue()
    
    return df, report, cleansed_bytes
