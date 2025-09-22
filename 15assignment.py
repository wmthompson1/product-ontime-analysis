name = 'words.txt'
handle = open(name, 'r')
third = None
three =list()

for line in handle:
    words = line.split()
    if len(words) > 2:
        third = words[2]
        three.append(third)

print(three)
