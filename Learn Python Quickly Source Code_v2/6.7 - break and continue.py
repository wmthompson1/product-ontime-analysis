fruit_list = ['mango', 'lemon', 'banana',
              'apple', 'cherry', 'watermelon', 'orange']

for fruit in fruit_list:
    print(fruit)
    if(fruit == 'apple'):
        print("Apple is in the list")
        break

print("Loop ended")

num_list = [24, 46, 21, 35, 62, 12, 19, 38, 20]

print("Printing only odd numbers")

for i in num_list:
    if i % 2 == 0:
        continue
    print(i)
