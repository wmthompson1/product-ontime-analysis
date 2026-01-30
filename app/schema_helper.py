"""
CSV to JSON Schema Helper

Transforms CSV samples into JSON schema format for the Combined Pipeline.
Infers data types from column names and sample values.
"""

import csv
import json
import re
from io import StringIO
from typing import Dict, List, Tuple
from datetime import datetime


def infer_type_from_name(column_name: str) -> str:
    """
    Infer data type from column name patterns.
    """
    name_lower = column_name.lower().strip()
    
    date_patterns = ['date', 'time', 'timestamp', 'created', 'updated', 'modified', 'expires', 'due', 'start', 'end']
    for pattern in date_patterns:
        if pattern in name_lower:
            return 'date'
    
    numeric_patterns = ['num', 'count', 'qty', 'quantity', 'amount', 'price', 'cost', 'rate', 'total', 'sum', 
                        'received', 'shipped', 'ordered', 'balance', 'weight', 'height', 'width', 'length',
                        'units', 'pieces', 'defects', 'late', 'early', 'avg', 'min', 'max', 'id']
    for pattern in numeric_patterns:
        if pattern in name_lower:
            if 'id' in name_lower and name_lower.endswith('id'):
                continue
            return 'numeric'
    
    return 'text'


def infer_type_from_value(value: str) -> str:
    """
    Infer data type from sample value.
    """
    if not value or value.strip() == '':
        return 'text'
    
    value = value.strip()
    
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}',
        r'^\d{2}/\d{2}/\d{4}',
        r'^\d{2}-\d{2}-\d{4}',
        r'^\d{4}/\d{2}/\d{2}',
    ]
    for pattern in date_patterns:
        if re.match(pattern, value):
            return 'date'
    
    try:
        cleaned = value.replace(',', '').replace('$', '').replace('%', '')
        float(cleaned)
        return 'numeric'
    except ValueError:
        pass
    
    return 'text'


def csv_to_schema(csv_content: str) -> Tuple[Dict[str, str], List[str]]:
    """
    Convert CSV sample to JSON schema.
    
    Args:
        csv_content: CSV string with header row and optionally one data row
        
    Returns:
        Tuple of (schema_dict, column_names)
    """
    reader = csv.reader(StringIO(csv_content.strip()))
    rows = list(reader)
    
    if not rows:
        return {}, []
    
    headers = [h.strip() for h in rows[0]]
    sample_values = rows[1] if len(rows) > 1 else ['' for _ in headers]
    
    if len(sample_values) < len(headers):
        sample_values.extend([''] * (len(headers) - len(sample_values)))
    
    schema = {}
    for i, header in enumerate(headers):
        if not header:
            continue
        
        name_type = infer_type_from_name(header)
        value_type = infer_type_from_value(sample_values[i]) if i < len(sample_values) else 'text'
        
        if name_type == 'date' or value_type == 'date':
            schema[header] = 'date'
        elif name_type == 'numeric' or value_type == 'numeric':
            schema[header] = 'numeric'
        else:
            schema[header] = 'text'
    
    return schema, headers


def schema_to_json(schema: Dict[str, str], indent: int = 2) -> str:
    """
    Convert schema dict to formatted JSON string.
    """
    return json.dumps(schema, indent=indent)


def process_csv_for_block_schema(csv_content: str, block_type: str = 'tabular') -> Dict:
    """
    Process CSV content and return schema with metadata.
    
    Args:
        csv_content: CSV string
        block_type: 'freeform' or 'tabular'
        
    Returns:
        Dict with schema, json_output, columns, and type_summary
    """
    schema, columns = csv_to_schema(csv_content)
    
    type_counts = {'text': 0, 'numeric': 0, 'date': 0}
    for dtype in schema.values():
        type_counts[dtype] = type_counts.get(dtype, 0) + 1
    
    return {
        'schema': schema,
        'json_output': schema_to_json(schema),
        'columns': columns,
        'column_count': len(columns),
        'type_summary': type_counts,
        'block_type': block_type
    }
