##https://www.codequickly.org/bonus
##/Users/williamthompson/bbb/20241019 Python/106_python.py

"""
https://github.com/dennisbakhuis/python10minutesaday/blob/master/9%20-%20Python%2010min%20a%20day%20-%20Defining%20functions%20and%20stop%20repeating%20yourself.ipynb

https://medium.com/@gbemiadekoya/importing-python-libraries-in-vs-code-e9e7806586a7

by using the command palette(ctrl+shift+P), then type in and 
select ‘python:create environment’. 
A venv and conda will pop, then you select venv. 
You will be prompted to 

To import your library, create a new terminal by going to 
the command palette(ctrl+shift+p) and type
‘Python:create terminal’.

In your new terminal, type e.g “pip install pandas” 
or whatever library you want to install and press enter.

"""
import unittest
import pandas


def factorial_calculation(num):
    current_value = 1

    for i in range(1, num + 1):
        current_value *= i

    return current_value


def divide_numbers(r, s):
    if s == 0:
        raise ValueError("Can’t divide by zero.")
    result = r / s
    return result


class Tester(unittest.TestCase):

    def test_factorial(self):
        result = factorial_calculation(5)
        self.assertEqual(result, 120)
    # test wrong
    # self.assertEqual(result, 100)


class TestDiv(unittest.TestCase):

    def test_divide(self):
        result = divide_numbers(-1, -1)
        self.assertEqual(result, 1)
        with self.assertRaises(ValueError):
            divide_numbers(5, 0)


if __name__ == "__main__":
    unittest.main()
