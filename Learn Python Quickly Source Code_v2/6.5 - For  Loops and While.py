cats = ['Kitana', 'Fluffy', 'Ben', 'Cookie']

for cat in cats:
    print(cat + " has been fed.")

drinks = {'drink_1': 'coffee', 'drink_2': 'tea'}

for i in drinks:
    print("Drink number = %s, drink = %s" % (i, drinks[i]))

for i, j in drinks.items():
    print("Drink number = %s, drink = %s" % (i, j))

stringy = 'A string.'
for i in stringy:
    print(i)

for x in range(11):
    print(x)

value = 0

while value < 5:
    print("Part of the while loop")
    value = value + 1
else:
    print("The else condition")
