def shopping_list(store, *args):

    shopping_list = []

    for i in args:
        print("Adding {} to list".format(i))
        shopping_list.append(str(store) + " - " + str(i))

    return shopping_list