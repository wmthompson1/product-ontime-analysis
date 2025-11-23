### Data Types ###

string_1 = "This is a string."
string_2 = 'This is also a string.'

# The 97 here is a string

Stringy = "97"

# Here it is a number

Numerical = 97

Str_1 = "Words "
Str_2 = "and "
Str_3 = "more words."

Str_4 = Str_1 + Str_2 + Str_3

print(Str_4)

String_to_print = "With the modulus operator, you can add %s, integers like %d, or even floats like %2.1f." % (
    "strings", 25, 12.34)

print(String_to_print)

String_to_print = "With the modulus operator, you can add {0:s}, integers like {1:d}, or even floats like {2:2.1f}."

print(String_to_print.format("strings", 25, 12.34))

### Data Structures ###

fruits = ["apple", "pear", "orange", "banana"]
Apple = fruits[0]

this_is_a_tuple = ("these", "are", "values", "in", "a", "tuple")
Word = this_is_a_tuple[0]

Dict_example = {"key1": 39}
Dict_example2 = {"key1": 39, "key2": 21, "key3": 54}
Dict_example3 = dict(key1=39, key2=21, key3=54)

number = Dict_example3["key1"]

Dict_example3["key1"] = 99

Dict_example4 = {}

Dict_example4["key1"] = 109

del Dict_example4["key1"]
