difficulty = input(
    "Choose ‘1’ for 'Easy, '2' for ‘Normal’, '3' for ‘Hard’, or '4' for ‘Impossible’:")

if difficulty == "1":
    print("Easy difficulty chosen.")
elif difficulty == "2":
    print("Normal difficulty chosen.")
elif difficulty == "3":
    print("Hard difficulty chosen.")
elif difficulty == "4":
    print("Impossible difficulty chosen.")
else:
    print("Please enter a valid difficulty.")
