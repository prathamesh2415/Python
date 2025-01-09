# Function to add two numbers
def add(a, b):
    return a + b

# Function to subtract two numbers
def subtract(a, b):
    return a - b

# Function to multiply two numbers
def multiply(a, b):
    return a * b

# Function to divide two numbers
def divide(a, b):
    if b == 0:
        return "Cannot divide by zero"
    return a / b

# Function to find the factorial of a number
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)

# Function to check if a number is prime
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# Function to find the maximum of three numbers
def max_of_three(a, b, c):
    return max(a, b, c)

# Function to reverse a string
def reverse_string(s):
    return s[::-1]

# Function to check if a string is a palindrome
def is_palindrome(s):
    return s == s[::-1]

# Function to find the length of a list
def list_length(lst):
    return len(lst)

# Examples of using the functions
print(add(2, 3))  # Output: 5
print(subtract(5, 2))  # Output: 3
print(multiply(3, 4))  # Output: 12
print(divide(10, 2))  # Output: 5.0
print(factorial(5))  # Output: 120
print(is_prime(7))  # Output: True
print(max_of_three(1, 5, 3))  # Output: 5
print(reverse_string("hello"))  # Output: "olleh"
print(is_palindrome("racecar"))  # Output: True
print(list_length([1, 2, 3, 4]))  # Output: 4