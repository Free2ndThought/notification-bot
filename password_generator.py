import random

lower_case = 'abcdefghijklmnopqrstuvwxyz'
upper_case = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
numbers = '0123456789'
special_characters = '!@#$%^&*()_+'
consists_of = lower_case + upper_case + numbers + special_characters
password_length = 12

password = "".join(random.sample(consists_of, password_length))

print(password)