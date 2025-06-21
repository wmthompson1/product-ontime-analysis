#!/usr/bin/env python3
"""
Complete Unicode Grid Message Solver
Extracts and displays the secret message from Google Doc Unicode grids
"""

import requests
from bs4 import BeautifulSoup
import re

def solve_unicode_message(url):
    """Extract and display the complete secret message"""
    
    # Fetch and parse document
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    for element in soup(["script", "style", "meta", "link", "title"]):
        element.decompose()
    
    text = soup.get_text()
    coord_index = text.find('y-coordinate')
    data_section = text[coord_index + len('y-coordinate'):]
    
    # Extract character coordinates using regex
    pattern = r'(\d+)([^\d])(\d+)'
    matches = re.findall(pattern, data_section)
    
    entries = []
    for x_str, char, y_str in matches:
        try:
            entries.append((char, int(x_str), int(y_str)))
        except ValueError:
            continue
    
    print(f"Processing {len(entries)} characters from the document...")
    
    # Create the complete grid
    max_x = max(x for _, x, _ in entries)
    max_y = max(y for _, _, y in entries)
    
    grid = [[' ' for _ in range(max_x + 1)] for _ in range(max_y + 1)]
    
    for char, x, y in entries:
        grid[y][x] = char
    
    # Find all rows that contain characters
    rows_with_chars = set()
    for _, _, y in entries:
        rows_with_chars.add(y)
    
    rows_with_chars = sorted(rows_with_chars)
    
    # Group rows into letter blocks (consecutive or near-consecutive rows)
    letter_blocks = []
    current_block = [rows_with_chars[0]]
    
    for i in range(1, len(rows_with_chars)):
        if rows_with_chars[i] - current_block[-1] <= 5:  # Rows within 5 units are part of same letter
            current_block.append(rows_with_chars[i])
        else:
            if len(current_block) >= 2:  # Valid letter needs at least 2 rows
                letter_blocks.append(current_block)
            current_block = [rows_with_chars[i]]
    
    # Add final block
    if len(current_block) >= 2:
        letter_blocks.append(current_block)
    
    print(f"Found {len(letter_blocks)} letter blocks")
    
    # Display each letter block
    print("\n" + "="*80)
    print("SECRET MESSAGE LETTERS:")
    print("="*80)
    
    all_letters = []
    
    for i, block in enumerate(letter_blocks):
        min_y = min(block)
        max_y = max(block)
        
        # Find x-range for this letter block
        chars_in_block = [(x, y) for _, x, y in entries if min_y <= y <= max_y]
        if not chars_in_block:
            continue
            
        min_x = min(x for x, y in chars_in_block)
        max_x = max(x for x, y in chars_in_block)
        
        # Extract letter
        letter_grid = []
        for y in range(min_y, max_y + 1):
            row = ''.join(grid[y][min_x:max_x + 1]).rstrip()
            letter_grid.append(row)
        
        # Remove empty lines from top and bottom
        while letter_grid and not letter_grid[0].strip():
            letter_grid.pop(0)
        while letter_grid and not letter_grid[-1].strip():
            letter_grid.pop()
        
        if letter_grid:
            print(f"\nLetter {i+1} (y:{min_y}-{max_y}, x:{min_x}-{max_x}):")
            for row in letter_grid:
                print(f"  {row}")
            
            all_letters.append((min_x, letter_grid))
    
    # Sort letters by x-coordinate to get the message in order
    all_letters.sort(key=lambda x: x[0])
    
    print("\n" + "="*80)
    print("COMPLETE SECRET MESSAGE (left to right):")
    print("="*80)
    
    # Display all letters side by side
    if all_letters:
        max_height = max(len(letter) for _, letter in all_letters)
        
        for row_idx in range(max_height):
            line = ""
            for min_x, letter in all_letters:
                if row_idx < len(letter):
                    line += letter[row_idx].ljust(15)  # Pad each letter to 15 chars width
                else:
                    line += " " * 15
            print(line.rstrip())
    
    print("="*80)
    
    # Also show the raw character data for verification
    print(f"\nCharacter summary:")
    char_types = {}
    for char, x, y in entries:
        char_types[char] = char_types.get(char, 0) + 1
    
    for char, count in sorted(char_types.items()):
        print(f"  '{char}': {count} occurrences")

if __name__ == "__main__":
    url = "https://docs.google.com/document/d/e/2PACX-1vTER-wL5E8YC9pxDx43gk8eIds59GtUUk4nJo_ZWagbnrH0NFvMXIw6VWFLpf5tWTZIT9P9oLIoFJ6A/pub"
    solve_unicode_message(url)