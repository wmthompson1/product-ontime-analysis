#!/usr/bin/env python3
"""
import re module.
Then create code for test string in '555-1212', 'ILL', '800-555-1212', '123-123-1234' if it matches the pattern of a phone number.

This script uses the re module to check if given strings match the pattern of a phone number. I would like to revise it to replace '555' with '800' in the test strings.


"""
import re

# Define a regex pattern for a phone number
pattern = re.compile(r'\b\d{3}-\d{3}-\d{4}\b')

# Define test strings
test_strings = ['555-1212', 'ILL', '800-555-1212', '123-123-1234']

# Check if the test strings match the pattern
for test_string in test_strings:
    if pattern.match(test_string):
        print(f"{test_string} matches the phone number pattern.")
    else:
        print(f"{test_string} does not match the phone number pattern.")cp
