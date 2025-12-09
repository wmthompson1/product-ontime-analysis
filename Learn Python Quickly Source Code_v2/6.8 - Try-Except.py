value = input("Please enter a value to divide with:")
value = int(value)

try:
    numeric = 100 // value
    print(numeric)
except:
    print("Error occurred, invalid value provided.")
