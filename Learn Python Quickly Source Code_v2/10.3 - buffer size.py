
target_file = open("test_text", "r")

print(target_file.read(20))

text = target_file.read(20)

while len(text):
    print(text)
    text = target_file.read(20)