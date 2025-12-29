"""
https://github.com/dennisbakhuis/python10minutesaday/blob/master/9%20-%20Python%2010min%20a%20day%20-%20Defining%20functions%20and%20stop%20repeating%20yourself.ipynb


"""
# a function that returns values

def add_one(value):
    """
    Adding one to the provided value
    """
    new_value = value + 1
    return new_value

result = add_one(13)
print(f'Adding 1 to 25 gives us {add_one(25)}')    