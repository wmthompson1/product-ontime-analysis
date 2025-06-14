# Python List Comprehensions: A Complete 4-Page Guide

## Page 1: Introduction and Basic Syntax

### What are List Comprehensions?

List comprehensions are a concise and powerful way to create lists in Python. They allow you to generate new lists by applying an expression to each item in an existing iterable (like a list, tuple, or range), optionally filtering items based on a condition.

### Why Use List Comprehensions?

**Benefits:**
- **Concise**: Replace multiple lines of code with a single expression
- **Readable**: More Pythonic and expressive than traditional loops
- **Efficient**: Generally faster than equivalent for loops
- **Functional**: Encourages functional programming patterns

**Traditional approach vs List Comprehension:**
```python
# Traditional for loop
squares = []
for x in range(10):
    squares.append(x**2)

# List comprehension
squares = [x**2 for x in range(10)]
```

### Basic Syntax

The general syntax of a list comprehension is:
```python
[expression for item in iterable]
```

**Components:**
- **expression**: What you want to do with each item
- **item**: Variable representing each element
- **iterable**: The source data (list, range, string, etc.)

### Simple Examples

**Creating a list of squares:**
```python
squares = [x**2 for x in range(1, 6)]
# Result: [1, 4, 9, 16, 25]
```

**Converting strings to uppercase:**
```python
words = ['hello', 'world', 'python']
uppercase = [word.upper() for word in words]
# Result: ['HELLO', 'WORLD', 'PYTHON']
```

**Extracting characters from a string:**
```python
letters = [char for char in 'Python']
# Result: ['P', 'y', 't', 'h', 'o', 'n']
```

**Mathematical operations:**
```python
numbers = [1, 2, 3, 4, 5]
doubled = [n * 2 for n in numbers]
# Result: [2, 4, 6, 8, 10]

celsius = [0, 20, 30, 40]
fahrenheit = [(temp * 9/5) + 32 for temp in celsius]
# Result: [32.0, 68.0, 86.0, 104.0]
```

### Working with Different Data Types

**Processing tuples:**
```python
coordinates = [(1, 2), (3, 4), (5, 6)]
x_values = [point[0] for point in coordinates]
# Result: [1, 3, 5]
```

**String manipulation:**
```python
names = ['alice', 'bob', 'charlie']
capitalized = [name.capitalize() for name in names]
# Result: ['Alice', 'Bob', 'Charlie']
```

**Nested data structures:**
```python
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [num for row in matrix for num in row]
# Result: [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

---

## Page 2: Conditional Logic and Filtering

### Adding Conditions with if

You can add conditional logic to filter items using the `if` clause:
```python
[expression for item in iterable if condition]
```

### Filtering Examples

**Even numbers only:**
```python
numbers = range(1, 11)
evens = [x for x in numbers if x % 2 == 0]
# Result: [2, 4, 6, 8, 10]
```

**Positive numbers:**
```python
mixed_numbers = [-3, -1, 0, 2, 5, -8, 9]
positives = [x for x in mixed_numbers if x > 0]
# Result: [2, 5, 9]
```

**Filtering strings by length:**
```python
words = ['cat', 'elephant', 'dog', 'butterfly', 'ant']
long_words = [word for word in words if len(word) > 3]
# Result: ['elephant', 'butterfly']
```

### Conditional Expressions (Ternary Operator)

You can use conditional expressions within the expression part:
```python
[expression_if_true if condition else expression_if_false for item in iterable]
```

**Examples:**
```python
numbers = [1, 2, 3, 4, 5]
result = ['even' if x % 2 == 0 else 'odd' for x in numbers]
# Result: ['odd', 'even', 'odd', 'even', 'odd']

grades = [85, 92, 78, 96, 65]
pass_fail = ['Pass' if grade >= 80 else 'Fail' for grade in grades]
# Result: ['Pass', 'Pass', 'Fail', 'Pass', 'Fail']
```

### Complex Filtering Conditions

**Multiple conditions with and/or:**
```python
numbers = range(1, 101)
special = [x for x in numbers if x % 3 == 0 and x % 5 == 0]
# Result: [15, 30, 45, 60, 75, 90]

words = ['apple', 'banana', 'apricot', 'cherry', 'avocado']
a_words = [word for word in words if word.startswith('a') and len(word) > 5]
# Result: ['apricot', 'avocado']
```

**Using functions in conditions:**
```python
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

primes = [x for x in range(2, 50) if is_prime(x)]
# Result: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
```

### Working with String Data

**Filtering and transforming text:**
```python
sentences = ['Hello world', 'Python is great', 'List comprehensions rock']
long_sentences = [s.upper() for s in sentences if len(s.split()) >= 3]
# Result: ['LIST COMPREHENSIONS ROCK']

# Extract words containing specific letters
text = "The quick brown fox jumps over the lazy dog"
words_with_o = [word for word in text.split() if 'o' in word.lower()]
# Result: ['brown', 'fox', 'over', 'dog']
```

### Filtering Dictionaries and Complex Objects

**Working with dictionaries:**
```python
students = [
    {'name': 'Alice', 'grade': 85, 'age': 20},
    {'name': 'Bob', 'grade': 92, 'age': 19},
    {'name': 'Charlie', 'grade': 78, 'age': 21}
]

high_achievers = [student['name'] for student in students if student['grade'] > 80]
# Result: ['Alice', 'Bob']

young_students = [student for student in students if student['age'] < 21]
# Result: [{'name': 'Alice', 'grade': 85, 'age': 20}, {'name': 'Bob', 'grade': 92, 'age': 19}]
```

---

## Page 3: Advanced Techniques and Nested Comprehensions

### Nested List Comprehensions

List comprehensions can be nested to work with multi-dimensional data structures.

**Basic nested comprehension:**
```python
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [item for sublist in matrix for item in sublist]
# Result: [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

**Creating a multiplication table:**
```python
multiplication_table = [[i * j for j in range(1, 6)] for i in range(1, 6)]
# Result: [[1, 2, 3, 4, 5], [2, 4, 6, 8, 10], [3, 6, 9, 12, 15], [4, 8, 12, 16, 20], [5, 10, 15, 20, 25]]
```

**Matrix operations:**
```python
# Transpose a matrix
matrix = [[1, 2, 3], [4, 5, 6]]
transposed = [[row[i] for row in matrix] for i in range(len(matrix[0]))]
# Result: [[1, 4], [2, 5], [3, 6]]

# Element-wise operations
matrix1 = [[1, 2], [3, 4]]
matrix2 = [[5, 6], [7, 8]]
added = [[matrix1[i][j] + matrix2[i][j] for j in range(len(matrix1[0]))] 
         for i in range(len(matrix1))]
# Result: [[6, 8], [10, 12]]
```

### Working with Multiple Iterables

**Using zip() for parallel iteration:**
```python
names = ['Alice', 'Bob', 'Charlie']
ages = [25, 30, 35]
cities = ['New York', 'London', 'Tokyo']

info = [f"{name}, {age}, {city}" for name, age, city in zip(names, ages, cities)]
# Result: ['Alice, 25, New York', 'Bob, 30, London', 'Charlie, 35, Tokyo']
```

**Cartesian product:**
```python
colors = ['red', 'blue']
sizes = ['small', 'large']
combinations = [f"{color} {size}" for color in colors for size in sizes]
# Result: ['red small', 'red large', 'blue small', 'blue large']
```

### Advanced Filtering and Processing

**Chaining operations:**
```python
numbers = range(1, 21)
result = [str(x**2) for x in numbers if x % 3 == 0]
# Result: ['9', '36', '81', '144', '225', '324']
```

**Processing file-like operations:**
```python
text = """Python is powerful
List comprehensions are elegant
Code should be readable"""

# Get words longer than 5 characters from all lines
long_words = [word for line in text.split('\n') 
              for word in line.split() if len(word) > 5]
# Result: ['Python', 'powerful', 'comprehensions', 'elegant', 'should', 'readable']
```

### Working with Enumerate and Range

**Using enumerate for index-value pairs:**
```python
fruits = ['apple', 'banana', 'cherry']
indexed = [f"{i}: {fruit}" for i, fruit in enumerate(fruits)]
# Result: ['0: apple', '1: banana', '2: cherry']

# Only even indices
even_indexed = [fruit for i, fruit in enumerate(fruits) if i % 2 == 0]
# Result: ['apple', 'cherry']
```

**Complex range operations:**
```python
# Create a pattern
pattern = [x if x % 2 == 0 else -x for x in range(1, 11)]
# Result: [-1, 2, -3, 4, -5, 6, -7, 8, -9, 10]

# Generate coordinates
coordinates = [(x, y) for x in range(3) for y in range(3) if x != y]
# Result: [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)]
```

### Function Calls in List Comprehensions

**Applying functions to elements:**
```python
import math

numbers = [1, 4, 9, 16, 25]
square_roots = [math.sqrt(x) for x in numbers]
# Result: [1.0, 2.0, 3.0, 4.0, 5.0]

# Using lambda functions
words = ['hello', 'world', 'python']
lengths = [len(word) for word in words]
# Result: [5, 5, 6]

# Method calls
sentences = ['  hello world  ', '  python programming  ']
cleaned = [s.strip().title() for s in sentences]
# Result: ['Hello World', 'Python Programming']
```

---

## Page 4: Best Practices, Performance, and Alternatives

### Best Practices

**1. Keep it readable:**
```python
# Good: Clear and concise
evens = [x for x in range(10) if x % 2 == 0]

# Bad: Too complex for a single line
result = [x**2 + y**3 for x in range(10) for y in range(5) 
          if x > 2 and y < 3 and (x + y) % 2 == 0]

# Better: Break into multiple steps or use traditional loops
complex_result = []
for x in range(10):
    for y in range(5):
        if x > 2 and y < 3 and (x + y) % 2 == 0:
            complex_result.append(x**2 + y**3)
```

**2. Use meaningful variable names:**
```python
# Good
user_names = [user.name for user in users if user.is_active]

# Less clear
data = [u.n for u in users if u.a]
```

**3. Limit nesting depth:**
```python
# Acceptable
matrix_sum = [sum(row) for row in matrix]

# Getting complex - consider alternatives
result = [item.upper() for sublist in data 
          for item in sublist if condition(item)]
```

### Performance Considerations

**List comprehensions vs traditional loops:**
```python
import time

# Performance comparison example
n = 100000

# List comprehension (generally faster)
start = time.time()
squares_lc = [x**2 for x in range(n)]
lc_time = time.time() - start

# Traditional loop
start = time.time()
squares_loop = []
for x in range(n):
    squares_loop.append(x**2)
loop_time = time.time() - start

print(f"List comprehension: {lc_time:.4f}s")
print(f"Traditional loop: {loop_time:.4f}s")
```

**Memory considerations:**
```python
# For large datasets, consider generator expressions
large_squares = (x**2 for x in range(1000000))  # Generator (memory efficient)
large_list = [x**2 for x in range(1000000)]     # List (uses more memory)
```

### Alternative Comprehensions

**Dictionary comprehensions:**
```python
numbers = range(1, 6)
squared_dict = {x: x**2 for x in numbers}
# Result: {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}

words = ['hello', 'world', 'python']
length_dict = {word: len(word) for word in words}
# Result: {'hello': 5, 'world': 5, 'python': 6}
```

**Set comprehensions:**
```python
numbers = [1, 2, 2, 3, 3, 3, 4]
unique_squares = {x**2 for x in numbers}
# Result: {1, 4, 9, 16}
```

**Generator expressions:**
```python
# Memory-efficient for large datasets
squares_gen = (x**2 for x in range(1000000))
first_ten = [next(squares_gen) for _ in range(10)]
# Result: [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

### When NOT to Use List Comprehensions

**1. Complex logic:**
```python
# Don't do this
result = [complex_function(x) for x in data 
          if complex_condition(x) and another_condition(x)]

# Do this instead
result = []
for x in data:
    if complex_condition(x) and another_condition(x):
        processed = complex_function(x)
        if processed:  # Additional logic
            result.append(processed)
```

**2. Side effects:**
```python
# Don't use comprehensions for side effects
[print(x) for x in numbers]  # Bad practice

# Use regular loops
for x in numbers:
    print(x)  # Better
```

### Real-World Examples

**Data processing:**
```python
# Processing CSV-like data
data = [
    "John,25,Engineer",
    "Jane,30,Designer", 
    "Bob,35,Manager"
]

employees = [{'name': row.split(',')[0], 
              'age': int(row.split(',')[1]),
              'role': row.split(',')[2]} for row in data]

# Filter and transform
senior_staff = [emp['name'] for emp in employees if emp['age'] > 28]
```

**Web scraping/API responses:**
```python
# Extracting data from API responses
api_response = [
    {'id': 1, 'name': 'Product A', 'price': 10.99, 'in_stock': True},
    {'id': 2, 'name': 'Product B', 'price': 15.50, 'in_stock': False},
    {'id': 3, 'name': 'Product C', 'price': 8.75, 'in_stock': True}
]

available_products = [f"{item['name']}: ${item['price']}" 
                      for item in api_response if item['in_stock']]
# Result: ['Product A: $10.99', 'Product C: $8.75']
```

**Mathematical computations:**
```python
# Statistical operations
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
mean = sum(data) / len(data)
deviations = [x - mean for x in data]
squared_deviations = [d**2 for d in deviations]
variance = sum(squared_deviations) / len(squared_deviations)
```

### Summary

List comprehensions are a powerful Python feature that can make your code more concise and readable when used appropriately. Key takeaways:

- Use for simple to moderately complex transformations and filtering
- Prioritize readability over brevity
- Consider alternatives (generators, traditional loops) for complex logic
- Practice with real-world data to master the syntax
- Remember that list comprehensions are expressions, not statements

Master list comprehensions and you'll write more Pythonic, efficient code!