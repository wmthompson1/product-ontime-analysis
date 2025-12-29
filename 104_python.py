"""
https://www.w3schools.com/python/python_lists.asp

Python Collections (Arrays)
There are four collection data types in the Python programming language:

List is a collection which is ordered and changeable. Allows duplicate members.
Tuple is a collection which is ordered and unchangeable. Allows duplicate members.
Set is a collection which is unordered, unchangeable*, and unindexed. No duplicate members.
Dictionary is a collection which is ordered** and changeable. No duplicate members.

https://www.codequickly.org/bonus

"""
thislist = ["apple", "banana", "cherry", "apple", "cherry"]
print(thislist)

"""
The list() Constructor

"""

thislist = list(("apple", "banana", "cherry")) # note the double round-brackets
print(thislist)
