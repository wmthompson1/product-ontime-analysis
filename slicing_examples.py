#!/usr/bin/env python3
"""
Interactive examples of Python list slicing
"""

def demonstrate_basic_slicing():
    print("=== Basic List Slicing ===")
    numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(f"Original list: {numbers}")
    print()
    
    # Basic slicing examples
    examples = [
        ("numbers[2:5]", numbers[2:5], "Elements from index 2 to 4"),
        ("numbers[:3]", numbers[:3], "First 3 elements"), 
        ("numbers[7:]", numbers[7:], "From index 7 to end"),
        ("numbers[-3:]", numbers[-3:], "Last 3 elements"),
        ("numbers[1:-1]", numbers[1:-1], "All except first and last"),
        ("numbers[:]", numbers[:], "Complete copy")
    ]
    
    for code, result, description in examples:
        print(f"{code:<15} → {result} ({description})")
    print()

def demonstrate_step_slicing():
    print("=== Step Slicing ===")
    numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(f"Original list: {numbers}")
    print()
    
    examples = [
        ("numbers[::2]", numbers[::2], "Every 2nd element"),
        ("numbers[1::2]", numbers[1::2], "Every 2nd starting from index 1"),
        ("numbers[::3]", numbers[::3], "Every 3rd element"),
        ("numbers[::-1]", numbers[::-1], "Reverse the list"),
        ("numbers[::-2]", numbers[::-2], "Every 2nd element in reverse"),
        ("numbers[2:8:2]", numbers[2:8:2], "Every 2nd from index 2 to 7")
    ]
    
    for code, result, description in examples:
        print(f"{code:<18} → {result} ({description})")
    print()

def demonstrate_string_slicing():
    print("=== String Slicing ===")
    text = "Hello, World!"
    print(f"Original string: '{text}'")
    print()
    
    examples = [
        ("text[:5]", text[:5], "First 5 characters"),
        ("text[7:]", text[7:], "From index 7 to end"),
        ("text[::-1]", text[::-1], "Reverse string"),
        ("text[::2]", text[::2], "Every 2nd character"),
        ("text[1:-1]", text[1:-1], "Remove first and last char")
    ]
    
    for code, result, description in examples:
        print(f"{code:<12} → '{result}' ({description})")
    print()

def demonstrate_practical_examples():
    print("=== Practical Examples ===")
    
    # Working with data
    temperatures = [72, 75, 73, 78, 80, 77, 74, 71, 69, 70]
    print(f"Temperature data: {temperatures}")
    print(f"Last 3 days: {temperatures[-3:]}")
    print(f"Every other day: {temperatures[::2]}")
    print(f"Descending order: {temperatures[::-1]}")
    print()
    
    # Text processing
    sentence = "The quick brown fox jumps over lazy dog"
    words = sentence.split()
    print(f"Words: {words}")
    print(f"First half: {words[:len(words)//2]}")
    print(f"Last half: {words[len(words)//2:]}")
    print(f"Every other word: {words[::2]}")
    print()

def demonstrate_edge_cases():
    print("=== Edge Cases and Safety ===")
    numbers = [1, 2, 3, 4, 5]
    print(f"Original list: {numbers}")
    print()
    
    examples = [
        ("numbers[10:20]", numbers[10:20], "Out of bounds - no error"),
        ("numbers[1:1]", numbers[1:1], "Empty slice"),
        ("numbers[5:]", numbers[5:], "Start beyond list"),
        ("numbers[-10:2]", numbers[-10:2], "Negative start beyond bounds")
    ]
    
    for code, result, description in examples:
        print(f"{code:<17} → {result} ({description})")
    print()

if __name__ == "__main__":
    demonstrate_basic_slicing()
    demonstrate_step_slicing() 
    demonstrate_string_slicing()
    demonstrate_practical_examples()
    demonstrate_edge_cases()
    
    print("=== Interactive Test ===")
    print("Try your own slicing examples:")
    test_list = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    print(f"test_list = {test_list}")
    print("Examples to try:")
    print("  test_list[2:6]")
    print("  test_list[::-2]") 
    print("  test_list[1::3]")