
def factorial_calculation(num):
    current_value = 1

    for i in range(1, num + 1):
        current_value *= i

    return current_value


def recursive_calculation(num):
    if num != 1:
        return num * recursive_calculation(num - 1)
    else:
        return num


print(factorial_calculation(5))
print(recursive_calculation(5))
