#!/usr/bin/env python3
"""
Unicode Grid Solver for Google Docs
Extracts character coordinates and displays the secret message
"""

import requests
from bs4 import BeautifulSoup
import re
import sys

def fetch_and_parse_document(url):
    """Fetch document and extract Unicode character data"""
    # Get document content
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    # Parse HTML and extract text
    soup = BeautifulSoup(response.text, 'html.parser')
    for element in soup(["script", "style", "meta", "link", "title"]):
        element.decompose()
    
    text = soup.get_text()
    
    # Find the data section after "y-coordinate"
    coord_index = text.find('y-coordinate')
    if coord_index == -1:
        raise ValueError("Could not find coordinate data in document")
    
    data_section = text[coord_index + len('y-coordinate'):]
    
    # Extract character entries using regex pattern
    # Pattern: digits + unicode_char + digits (repeated)
    entries = []
    
    # Use regex to find all patterns of: number + non-digit + number
    pattern = r'(\d+)([^\d])(\d+)'
    matches = re.findall(pattern, data_section)
    
    for x_str, char, y_str in matches:
        try:
            x, y = int(x_str), int(y_str)
            entries.append((char, x, y))
        except ValueError:
            continue
    
    return entries

def create_grid(entries):
    """Create 2D grid from character entries"""
    if not entries:
        return []
    
    # Find grid dimensions
    max_x = max(entry[1] for entry in entries)
    max_y = max(entry[2] for entry in entries)
    
    # Create grid filled with spaces
    grid = [[' ' for _ in range(max_x + 1)] for _ in range(max_y + 1)]
    
    # Place characters in grid
    for char, x, y in entries:
        grid[y][x] = char
    
    return grid

def display_solution(url):
    """Main function to solve and display the Unicode grid"""
    print(f"Solving Unicode grid from: {url}")
    
    # Extract character data
    entries = fetch_and_parse_document(url)
    print(f"Found {len(entries)} character entries")
    
    if not entries:
        print("No character data found!")
        return
    
    # Create and display grid
    grid = create_grid(entries)
    
    print(f"\nGrid dimensions: {len(grid[0])} × {len(grid)}")
    print("\nSecret Message:")
    print("=" * len(grid[0]))
    
    for row in grid:
        print(''.join(row))
    
    print("=" * len(grid[0]))
    
    # Show some sample entries for verification
    print(f"\nSample entries (first 10):")
    for i, (char, x, y) in enumerate(entries[:10]):
        print(f"  '{char}' at ({x}, {y})")
    
    if len(entries) > 10:
        print(f"  ... and {len(entries) - 10} more")

if __name__ == "__main__":
    url = "https://docs.google.com/document/d/e/2PACX-1vTER-wL5E8YC9pxDx43gk8eIds59GtUUk4nJo_ZWagbnrH0NFvMXIw6VWFLpf5tWTZIT9P9oLIoFJ6A/pub"
    display_solution(url)