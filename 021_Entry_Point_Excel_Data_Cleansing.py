#!/usr/bin/env python3
"""
Excel Data Cleansing One-Pager
===============================
A comprehensive guide to cleansing Excel data using Python and Pandas.
Perfect for manufacturing quality control data preparation.

Author: Manufacturing Intelligence Team
Purpose: Berkeley Haas AI Strategy - Data Preparation for Analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def cleanse_excel_data(input_file: str, output_file: str):
    """
    Complete data cleansing pipeline for Excel files.
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to save cleansed Excel file
    """
    
    print("="*60)
    print("EXCEL DATA CLEANSING PIPELINE")
    print("="*60)
    
    print(f"\n1. LOADING DATA from {input_file}...")
    df = pd.read_excel(input_file)
    print(f"   ✓ Loaded {len(df)} rows and {len(df.columns)} columns")
    print(f"   Columns: {list(df.columns)}")
    
    print("\n2. INITIAL DATA INSPECTION")
    print(f"   Shape: {df.shape}")
    print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
    print("\n   Data types:")
    print(df.dtypes)
    
    print("\n3. HANDLING MISSING VALUES")
    missing_before = df.isnull().sum().sum()
    print(f"   Missing values found: {missing_before}")
    if missing_before > 0:
        print("\n   Missing values by column:")
        for col in df.columns:
            missing = df[col].isnull().sum()
            if missing > 0:
                pct = (missing / len(df)) * 100
                print(f"   - {col}: {missing} ({pct:.1f}%)")
        
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                df[col].fillna(df[col].median(), inplace=True)
            elif df[col].dtype == 'object':
                df[col].fillna('Unknown', inplace=True)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col].fillna(pd.NaT, inplace=True)
        
        print(f"   ✓ Filled {missing_before} missing values")
    
    print("\n4. REMOVING DUPLICATE ROWS")
    duplicates_before = df.duplicated().sum()
    print(f"   Duplicates found: {duplicates_before}")
    if duplicates_before > 0:
        df = df.drop_duplicates()
        print(f"   ✓ Removed {duplicates_before} duplicate rows")
    
    print("\n5. STANDARDIZING TEXT COLUMNS")
    text_columns = df.select_dtypes(include=['object']).columns
    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.replace(r'\s+', ' ', regex=True)
        print(f"   ✓ Cleaned whitespace in: {col}")
    
    print("\n6. STANDARDIZING COLUMN NAMES")
    original_cols = df.columns.tolist()
    df.columns = [
        re.sub(r'[^\w\s]', '', col)
        .strip()
        .replace(' ', '_')
        .lower()
        for col in df.columns
    ]
    print("   Column name changes:")
    for old, new in zip(original_cols, df.columns):
        if old != new:
            print(f"   - '{old}' → '{new}'")
    
    print("\n7. DETECTING AND HANDLING OUTLIERS")
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
        if outliers > 0:
            print(f"   - {col}: {outliers} outliers detected")
            print(f"     Valid range: [{lower_bound:.2f}, {upper_bound:.2f}]")
    
    print("\n8. DATA TYPE OPTIMIZATION")
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_numeric(df[col])
                print(f"   ✓ Converted {col} to numeric")
            except (ValueError, TypeError):
                try:
                    df[col] = pd.to_datetime(df[col])
                    print(f"   ✓ Converted {col} to datetime")
                except (ValueError, TypeError):
                    pass
    
    print("\n9. FINAL DATA SUMMARY")
    print(f"   Final shape: {df.shape}")
    print(f"   Missing values: {df.isnull().sum().sum()}")
    print(f"   Duplicates: {df.duplicated().sum()}")
    
    print(f"\n10. SAVING CLEANSED DATA to {output_file}...")
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"    ✓ Saved successfully!")
    
    print("\n" + "="*60)
    print("DATA CLEANSING COMPLETE")
    print("="*60)
    
    return df


def create_sample_manufacturing_data():
    """
    Create a sample manufacturing dataset with common data quality issues.
    This simulates real-world messy data from production systems.
    """
    
    data = {
        'Part ID   ': ['P001', 'P002', 'P003', 'P001', 'P004', None, 'P005', 'P006'],
        'Production Date': ['2024-01-15', '2024-01-16', '01/17/2024', '2024-01-15', 
                            '2024-01-18', '2024-01-19', None, '2024-01-20'],
        'Defect Count ': [2, 0, 1, 2, 15, 3, 1, 0],
        ' Operator Name': ['  John Smith', 'Jane Doe  ', 'Bob Johnson', 'John Smith', 
                           'Mary Wilson', 'Jane Doe', 'Bob Johnson', None],
        'Line #': ['Line 1', 'Line 2', 'Line 1', 'Line 1', 'Line 3', 'Line 2', 
                   'Line 1', 'Line 2'],
        'Cycle Time (min)': [45.5, 42.0, 48.2, 45.5, 120.0, 43.5, 46.8, 41.9]
    }
    
    df = pd.DataFrame(data)
    sample_file = 'sample_manufacturing_data_dirty.xlsx'
    df.to_excel(sample_file, index=False, engine='openpyxl')
    
    print("\n" + "="*60)
    print("SAMPLE DIRTY DATA CREATED")
    print("="*60)
    print(f"\nCreated: {sample_file}")
    print("\nData Quality Issues Included:")
    print("  ✗ Extra whitespace in column names and values")
    print("  ✗ Duplicate rows (Part ID P001)")
    print("  ✗ Missing values (Part ID, Production Date, Operator Name)")
    print("  ✗ Inconsistent date formats")
    print("  ✗ Outlier data (Defect Count: 15, Cycle Time: 120.0)")
    print("  ✗ Inconsistent spacing in text fields")
    print("="*60)
    
    return sample_file


if __name__ == "__main__":
    print("\n" + "🔧 EXCEL DATA CLEANSING FOR MANUFACTURING QUALITY CONTROL 🔧\n")
    
    sample_file = create_sample_manufacturing_data()
    
    print("\n\nPROCEEDING WITH DATA CLEANSING...")
    input("\nPress Enter to start cleansing the sample data...")
    
    cleansed_df = cleanse_excel_data(
        input_file=sample_file,
        output_file='sample_manufacturing_data_clean.xlsx'
    )
    
    print("\n\n📊 CLEANSED DATA PREVIEW:")
    print(cleansed_df.to_string())
    
    print("\n\n✅ SUCCESS! Your data is now clean and ready for analysis.")
    print("\nNext Steps:")
    print("  1. Review the cleansed file: sample_manufacturing_data_clean.xlsx")
    print("  2. Use this script with your own Excel files")
    print("  3. Integrate with your manufacturing quality control pipeline")
    print("\n💡 TIP: Customize the cleansing rules based on your specific data needs!")
