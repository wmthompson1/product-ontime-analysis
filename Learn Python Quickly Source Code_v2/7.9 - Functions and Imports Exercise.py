

# save this in a file called "shopping_list.py"
from shopping_list import shopping_list as SL


def shopping_list(store, *args):

    shopping_list = []

    for i in args:
        print("Adding {} to list".format(i))
        shopping_list.append(str(store) + " - " + str(i))

    return shopping_list


# create a new file in the same directory (or alias the import)

grocery_list = SL("Hilltop Grocery", "bread", "milk", "coffee", "apple juice")
computer_list = SL("Top Computer Parts", "RAM", "keyboard", "USB hub")
print(grocery_list)
print(computer_list)
