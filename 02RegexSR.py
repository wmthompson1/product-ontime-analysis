#!/usr/bin/env python3
"""
I would like to revise the 02RegexSR script to replace '555' with '800' in the test strings.


"""
import re

# Define a regex pattern for a phone number
pattern = re.compile(r'\b\d{3}-\d{3}-\d{4}\b')

# Define test strings
test_strings = ['800-1212', 'ILL', '800-800-1212', '123-123-1234']

# Check if the test strings match the pattern
for test_string in test_strings:
    if pattern.match(test_string):
        print(f"{test_string} matches the phone number pattern.")
    else:
        print(f"{test_string} does not match the phone number pattern.")
