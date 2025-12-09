import unittest


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
