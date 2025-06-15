sentences = ['Hello world', 'Python is great', 'List comprehensions rock']
long_sentences = [s.upper() for s in sentences if len(s.split()) >= 3]
print("Result:", long_sentences)

# Let's also check each step
for i, s in enumerate(sentences):
    words = s.split()
    print(f"Sentence {i+1}: '{s}'")
    print(f"  Words: {words}")
    print(f"  Word count: {len(words)}")
    print(f"  Passes condition (>= 3): {len(words) >= 3}")
    if len(words) >= 3:
        print(f"  Uppercase: '{s.upper()}'")
    print()