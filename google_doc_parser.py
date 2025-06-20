#!/usr/bin/env python3
"""
Google Doc Unicode Grid Parser
Retrieves data from a published Google Doc containing Unicode characters and their grid positions,
then displays the characters as a 2D grid forming a secret message.
"""

import requests
from bs4 import BeautifulSoup
import re
import sys

def get_google_doc_text(url):
    """
    Retrieve the text content from a published Google Doc
    
    Args:
        url (str): URL of the published Google Doc
        
    Returns:
        str: Raw text content of the document
    """
    try:
        # Convert Google Doc URL to export format for plain text
        if '/document/d/' in url:
            doc_id = url.split('/document/d/')[1].split('/')[0]
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        else:
            # Try using the URL as-is
            export_url = url
        
        response = requests.get(export_url)
        response.raise_for_status()
        return response.text
    
    except requests.RequestException as e:
        print(f"Error fetching document: {e}")
        return None

def parse_character_data(text):
    """
    Parse the document text to extract character and position data
    
    Args:
        text (str): Raw text from the Google Doc
        
    Returns:
        list: List of tuples (character, x, y) representing the grid data
    """
    characters = []
    
    # Split text into lines and process each line
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for patterns like: "Character\tX\tY" or "Character,X,Y" or various formats
        # We'll try multiple parsing strategies
        
        # Strategy 1: Tab-separated values
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    char = parts[0].strip()
                    x = int(parts[1].strip())
                    y = int(parts[2].strip())
                    characters.append((char, x, y))
                    continue
                except (ValueError, IndexError):
                    pass
        
        # Strategy 2: Comma-separated values
        if ',' in line:
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    char = parts[0].strip()
                    x = int(parts[1].strip())
                    y = int(parts[2].strip())
                    characters.append((char, x, y))
                    continue
                except (ValueError, IndexError):
                    pass
        
        # Strategy 3: Space-separated with regex
        # Look for pattern: character followed by two numbers
        match = re.match(r'^(.+?)\s+(\d+)\s+(\d+)$', line)
        if match:
            try:
                char = match.group(1).strip()
                x = int(match.group(2))
                y = int(match.group(3))
                characters.append((char, x, y))
                continue
            except ValueError:
                pass
        
        # Strategy 4: Look for Unicode character notation
        # Handle cases like "U+0041 5 10" (Unicode codepoint format)
        unicode_match = re.match(r'^U\+([0-9A-Fa-f]+)\s+(\d+)\s+(\d+)$', line)
        if unicode_match:
            try:
                codepoint = int(unicode_match.group(1), 16)
                char = chr(codepoint)
                x = int(unicode_match.group(2))
                y = int(unicode_match.group(3))
                characters.append((char, x, y))
                continue
            except ValueError:
                pass
    
    return characters

def create_grid(characters):
    """
    Create a 2D grid from the character data
    
    Args:
        characters (list): List of tuples (character, x, y)
        
    Returns:
        list: 2D list representing the character grid
    """
    if not characters:
        return []
    
    # Find the dimensions of the grid
    max_x = max(char[1] for char in characters)
    max_y = max(char[2] for char in characters)
    
    # Create grid filled with spaces
    grid = [[' ' for _ in range(max_x + 1)] for _ in range(max_y + 1)]
    
    # Place characters in the grid
    for char, x, y in characters:
        grid[y][x] = char
    
    return grid

def print_grid(grid):
    """
    Print the grid in a readable format
    
    Args:
        grid (list): 2D list representing the character grid
    """
    if not grid:
        print("Empty grid")
        return
    
    print("Grid contents:")
    print("-" * (len(grid[0]) + 2))
    
    for row in grid:
        print('|' + ''.join(row) + '|')
    
    print("-" * (len(grid[0]) + 2))
    
    print("\nSecret message:")
    for row in grid:
        print(''.join(row))

def solve_google_doc_puzzle(url):
    """
    Main function to solve the Google Doc Unicode grid puzzle
    
    Args:
        url (str): URL of the published Google Doc
    """
    print(f"Fetching data from: {url}")
    
    # Get document text
    text = get_google_doc_text(url)
    if text is None:
        print("Failed to retrieve document")
        return
    
    print(f"Retrieved {len(text)} characters of text")
    
    # Parse character data
    characters = parse_character_data(text)
    if not characters:
        print("No character data found in document")
        print("Document content preview:")
        print(text[:500] + "..." if len(text) > 500 else text)
        return
    
    print(f"Parsed {len(characters)} character entries")
    
    # Create and display grid
    grid = create_grid(characters)
    print_grid(grid)

# Example usage and testing
def test_with_sample_data():
    """Test the parser with sample data"""
    print("Testing with sample data...")
    
    sample_data = """A	0	0
B	1	0
C	2	0
D	0	1
E	1	1
F	2	1"""
    
    characters = parse_character_data(sample_data)
    grid = create_grid(characters)
    print_grid(grid)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        solve_google_doc_puzzle(url)
    else:
        print("Usage: python google_doc_parser.py <google_doc_url>")
        print("\nTesting with sample data:")
        test_with_sample_data()