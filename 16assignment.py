p_words = None

# YOUR CODE HERE
name = 'school_prompt.txt'
handle = open(name, 'r')
pos = None
p_words = list()

for line in handle:
    words = line.split()
    if len(words) > 0:
        for word in words:
            pos = None
            pos = word.find('p')
            if pos >= 0:
                p_words.append(word.strip())
print(p_words)
print(len(p_words))
