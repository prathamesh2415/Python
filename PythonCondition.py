# Simple if statement
x = 10
if x > 5:
    print("x is greater than 5")

# if-else statement
y = 3
if y > 5:
    print("y is greater than 5")
else:
    print("y is not greater than 5")

# if-elif-else statement
z = 7
if z > 10:
    print("z is greater than 10")
elif z > 5:
    print("z is greater than 5 but less than or equal to 10")
else:
    print("z is 5 or less")

# Nested if statements
a = 8
if a > 5:
    if a > 7:
        print("a is greater than 7")
    else:
        print("a is greater than 5 but less than or equal to 7")

# Ternary operator (conditional expression)
b = 15
result = "b is even" if b % 2 == 0 else "b is odd"
print(result)

# Using logical operators
c = 20
if c > 10 and c < 30:
    print("c is between 10 and 30")

# Using 'in' keyword
name = "Alice"
if "A" in name:
    print("The name contains the letter A")

# Using 'not' keyword
d = 25
if not d < 20:
    print("d is not less than 20")