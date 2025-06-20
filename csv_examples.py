#!/usr/bin/env python3
"""
Comprehensive CSV examples demonstrating reading and writing operations
"""

import csv
import os
from datetime import datetime
import random

def create_sample_data():
    """Create sample CSV files for demonstration"""
    
    # Create employees.csv
    employees = [
        ['name', 'age', 'city', 'salary', 'department'],
        ['Alice Johnson', 28, 'New York', 65000, 'Engineering'],
        ['Bob Smith', 34, 'London', 70000, 'Marketing'],
        ['Charlie Brown', 29, 'Tokyo', 75000, 'Engineering'],
        ['Diana Prince', 31, 'Paris', 68000, 'Sales'],
        ['Eve Davis', 26, 'Berlin', 62000, 'Design']
    ]
    
    with open('employees.csv', 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(employees)
    
    # Create sales.csv
    sales_data = [
        ['date', 'product', 'salesperson', 'quantity', 'price'],
        ['2024-01-15', 'Laptop', 'Alice', 2, 999.99],
        ['2024-01-16', 'Mouse', 'Bob', 5, 25.50],
        ['2024-01-17', 'Keyboard', 'Charlie', 3, 79.99],
        ['2024-01-18', 'Monitor', 'Diana', 1, 299.99],
        ['2024-01-19', 'Laptop', 'Eve', 1, 999.99]
    ]
    
    with open('sales.csv', 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(sales_data)
    
    print("Sample CSV files created: employees.csv, sales.csv")

def demonstrate_reading():
    """Demonstrate different ways to read CSV files"""
    print("\n=== CSV Reading Examples ===")
    
    # Method 1: Basic csv.reader
    print("\n1. Using csv.reader():")
    with open('employees.csv', 'r') as file:
        csv_reader = csv.reader(file)
        header = next(csv_reader)
        print(f"Headers: {header}")
        for i, row in enumerate(csv_reader, 1):
            if i <= 2:  # Show first 2 rows
                print(f"Row {i}: {row}")
    
    # Method 2: csv.DictReader
    print("\n2. Using csv.DictReader():")
    with open('employees.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for i, row in enumerate(csv_reader, 1):
            if i <= 2:
                print(f"Employee {i}: {row['name']}, Age: {row['age']}, Salary: ${row['salary']}")
    
    # Method 3: Reading all data at once
    print("\n3. Reading all data into list:")
    with open('employees.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        all_employees = list(csv_reader)
        print(f"Total employees: {len(all_employees)}")
        print(f"First employee: {all_employees[0]['name']}")

def demonstrate_writing():
    """Demonstrate different ways to write CSV files"""
    print("\n=== CSV Writing Examples ===")
    
    # Method 1: Basic csv.writer
    print("\n1. Using csv.writer():")
    new_employees = [
        ['name', 'age', 'position'],
        ['Frank Miller', 35, 'Manager'],
        ['Grace Lee', 27, 'Developer']
    ]
    
    with open('new_employees.csv', 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(new_employees)
    print("Created new_employees.csv")
    
    # Method 2: csv.DictWriter
    print("\n2. Using csv.DictWriter():")
    projects = [
        {'name': 'Website Redesign', 'budget': 50000, 'duration': '3 months'},
        {'name': 'Mobile App', 'budget': 75000, 'duration': '6 months'},
        {'name': 'Database Migration', 'budget': 30000, 'duration': '2 months'}
    ]
    
    with open('projects.csv', 'w', newline='') as file:
        fieldnames = ['name', 'budget', 'duration']
        csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(projects)
    print("Created projects.csv")

def demonstrate_data_processing():
    """Demonstrate data processing and transformation"""
    print("\n=== Data Processing Examples ===")
    
    # Read, process, and write data
    processed_employees = []
    
    with open('employees.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            # Calculate annual bonus (10% of salary)
            salary = int(row['salary'])
            bonus = salary * 0.10
            
            processed_row = {
                'name': row['name'].upper(),
                'age': int(row['age']),
                'city': row['city'],
                'department': row['department'],
                'salary': salary,
                'bonus': round(bonus, 2),
                'total_compensation': salary + bonus
            }
            processed_employees.append(processed_row)
    
    # Write processed data
    with open('processed_employees.csv', 'w', newline='') as file:
        fieldnames = ['name', 'age', 'city', 'department', 'salary', 'bonus', 'total_compensation']
        csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(processed_employees)
    
    print("Created processed_employees.csv with calculated bonuses")
    
    # Show some statistics
    total_salary = sum(emp['salary'] for emp in processed_employees)
    avg_salary = total_salary / len(processed_employees)
    print(f"Average salary: ${avg_salary:,.2f}")

def demonstrate_filtering():
    """Demonstrate filtering and sorting data"""
    print("\n=== Filtering and Sorting Examples ===")
    
    # Filter high earners (salary > 65000)
    high_earners = []
    
    with open('employees.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if int(row['salary']) > 65000:
                high_earners.append(row)
    
    # Sort by salary (descending)
    high_earners.sort(key=lambda x: int(x['salary']), reverse=True)
    
    # Write filtered data
    with open('high_earners.csv', 'w', newline='') as file:
        if high_earners:
            fieldnames = high_earners[0].keys()
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(high_earners)
    
    print(f"Created high_earners.csv with {len(high_earners)} employees")
    for emp in high_earners:
        print(f"  {emp['name']}: ${emp['salary']}")

def demonstrate_aggregation():
    """Demonstrate data aggregation"""
    print("\n=== Data Aggregation Examples ===")
    
    # Group employees by department
    departments = {}
    
    with open('employees.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            dept = row['department']
            if dept not in departments:
                departments[dept] = {'count': 0, 'total_salary': 0, 'employees': []}
            
            departments[dept]['count'] += 1
            departments[dept]['total_salary'] += int(row['salary'])
            departments[dept]['employees'].append(row['name'])
    
    # Create department summary
    dept_summary = []
    for dept, data in departments.items():
        avg_salary = data['total_salary'] / data['count']
        dept_summary.append({
            'department': dept,
            'employee_count': data['count'],
            'total_salary': data['total_salary'],
            'average_salary': round(avg_salary, 2),
            'employees': '; '.join(data['employees'])
        })
    
    # Write summary
    with open('department_summary.csv', 'w', newline='') as file:
        fieldnames = ['department', 'employee_count', 'total_salary', 'average_salary', 'employees']
        csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(dept_summary)
    
    print("Created department_summary.csv")
    for dept in dept_summary:
        print(f"  {dept['department']}: {dept['employee_count']} employees, avg salary: ${dept['average_salary']}")

def demonstrate_error_handling():
    """Demonstrate proper error handling"""
    print("\n=== Error Handling Examples ===")
    
    def safe_read_csv(filename):
        try:
            data = []
            with open(filename, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        # Validate data
                        if not row.get('name', '').strip():
                            print(f"Warning: Empty name in row {row_num}")
                            continue
                        
                        # Convert numeric fields safely
                        try:
                            row['age'] = int(row['age'])
                            row['salary'] = int(row['salary'])
                        except ValueError as e:
                            print(f"Warning: Invalid numeric data in row {row_num}: {e}")
                            continue
                        
                        data.append(row)
                        
                    except Exception as e:
                        print(f"Error processing row {row_num}: {e}")
                        continue
            
            return data
            
        except FileNotFoundError:
            print(f"Error: File {filename} not found")
            return []
        except PermissionError:
            print(f"Error: Permission denied accessing {filename}")
            return []
        except Exception as e:
            print(f"Unexpected error reading {filename}: {e}")
            return []
    
    # Test with existing file
    data = safe_read_csv('employees.csv')
    print(f"Successfully read {len(data)} valid records")
    
    # Test with non-existent file
    data = safe_read_csv('nonexistent.csv')

def cleanup_files():
    """Clean up created files"""
    files_to_remove = [
        'employees.csv', 'sales.csv', 'new_employees.csv', 'projects.csv',
        'processed_employees.csv', 'high_earners.csv', 'department_summary.csv'
    ]
    
    removed_count = 0
    for filename in files_to_remove:
        try:
            if os.path.exists(filename):
                os.remove(filename)
                removed_count += 1
        except Exception as e:
            print(f"Could not remove {filename}: {e}")
    
    print(f"\nCleaned up {removed_count} temporary files")

def main():
    """Run all CSV demonstrations"""
    print("Python CSV File Operations - Comprehensive Examples")
    print("=" * 50)
    
    # Create sample data
    create_sample_data()
    
    # Run demonstrations
    demonstrate_reading()
    demonstrate_writing()
    demonstrate_data_processing()
    demonstrate_filtering()
    demonstrate_aggregation()
    demonstrate_error_handling()
    
    # Clean up
    print("\n" + "=" * 50)
    cleanup_files()
    
    print("\nAll CSV examples completed successfully!")

if __name__ == "__main__":
    main()