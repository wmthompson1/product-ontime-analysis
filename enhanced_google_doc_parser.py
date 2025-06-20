#!/usr/bin/env python3
"""
Enhanced Google Doc Unicode Grid Parser
Handles multiple document formats and provides robust parsing for Unicode character grids.
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import csv
from io import StringIO

def get_google_doc_content(url):
    """
    Retrieve content from a published Google Doc using multiple strategies
    
    Args:
        url (str): URL of the published Google Doc
        
    Returns:
        str: Document content
    """
    # Strategy 1: Try to get plain text export
    try:
        if '/document/d/' in url:
            doc_id = url.split('/document/d/')[1].split('/')[0]
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            response = requests.get(export_url)
            response.raise_for_status()
            return response.text
    except:
        pass
    
    # Strategy 2: Try CSV export format
    try:
        if '/document/d/' in url:
            doc_id = url.split('/document/d/')[1].split('/')[0]
            csv_url = f"https://docs.google.com/document/d/{doc_id}/export?format=csv"
            response = requests.get(csv_url)
            response.raise_for_status()
            return response.text
    except:
        pass
    
    # Strategy 3: Try HTML format and extract text
    try:
        if '/document/d/' in url:
            doc_id = url.split('/document/d/')[1].split('/')[0]
            html_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
            response = requests.get(html_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text()
    except:
        pass
    
    # Strategy 4: Try the original URL as-is
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        if 'text/html' in response.headers.get('content-type', ''):
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.get_text()
        else:
            return response.text
    except:
        pass
    
    raise Exception("Unable to retrieve document content from any format")

def parse_characters_advanced(text):
    """
    Advanced parsing to extract character data from various formats
    
    Args:
        text (str): Document text content
        
    Returns:
        list: List of tuples (character, x, y)
    """
    characters = []
    lines = text.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):  # Skip empty lines and comments
            continue
        
        # Try multiple parsing strategies
        parsed = None
        
        # Strategy 1: Tab-separated values
        if '\t' in line:
            parts = [part.strip() for part in line.split('\t')]
            if len(parts) >= 3:
                parsed = try_parse_entry(parts[0], parts[1], parts[2])
        
        # Strategy 2: Comma-separated values
        if not parsed and ',' in line:
            try:
                # Use CSV reader to handle quoted values properly
                csv_reader = csv.reader(StringIO(line))
                parts = next(csv_reader)
                if len(parts) >= 3:
                    parsed = try_parse_entry(parts[0].strip(), parts[1].strip(), parts[2].strip())
            except:
                # Fallback to simple split
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 3:
                    parsed = try_parse_entry(parts[0], parts[1], parts[2])
        
        # Strategy 3: Space-separated values (be careful with multi-character entries)
        if not parsed:
            # Look for pattern: anything followed by two integers
            match = re.match(r'^(.+?)\s+(\d+)\s+(\d+)$', line)
            if match:
                parsed = try_parse_entry(match.group(1), match.group(2), match.group(3))
        
        # Strategy 4: Unicode notation (U+XXXX format)
        if not parsed:
            unicode_match = re.match(r'^U\+([0-9A-Fa-f]+)\s+(\d+)\s+(\d+)$', line)
            if unicode_match:
                try:
                    codepoint = int(unicode_match.group(1), 16)
                    char = chr(codepoint)
                    x = int(unicode_match.group(2))
                    y = int(unicode_match.group(3))
                    parsed = (char, x, y)
                except ValueError:
                    pass
        
        # Strategy 5: Hexadecimal character codes
        if not parsed:
            hex_match = re.match(r'^(?:0x)?([0-9A-Fa-f]+)\s+(\d+)\s+(\d+)$', line)
            if hex_match:
                try:
                    codepoint = int(hex_match.group(1), 16)
                    char = chr(codepoint)
                    x = int(hex_match.group(2))
                    y = int(hex_match.group(3))
                    parsed = (char, x, y)
                except ValueError:
                    pass
        
        if parsed:
            characters.append(parsed)
        else:
            # Debug: show unparsed lines
            if len(line) > 0 and not line.isspace():
                print(f"Warning: Could not parse line {line_num}: '{line}'")
    
    return characters

def try_parse_entry(char_str, x_str, y_str):
    """
    Try to parse a character entry from string components
    
    Args:
        char_str (str): Character string
        x_str (str): X coordinate string
        y_str (str): Y coordinate string
        
    Returns:
        tuple or None: (character, x, y) if successful, None otherwise
    """
    try:
        # Handle different character representations
        char = char_str.strip()
        
        # Handle Unicode escape sequences
        if char.startswith('\\u'):
            char = char.encode().decode('unicode_escape')
        elif char.startswith('\\x'):
            char = char.encode().decode('unicode_escape')
        elif char.startswith('&#'):
            # HTML entity
            char_code = int(char[2:-1]) if char.endswith(';') else int(char[2:])
            char = chr(char_code)
        
        # Handle quoted characters
        if (char.startswith('"') and char.endswith('"')) or (char.startswith("'") and char.endswith("'")):
            char = char[1:-1]
        
        # Parse coordinates
        x = int(x_str.strip())
        y = int(y_str.strip())
        
        return (char, x, y)
    
    except (ValueError, TypeError):
        return None

def create_character_grid(characters):
    """
    Create a 2D grid from character data with error handling
    
    Args:
        characters (list): List of tuples (character, x, y)
        
    Returns:
        list: 2D grid of characters
    """
    if not characters:
        return []
    
    # Find grid dimensions
    max_x = max(char[1] for char in characters)
    max_y = max(char[2] for char in characters)
    min_x = min(char[1] for char in characters)
    min_y = min(char[2] for char in characters)
    
    # Adjust for negative coordinates
    offset_x = abs(min_x) if min_x < 0 else 0
    offset_y = abs(min_y) if min_y < 0 else 0
    
    width = max_x + offset_x + 1
    height = max_y + offset_y + 1
    
    # Create grid filled with spaces
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Place characters in grid
    for char, x, y in characters:
        adjusted_x = x + offset_x
        adjusted_y = y + offset_y
        if 0 <= adjusted_x < width and 0 <= adjusted_y < height:
            grid[adjusted_y][adjusted_x] = char
    
    return grid

def display_grid(grid):
    """
    Display the character grid with formatting
    
    Args:
        grid (list): 2D character grid
    """
    if not grid:
        print("No grid data to display")
        return
    
    print(f"\nGrid dimensions: {len(grid[0])} x {len(grid)}")
    print("=" * (len(grid[0]) + 4))
    
    for row in grid:
        print('| ' + ''.join(row) + ' |')
    
    print("=" * (len(grid[0]) + 4))
    
    print("\nSecret message (raw output):")
    for row in grid:
        print(''.join(row))
    
    # Try to extract just the non-space characters as a message
    message_chars = []
    for row in grid:
        for char in row:
            if char != ' ':
                message_chars.append(char)
    
    if message_chars:
        print(f"\nExtracted characters: {''.join(message_chars)}")

def solve_unicode_puzzle(url):
    """
    Main function to solve the Google Doc Unicode puzzle
    
    Args:
        url (str): URL of the published Google Doc
    """
    print(f"Processing Google Doc: {url}")
    
    try:
        # Get document content
        content = get_google_doc_content(url)
        print(f"Retrieved {len(content)} characters")
        
        # Parse character data
        characters = parse_characters_advanced(content)
        
        if not characters:
            print("\nNo character data found. Document preview:")
            print("-" * 50)
            preview = content[:1000] + "..." if len(content) > 1000 else content
            print(preview)
            print("-" * 50)
            return
        
        print(f"\nParsed {len(characters)} character entries:")
        for i, (char, x, y) in enumerate(characters[:10]):  # Show first 10
            print(f"  {i+1}: '{char}' at ({x}, {y})")
        if len(characters) > 10:
            print(f"  ... and {len(characters) - 10} more")
        
        # Create and display grid
        grid = create_character_grid(characters)
        display_grid(grid)
        
    except Exception as e:
        print(f"Error processing document: {e}")
        print("Make sure the Google Doc is published and accessible.")

def test_sample():
    """Test with sample data"""
    print("Testing with sample Unicode data...")
    
    sample_text = """A	0	0
B	1	0
C	2	0
L	0	1
L	1	1
O	2	1
H	0	2
E	1	2
!	2	2"""
    
    characters = parse_characters_advanced(sample_text)
    grid = create_character_grid(characters)
    display_grid(grid)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        solve_unicode_puzzle(url)
    else:
        print("Google Doc Unicode Grid Solver")
        print("Usage: python enhanced_google_doc_parser.py <google_doc_url>")
        print("\nExample: python enhanced_google_doc_parser.py 'https://docs.google.com/document/d/your_doc_id/edit'")
        print("\nRunning test with sample data:")
        test_sample()