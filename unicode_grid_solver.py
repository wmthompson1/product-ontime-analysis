#!/usr/bin/env python3
"""
Complete Unicode Grid Solver for Google Docs
Handles various document formats and extracts secret messages from character grids.
"""

import requests
import re
import sys
import csv
from io import StringIO

def fetch_google_doc(url):
    """Retrieve Google Doc content using the most reliable method"""
    
    # Extract document ID and try multiple export formats
    if '/document/d/' in url:
        doc_id = url.split('/document/d/')[1].split('/')[0]
        
        # Try plain text export first (most reliable)
        try:
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            response = requests.get(export_url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            pass
        
        # Try HTML export as fallback
        try:
            html_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
            response = requests.get(html_url, timeout=10)
            response.raise_for_status()
            
            # Basic HTML text extraction
            import html
            text = html.unescape(response.text)
            # Remove HTML tags
            clean_text = re.sub(r'<[^>]+>', '\n', text)
            return clean_text
        except requests.RequestException:
            pass
    
    # Direct URL access as last resort
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Cannot access document: {e}")

def parse_unicode_data(text):
    """Parse document text to extract Unicode character positions"""
    
    entries = []
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Try different parsing patterns
        entry = None
        
        # Pattern 1: Tab-separated (char\tx\ty)
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                entry = parse_entry_parts(parts[0], parts[1], parts[2])
        
        # Pattern 2: Comma-separated with proper CSV handling
        elif ',' in line:
            try:
                reader = csv.reader(StringIO(line))
                parts = next(reader)
                if len(parts) >= 3:
                    entry = parse_entry_parts(parts[0], parts[1], parts[2])
            except:
                parts = line.split(',')
                if len(parts) >= 3:
                    entry = parse_entry_parts(parts[0], parts[1], parts[2])
        
        # Pattern 3: Space-separated (char x y)
        else:
            match = re.match(r'^(.+?)\s+(\d+)\s+(\d+)$', line)
            if match:
                entry = parse_entry_parts(match.group(1), match.group(2), match.group(3))
        
        # Pattern 4: Unicode codepoint format (U+XXXX x y)
        if not entry:
            unicode_match = re.match(r'^U\+([0-9A-Fa-f]+)\s+(\d+)\s+(\d+)$', line)
            if unicode_match:
                try:
                    codepoint = int(unicode_match.group(1), 16)
                    char = chr(codepoint)
                    x = int(unicode_match.group(2))
                    y = int(unicode_match.group(3))
                    entry = (char, x, y)
                except ValueError:
                    pass
        
        if entry:
            entries.append(entry)
    
    return entries

def parse_entry_parts(char_part, x_part, y_part):
    """Parse individual components of a character entry"""
    
    try:
        # Clean and process character
        char = char_part.strip()
        
        # Handle quoted characters
        if (char.startswith('"') and char.endswith('"')) or (char.startswith("'") and char.endswith("'")):
            char = char[1:-1]
        
        # Handle Unicode escape sequences
        if char.startswith('\\u'):
            char = char.encode().decode('unicode_escape')
        elif char.startswith('\\x'):
            char = char.encode().decode('unicode_escape')
        
        # Parse coordinates
        x = int(x_part.strip())
        y = int(y_part.strip())
        
        return (char, x, y)
    
    except (ValueError, TypeError):
        return None

def build_grid(character_data):
    """Build 2D character grid from parsed data"""
    
    if not character_data:
        return []
    
    # Calculate grid boundaries
    x_coords = [entry[1] for entry in character_data]
    y_coords = [entry[2] for entry in character_data]
    
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    
    # Create grid with proper offsets for negative coordinates
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Place characters
    for char, x, y in character_data:
        grid_x = x - min_x
        grid_y = y - min_y
        grid[grid_y][grid_x] = char
    
    return grid

def display_result(grid):
    """Display the final grid and extract the secret message"""
    
    if not grid:
        print("No grid generated")
        return
    
    print(f"Grid size: {len(grid[0])} × {len(grid)}")
    print()
    
    # Display grid with borders
    border = '+' + '-' * len(grid[0]) + '+'
    print(border)
    for row in grid:
        print('|' + ''.join(row) + '|')
    print(border)
    
    print("\nSecret message:")
    for row in grid:
        print(''.join(row))

def solve_puzzle(doc_url):
    """Main function to solve the Unicode grid puzzle"""
    
    print(f"Fetching document from: {doc_url}")
    
    try:
        # Get document content
        content = fetch_google_doc(doc_url)
        print(f"Retrieved {len(content)} characters")
        
        # Parse character data
        character_data = parse_unicode_data(content)
        
        if not character_data:
            print("No valid character data found in document")
            print("\nDocument preview:")
            print(content[:500] + "..." if len(content) > 500 else content)
            return
        
        print(f"Found {len(character_data)} character entries")
        
        # Build and display grid
        grid = build_grid(character_data)
        display_result(grid)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python unicode_grid_solver.py <google_doc_url>")
        print("Example: python unicode_grid_solver.py 'https://docs.google.com/document/d/your_doc_id'")
        
        # Demonstrate with test data
        print("\nDemo with sample data:")
        test_data = [('H', 0, 0), ('E', 1, 0), ('L', 2, 0), ('L', 3, 0), ('O', 4, 0)]
        demo_grid = build_grid(test_data)
        display_result(demo_grid)
    else:
        solve_puzzle(sys.argv[1])