# Python Input/Output Examples

# Taking input from the user
name = input("Enter your name: ")
print("Hello, " + name + "!")

# Reading an integer input
age = int(input("Enter your age: "))
print("You are " + str(age) + " years old.")

# Reading a float input
height = float(input("Enter your height in meters: "))
print("Your height is " + str(height) + " meters.")

# Writing to a file
with open("info.txt", "w") as file:
    file.write("Hello, this is a test file.\n")
    file.write("Name: " + name + "\n")
    file.write("Age: " + str(age) + "\n")
    file.write("Height: " + str(height) + " meters\n")

# Reading from a file
with open("info.txt", "r") as file:
    content = file.read()
    print("\nContent of the file:")
    print(content)

# Appending to a file
with open("info.txt", "a") as file:
    file.write("This is an appended line.\n")

# Reading line by line from a file
with open("info.txt", "r") as file:
    print("Reading file line by line:")
    for line in file:
        print(line, end='')

# Using 'with' statement for file operations ensures the file is properly closed after its suite finishes