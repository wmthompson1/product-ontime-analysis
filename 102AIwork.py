"""
count the number of words in the file
"""

# YOUR CODE HERE
name = 'my_writing01.txt'
handle = open(name, 'r')
counts = 0

for line in handle:
    words = line.split()
    counts = counts + len(words)

print("count:", counts)
