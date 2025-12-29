# Python CSV Files: Complete 4-Page Guide

## Page 1: Introduction and Basic Reading

### What are CSV Files?

CSV (Comma-Separated Values) files are plain text files that store tabular data. Each line represents a row, and values are separated by commas (or other delimiters like semicolons or tabs).

**Example CSV structure:**
```
name,age,city,salary
Alice,25,New York,50000
Bob,30,London,60000
Charlie,35,Tokyo,70000
```

### Python's CSV Module

Python's built-in `csv` module provides functionality for reading and writing CSV files efficiently and safely.

```python
import csv
```

### Basic CSV Reading

**Method 1: Using csv.reader()**
```python
import csv

# Reading a CSV file
with open('employees.csv', 'r') as file:
    csv_reader = csv.reader(file)
    
    # Read header row
    header = next(csv_reader)
    print(f"Headers: {header}")
    
    # Read data rows
    for row in csv_reader:
        print(row)

# Output:
# Headers: ['name', 'age', 'city', 'salary']
# ['Alice', '25', 'New York', '50000']
# ['Bob', '30', 'London', '60000']
# ['Charlie', '35', 'Tokyo', '70000']
```

**Method 2: Using csv.DictReader()**
```python
import csv

with open('employees.csv', 'r') as file:
    csv_reader = csv.DictReader(file)
    
    for row in csv_reader:
        print(f"Name: {row['name']}, Age: {row['age']}, City: {row['city']}")

# Output:
# Name: Alice, Age: 25, City: New York
# Name: Bob, Age: 30, City: London
# Name: Charlie, Age: 35, City: Tokyo
```

### Reading All Data at Once

```python
import csv

# Read all rows into a list
def read_csv_to_list(filename):
    data = []
    with open(filename, 'r') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)  # Skip header
        for row in csv_reader:
            data.append(row)
    return header, data

# Read all rows as dictionaries
def read_csv_to_dict_list(filename):
    data = []
    with open(filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(dict(row))
    return data

# Usage
header, rows = read_csv_to_list('employees.csv')
dict_data = read_csv_to_dict_list('employees.csv')
```

### Handling Different Delimiters

```python
import csv

# Reading tab-separated values
with open('data.tsv', 'r') as file:
    csv_reader = csv.reader(file, delimiter='\t')
    for row in csv_reader:
        print(row)

# Reading semicolon-separated values
with open('data.csv', 'r') as file:
    csv_reader = csv.reader(file, delimiter=';')
    for row in csv_reader:
        print(row)

# Reading with custom quote character
with open('data.csv', 'r') as file:
    csv_reader = csv.reader(file, quotechar="'")
    for row in csv_reader:
        print(row)
```

### Error Handling

```python
import csv
import os

def safe_read_csv(filename):
    try:
        if not os.path.exists(filename):
            print(f"File {filename} not found")
            return []
        
        data = []
        with open(filename, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    data.append(dict(row))
                except Exception as e:
                    print(f"Error reading row {row_num}: {e}")
        
        return data
    
    except PermissionError:
        print(f"Permission denied accessing {filename}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return []
```

---

## Page 2: Basic Writing and Data Manipulation

### Basic CSV Writing

**Method 1: Using csv.writer()**
```python
import csv

# Writing data to CSV
data = [
    ['name', 'age', 'city', 'salary'],
    ['Alice', 25, 'New York', 50000],
    ['Bob', 30, 'London', 60000],
    ['Charlie', 35, 'Tokyo', 70000]
]

with open('output.csv', 'w', newline='') as file:
    csv_writer = csv.writer(file)
    csv_writer.writerows(data)

# Writing row by row
with open('output.csv', 'w', newline='') as file:
    csv_writer = csv.writer(file)
    
    # Write header
    csv_writer.writerow(['name', 'age', 'city', 'salary'])
    
    # Write data rows
    csv_writer.writerow(['Alice', 25, 'New York', 50000])
    csv_writer.writerow(['Bob', 30, 'London', 60000])
```

**Method 2: Using csv.DictWriter()**
```python
import csv

# Data as list of dictionaries
employees = [
    {'name': 'Alice', 'age': 25, 'city': 'New York', 'salary': 50000},
    {'name': 'Bob', 'age': 30, 'city': 'London', 'salary': 60000},
    {'name': 'Charlie', 'age': 35, 'city': 'Tokyo', 'salary': 70000}
]

fieldnames = ['name', 'age', 'city', 'salary']

with open('employees.csv', 'w', newline='') as file:
    csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
    
    # Write header
    csv_writer.writeheader()
    
    # Write all rows
    csv_writer.writerows(employees)
    
    # Or write one row at a time
    # for employee in employees:
    #     csv_writer.writerow(employee)
```

### Appending to Existing CSV Files

```python
import csv

# Append new data to existing file
new_employee = {'name': 'Diana', 'age': 28, 'city': 'Paris', 'salary': 55000}

with open('employees.csv', 'a', newline='') as file:
    fieldnames = ['name', 'age', 'city', 'salary']
    csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
    csv_writer.writerow(new_employee)

# Append multiple rows
new_employees = [
    {'name': 'Eve', 'age': 32, 'city': 'Berlin', 'salary': 65000},
    {'name': 'Frank', 'age': 29, 'city': 'Sydney', 'salary': 58000}
]

with open('employees.csv', 'a', newline='') as file:
    fieldnames = ['name', 'age', 'city', 'salary']
    csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
    csv_writer.writerows(new_employees)
```

### Data Processing and Transformation

```python
import csv

def process_employee_data(input_file, output_file):
    """Read CSV, process data, and write to new file"""
    processed_data = []
    
    with open(input_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            # Convert salary to integer and add bonus
            salary = int(row['salary'])
            bonus = salary * 0.1
            
            processed_row = {
                'name': row['name'].upper(),
                'age': int(row['age']),
                'city': row['city'],
                'salary': salary,
                'bonus': round(bonus, 2),
                'total_compensation': salary + bonus
            }
            processed_data.append(processed_row)
    
    # Write processed data
    fieldnames = ['name', 'age', 'city', 'salary', 'bonus', 'total_compensation']
    
    with open(output_file, 'w', newline='') as file:
        csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(processed_data)

# Usage
process_employee_data('employees.csv', 'processed_employees.csv')
```

### Filtering and Sorting Data

```python
import csv

def filter_and_sort_csv(input_file, output_file, min_salary=55000):
    """Filter employees by salary and sort by age"""
    
    # Read and filter data
    filtered_data = []
    with open(input_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if int(row['salary']) >= min_salary:
                row['age'] = int(row['age'])
                row['salary'] = int(row['salary'])
                filtered_data.append(row)
    
    # Sort by age
    filtered_data.sort(key=lambda x: x['age'])
    
    # Write sorted data
    if filtered_data:
        fieldnames = filtered_data[0].keys()
        with open(output_file, 'w', newline='') as file:
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(filtered_data)

# Usage
filter_and_sort_csv('employees.csv', 'high_earners.csv', min_salary=60000)
```

### Working with Different Formats

```python
import csv

# Write with different delimiter
data = [['A', 'B', 'C'], [1, 2, 3], [4, 5, 6]]

with open('data.tsv', 'w', newline='') as file:
    csv_writer = csv.writer(file, delimiter='\t')
    csv_writer.writerows(data)

# Write with custom quoting
with open('data.csv', 'w', newline='') as file:
    csv_writer = csv.writer(file, quoting=csv.QUOTE_ALL)
    csv_writer.writerows(data)

# Write with custom quote character
with open('data.csv', 'w', newline='') as file:
    csv_writer = csv.writer(file, quotechar="'")
    csv_writer.writerows(data)
```

---

## Page 3: Advanced Techniques and Error Handling

### Handling Large CSV Files

**Reading Large Files in Chunks**
```python
import csv

def process_large_csv(filename, chunk_size=1000):
    """Process large CSV files in chunks to manage memory"""
    
    with open(filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        chunk = []
        for row_num, row in enumerate(csv_reader, 1):
            chunk.append(row)
            
            # Process chunk when it reaches the specified size
            if len(chunk) >= chunk_size:
                process_chunk(chunk)
                chunk = []  # Reset chunk
                print(f"Processed {row_num} rows...")
        
        # Process remaining rows
        if chunk:
            process_chunk(chunk)
            print(f"Finished processing {row_num} total rows")

def process_chunk(chunk):
    """Process a chunk of data"""
    # Example: Calculate average salary for this chunk
    if chunk:
        salaries = [int(row['salary']) for row in chunk if row['salary'].isdigit()]
        if salaries:
            avg_salary = sum(salaries) / len(salaries)
            print(f"Average salary in this chunk: ${avg_salary:.2f}")
```

### Data Validation and Cleaning

```python
import csv
import re
from datetime import datetime

def validate_and_clean_csv(input_file, output_file, error_file):
    """Validate CSV data and separate good from bad records"""
    
    valid_records = []
    error_records = []
    
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_phone(phone):
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        return len(digits) == 10
    
    with open(input_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row_num, row in enumerate(csv_reader, start=2):
            errors = []
            cleaned_row = {}
            
            # Validate and clean each field
            try:
                # Name validation
                name = row.get('name', '').strip()
                if not name:
                    errors.append("Missing name")
                cleaned_row['name'] = name.title()
                
                # Age validation
                age_str = row.get('age', '').strip()
                try:
                    age = int(age_str)
                    if age < 0 or age > 120:
                        errors.append("Invalid age range")
                    cleaned_row['age'] = age
                except ValueError:
                    errors.append("Invalid age format")
                    cleaned_row['age'] = None
                
                # Email validation
                email = row.get('email', '').strip().lower()
                if not validate_email(email):
                    errors.append("Invalid email format")
                cleaned_row['email'] = email
                
                # Phone validation
                phone = row.get('phone', '').strip()
                if not validate_phone(phone):
                    errors.append("Invalid phone format")
                else:
                    # Format phone number
                    digits = re.sub(r'\D', '', phone)
                    cleaned_row['phone'] = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                
                # If no errors, add to valid records
                if not errors:
                    valid_records.append(cleaned_row)
                else:
                    error_record = row.copy()
                    error_record['row_number'] = row_num
                    error_record['errors'] = '; '.join(errors)
                    error_records.append(error_record)
                    
            except Exception as e:
                error_record = row.copy()
                error_record['row_number'] = row_num
                error_record['errors'] = f"Processing error: {e}"
                error_records.append(error_record)
    
    # Write valid records
    if valid_records:
        with open(output_file, 'w', newline='') as file:
            fieldnames = valid_records[0].keys()
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(valid_records)
    
    # Write error records
    if error_records:
        with open(error_file, 'w', newline='') as file:
            all_fieldnames = set()
            for record in error_records:
                all_fieldnames.update(record.keys())
            
            csv_writer = csv.DictWriter(file, fieldnames=list(all_fieldnames))
            csv_writer.writeheader()
            csv_writer.writerows(error_records)
    
    return len(valid_records), len(error_records)

# Usage
valid_count, error_count = validate_and_clean_csv(
    'raw_data.csv', 
    'clean_data.csv', 
    'errors.csv'
)
print(f"Processed: {valid_count} valid, {error_count} errors")
```

### Working with Different Encodings

```python
import csv
import chardet

def detect_encoding(filename):
    """Detect file encoding"""
    with open(filename, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']

def read_csv_with_encoding(filename, encoding=None):
    """Read CSV with proper encoding handling"""
    
    if encoding is None:
        encoding = detect_encoding(filename)
        print(f"Detected encoding: {encoding}")
    
    try:
        with open(filename, 'r', encoding=encoding) as file:
            csv_reader = csv.DictReader(file)
            return list(csv_reader)
    except UnicodeDecodeError:
        # Fallback encodings
        fallback_encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
        
        for enc in fallback_encodings:
            try:
                with open(filename, 'r', encoding=enc) as file:
                    csv_reader = csv.DictReader(file)
                    print(f"Successfully read with encoding: {enc}")
                    return list(csv_reader)
            except UnicodeDecodeError:
                continue
        
        raise Exception("Could not decode file with any common encoding")

# Usage
data = read_csv_with_encoding('international_data.csv')
```

### Advanced CSV Dialects

```python
import csv

# Define custom CSV dialect
class CustomDialect(csv.Dialect):
    delimiter = '|'
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = '\n'
    quoting = csv.QUOTE_MINIMAL

# Register the dialect
csv.register_dialect('custom', CustomDialect)

# Use custom dialect
with open('custom_format.csv', 'r') as file:
    csv_reader = csv.reader(file, dialect='custom')
    for row in csv_reader:
        print(row)

# Or specify dialect parameters directly
with open('data.csv', 'r') as file:
    csv_reader = csv.reader(
        file,
        delimiter='|',
        quotechar='"',
        skipinitialspace=True
    )
    for row in csv_reader:
        print(row)
```

### Memory-Efficient CSV Processing

```python
import csv
from collections import defaultdict

def analyze_csv_memory_efficient(filename):
    """Analyze large CSV files without loading all data into memory"""
    
    stats = {
        'total_rows': 0,
        'column_stats': defaultdict(lambda: {'count': 0, 'sum': 0, 'min': float('inf'), 'max': float('-inf')})
    }
    
    with open(filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            stats['total_rows'] += 1
            
            for column, value in row.items():
                if value.strip():  # Non-empty values
                    try:
                        # Try to convert to number
                        num_value = float(value)
                        col_stats = stats['column_stats'][column]
                        col_stats['count'] += 1
                        col_stats['sum'] += num_value
                        col_stats['min'] = min(col_stats['min'], num_value)
                        col_stats['max'] = max(col_stats['max'], num_value)
                    except ValueError:
                        # Handle non-numeric data
                        pass
    
    # Calculate averages
    for column, col_stats in stats['column_stats'].items():
        if col_stats['count'] > 0:
            col_stats['average'] = col_stats['sum'] / col_stats['count']
    
    return stats

# Usage
stats = analyze_csv_memory_efficient('large_dataset.csv')
print(f"Total rows: {stats['total_rows']}")
for column, col_stats in stats['column_stats'].items():
    print(f"{column}: avg={col_stats.get('average', 'N/A')}, min={col_stats['min']}, max={col_stats['max']}")
```

---

## Page 4: Real-World Applications and Best Practices

### Data Analysis and Reporting

```python
import csv
from collections import defaultdict, Counter
from datetime import datetime

def generate_sales_report(sales_file, output_file):
    """Generate comprehensive sales report from CSV data"""
    
    # Data structures for analysis
    monthly_sales = defaultdict(float)
    product_sales = defaultdict(float)
    salesperson_performance = defaultdict(lambda: {'sales': 0, 'revenue': 0})
    
    with open(sales_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            try:
                # Parse data
                date = datetime.strptime(row['date'], '%Y-%m-%d')
                month_key = date.strftime('%Y-%m')
                product = row['product']
                salesperson = row['salesperson']
                quantity = int(row['quantity'])
                price = float(row['price'])
                revenue = quantity * price
                
                # Aggregate data
                monthly_sales[month_key] += revenue
                product_sales[product] += revenue
                salesperson_performance[salesperson]['sales'] += quantity
                salesperson_performance[salesperson]['revenue'] += revenue
                
            except (ValueError, KeyError) as e:
                print(f"Error processing row: {row}, Error: {e}")
                continue
    
    # Generate report
    report_data = []
    
    # Monthly sales summary
    report_data.append(['MONTHLY SALES SUMMARY'])
    report_data.append(['Month', 'Revenue'])
    for month in sorted(monthly_sales.keys()):
        report_data.append([month, f"${monthly_sales[month]:.2f}"])
    
    report_data.append([])  # Empty row
    
    # Top products
    report_data.append(['TOP PRODUCTS BY REVENUE'])
    report_data.append(['Product', 'Revenue'])
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
    for product, revenue in top_products[:5]:
        report_data.append([product, f"${revenue:.2f}"])
    
    report_data.append([])
    
    # Salesperson performance
    report_data.append(['SALESPERSON PERFORMANCE'])
    report_data.append(['Salesperson', 'Units Sold', 'Revenue'])
    for person, stats in sorted(salesperson_performance.items(), 
                               key=lambda x: x[1]['revenue'], reverse=True):
        report_data.append([
            person, 
            stats['sales'], 
            f"${stats['revenue']:.2f}"
        ])
    
    # Write report
    with open(output_file, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(report_data)
    
    print(f"Report generated: {output_file}")

# Usage
generate_sales_report('sales_data.csv', 'sales_report.csv')
```

### Data Import/Export with Databases

```python
import csv
import sqlite3

def csv_to_database(csv_file, db_file, table_name):
    """Import CSV data into SQLite database"""
    
    # Connect to database
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        # Get column names from CSV header
        columns = csv_reader.fieldnames
        
        # Create table
        column_definitions = ', '.join([f"{col} TEXT" for col in columns])
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"CREATE TABLE {table_name} ({column_definitions})")
        
        # Insert data
        placeholders = ', '.join(['?' for _ in columns])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        
        for row in csv_reader:
            cursor.execute(insert_sql, [row[col] for col in columns])
    
    conn.commit()
    conn.close()
    print(f"Data imported to {db_file}")

def database_to_csv(db_file, table_name, csv_file):
    """Export database table to CSV"""
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Write to CSV
    with open(csv_file, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(columns)  # Header
        csv_writer.writerows(data)    # Data
    
    conn.close()
    print(f"Data exported to {csv_file}")

# Usage
csv_to_database('employees.csv', 'company.db', 'employees')
database_to_csv('company.db', 'employees', 'exported_employees.csv')
```

### Web API Integration

```python
import csv
import requests
import json

def export_to_api(csv_file, api_endpoint, headers=None):
    """Send CSV data to a REST API"""
    
    headers = headers or {'Content-Type': 'application/json'}
    
    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row_num, row in enumerate(csv_reader, 1):
            try:
                # Convert row to JSON
                json_data = json.dumps(row)
                
                # Send to API
                response = requests.post(api_endpoint, data=json_data, headers=headers)
                
                if response.status_code == 201:
                    print(f"Row {row_num} uploaded successfully")
                else:
                    print(f"Row {row_num} failed: {response.status_code}")
                    
            except Exception as e:
                print(f"Error uploading row {row_num}: {e}")

def download_from_api(api_endpoint, csv_file, headers=None):
    """Download data from API and save as CSV"""
    
    try:
        response = requests.get(api_endpoint, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if data and isinstance(data, list):
            # Assume data is list of dictionaries
            fieldnames = data[0].keys()
            
            with open(csv_file, 'w', newline='') as file:
                csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
                csv_writer.writeheader()
                csv_writer.writerows(data)
            
            print(f"Data downloaded to {csv_file}")
        
    except Exception as e:
        print(f"Error downloading data: {e}")
```

### Best Practices Summary

**1. Always use context managers (with statements)**
```python
# Good
with open('file.csv', 'r') as file:
    csv_reader = csv.reader(file)
    # Process data

# Avoid
file = open('file.csv', 'r')  # May not close properly
```

**2. Specify newline='' when writing**
```python
# Correct for Windows compatibility
with open('output.csv', 'w', newline='') as file:
    csv_writer = csv.writer(file)
```

**3. Handle encoding explicitly**
```python
with open('file.csv', 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
```

**4. Use DictReader/DictWriter for labeled data**
```python
# More readable and maintainable
with open('employees.csv', 'r') as file:
    for row in csv.DictReader(file):
        print(f"Name: {row['name']}, Salary: {row['salary']}")
```

**5. Validate and clean data**
```python
def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

# Usage
age = safe_int(row['age'])
```

**6. Process large files in chunks**
```python
# For memory efficiency with large datasets
def process_in_chunks(filename, chunk_size=1000):
    with open(filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        chunk = []
        for row in csv_reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
```

**7. Use proper error handling**
```python
try:
    with open('data.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for row_num, row in enumerate(csv_reader, 1):
            try:
                # Process row
                process_row(row)
            except Exception as e:
                print(f"Error in row {row_num}: {e}")
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")
```

### Performance Tips

1. **Use csv.DictReader for labeled access**
2. **Process data incrementally for large files**
3. **Use appropriate data types during processing**
4. **Consider pandas for complex data analysis**
5. **Use generators for memory efficiency**

The Python CSV module provides robust tools for handling tabular data efficiently and safely across various real-world scenarios.