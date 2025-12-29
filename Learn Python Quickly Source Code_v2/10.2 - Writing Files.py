
target_file = open("write_test.txt", "a")

target_file.write(
    "All we have to do is type in a sentence to write to the document." + "\n")
target_file.write(
    "Using the write function multiple times will write multiples lines to the document. \n")

list_to_write = ["This", " is", " our", " word", " list"]

for w in list_to_write:
    target_file.write(w)

target_file.close()
