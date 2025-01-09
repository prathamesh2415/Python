# For loop with a list
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)

# For loop with a range
for i in range(5):
    print(i)

# While loop
count = 0
while count < 5:
    print(count)
    count += 1

# Looping through a dictionary
person = {"name": "John", "age": 30, "city": "New York"}
for key in person:
    print(key, person[key])

# Looping through a string
for char in "Hello":
    print(char)

# Nested loops
for i in range(3):
    for j in range(2):
        print(f"i: {i}, j: {j}")

# List comprehension
squares = [x**2 for x in range(10)]
print(squares)

# Looping with enumerate
for index, value in enumerate(fruits):
    print(index, value)

# Looping with zip
names = ["Alice", "Bob", "Charlie"]
ages = [25, 30, 35]
for name, age in zip(names, ages):
    print(f"{name} is {age} years old")