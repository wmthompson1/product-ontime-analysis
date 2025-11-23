# save this in another file and then import it

from argtostring import args_to_string


def args_to_string(*args):
    string_1 = ""

    for i in args:
        string_1 += i + " "

    return string_1


string_1 = args_to_string('Hello,', 'this', 'should', 'be', 'one', 'string.')
print(string_1)
