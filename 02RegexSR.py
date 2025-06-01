#!/usr/bin/env python3
"""
create code that will use regex to repace all occurences of 'dog' with 'cat' in the string 'dog cat dog cat dog'. Save the result in a variable called 'NewString'.                       
echo "dog cat dog cat dog">> sample.txt


"""
import re
import os

with open('sample.txt', 'r') as file:
    original_string = file.read()

# Replace all occurrences of 'dog' with 'cat' in the string

NewString = re.sub(r'cat', 'dog', original_string)

# save the NewString back to the file
with open('sample.txt', 'w') as file:
    file.write(NewString)

# Rename files with filename containing 'sample' by replacing the string 'sample' with 'new'
for filename in os.listdir('.'):  
    if 'sample' in filename:
        new_filename = filename.replace('sample', 'new')
        os.rename(filename, new_filename)


