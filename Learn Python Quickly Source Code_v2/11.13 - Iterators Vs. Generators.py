for x in [1, 2, 3, 4]:
    print(x)

y = iter([6, 7, 8, 9])
print(y.__next__())
print(y.__next__())
print(y.__next__())


class range_ex:

    # Initializes two elements - i (current item) and num (number for range)
    def __init__(self, num):
        self.i = 0
        self.num = num

    # returns self (returning self is what makes the object iterable)
    def __iter__(self):
        return self

    # when called increment i and return as long as i is less than the ending number
    # otherwise stop iterating
    def __next__(self):
        if self.i < self.num:
            i = self.i
            self.i += 1
            return i
        else:
            raise StopIteration()


def gen_num(start, end):
    while start <= end:
        yield start
        start += 1


num_list = []

for i in gen_num(5, 12):
    num_list.append(i)

print(num_list)

added = (i + i for i in range(1, 5))
print(type(added))
