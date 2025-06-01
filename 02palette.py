#!/usr/bin/env python3
"""
Create code that will use regex to replace all occurrences of 'dog' with 'cat' 
in the string 'dog cat dog cat dog'. Save the result in a variable called 'NewString'.
"""
import re
import os

# First, create the sample.txt file with the content
original_string = "dog cat dog cat dog"
with open('sample.txt', 'w') as file:
    file.write(original_string)

# Read the file
with open('sample.txt', 'r') as file:
    file_content = file.read()

# Replace all occurrences of 'dog' with 'cat' in the string
NewString = re.sub(r'dog', 'cat', file_content)

print(f"Original: {file_content}")
print(f"Modified: {NewString}")

# save the NewString back to the file
with open('sample.txt', 'w') as file:
    file.write(NewString)

# Rename files with filename containing 'sample' by replacing the string 'sample' with 'new'

for filename in os.listdir('.'):  
    if 'sample' in filename:
        new_filename = filename.replace('sample', 'new')
        os.rename(filename, new_filename)


