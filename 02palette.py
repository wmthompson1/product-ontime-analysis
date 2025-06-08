import os

folder_name = "/home/runner/workspace/"
full_path = os.path.join(folder_name,"romeo.txt")
print (full_path)

with open(full_path, "r") as file:
    contents = file.read()
    print(contents)

num_list = [92, 11, 33, 59, 12, 65, 9, 43, 55, 1]

search_term = input("Enter a number to divide by:")

print("Starting loop")

for num in num_list:
    try:
        num = num // int(search_term)
        print(num)
    except:
        print("Incompatible divisor entered.")
        break

print("Loop ended")