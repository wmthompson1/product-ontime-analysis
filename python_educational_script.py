#!/usr/bin/env python3
"""
Python Educational Script for Beginners
========================================

This interactive script helps beginners learn basic programming concepts
through engaging examples and hands-on exercises.

Author: AI Assistant
Date: July 28, 2025
"""

import random
import time
import sys
from typing import List, Dict, Any

class PythonLearningTool:
    """Interactive Python learning tool for beginners."""
    
    def __init__(self):
        self.user_name = ""
        self.current_lesson = 0
        self.progress = {}
        
    def welcome(self):
        """Welcome message and setup."""
        print("🐍 Welcome to Python Learning Adventure!")
        print("=" * 50)
        print("This interactive script will teach you basic programming concepts")
        print("through fun examples and exercises.\n")
        
        self.user_name = input("What's your name? ").strip()
        if not self.user_name:
            self.user_name = "Student"
            
        print(f"\nHello {self.user_name}! Let's start learning Python together! 🚀\n")
        time.sleep(1)
    
    def show_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 50)
        print(f"🎓 Python Learning Menu - Welcome {self.user_name}!")
        print("=" * 50)
        print("1. Variables and Data Types")
        print("2. Basic Operations and Math")
        print("3. Lists and Collections")
        print("4. Conditional Statements (if/else)")
        print("5. Loops and Iteration")
        print("6. Functions Basics")
        print("7. Simple Games")
        print("8. Mini Projects")
        print("9. View Progress")
        print("0. Exit")
        print("=" * 50)
    
    def lesson_variables(self):
        """Teach variables and data types."""
        print("\n📝 Lesson 1: Variables and Data Types")
        print("-" * 40)
        
        print("Variables are like boxes that store information.")
        print("Let's see some examples:\n")
        
        # Demonstrate variables
        student_name = self.user_name
        student_age = 15
        is_learning = True
        favorite_number = 3.14
        
        print(f"student_name = '{student_name}'    # String (text)")
        print(f"student_age = {student_age}               # Integer (whole number)")
        print(f"is_learning = {is_learning}            # Boolean (True/False)")
        print(f"favorite_number = {favorite_number}         # Float (decimal number)")
        
        print("\n🎯 Try it yourself!")
        try:
            user_age = input("Enter your age: ")
            user_age = int(user_age)
            print(f"Great! You're {user_age} years old.")
            
            favorite_color = input("What's your favorite color? ")
            print(f"Nice choice! {favorite_color} is a beautiful color.")
            
            print(f"\n✅ You created variables! Here's what we stored:")
            print(f"   Name: {self.user_name}")
            print(f"   Age: {user_age}")
            print(f"   Favorite Color: {favorite_color}")
            
            self.progress["variables"] = True
            
        except ValueError:
            print("Oops! That's not a valid number. Let's move on!")
    
    def lesson_math(self):
        """Teach basic operations and math."""
        print("\n🔢 Lesson 2: Basic Operations and Math")
        print("-" * 40)
        
        print("Python can be used as a calculator!")
        print("Let's learn the basic operations:\n")
        
        a, b = 10, 3
        print(f"Let's use numbers: a = {a}, b = {b}")
        print(f"a + b = {a + b}    # Addition")
        print(f"a - b = {a - b}    # Subtraction")
        print(f"a * b = {a * b}   # Multiplication")
        print(f"a / b = {a / b:.2f}  # Division")
        print(f"a ** b = {a ** b}  # Power (a to the power of b)")
        print(f"a % b = {a % b}    # Remainder (modulo)")
        
        print("\n🎯 Math Challenge!")
        try:
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            
            print(f"\nResults with {num1} and {num2}:")
            print(f"Sum: {num1 + num2}")
            print(f"Difference: {num1 - num2}")
            print(f"Product: {num1 * num2}")
            if num2 != 0:
                print(f"Division: {num1 / num2:.2f}")
            else:
                print("Cannot divide by zero!")
                
            self.progress["math"] = True
            
        except ValueError:
            print("Please enter valid numbers next time!")
    
    def lesson_lists(self):
        """Teach lists and collections."""
        print("\n📋 Lesson 3: Lists and Collections")
        print("-" * 40)
        
        print("Lists are like containers that hold multiple items.")
        print("They're super useful for storing collections of data!\n")
        
        # Demonstrate lists
        fruits = ["apple", "banana", "orange", "grape"]
        numbers = [1, 2, 3, 4, 5]
        mixed_list = ["hello", 42, True, 3.14]
        
        print("Here are some example lists:")
        print(f"fruits = {fruits}")
        print(f"numbers = {numbers}")
        print(f"mixed_list = {mixed_list}")
        
        print("\n🔍 List Operations:")
        print(f"First fruit: {fruits[0]}")
        print(f"Last fruit: {fruits[-1]}")
        print(f"Number of fruits: {len(fruits)}")
        
        # Add item
        fruits.append("strawberry")
        print(f"After adding strawberry: {fruits}")
        
        print("\n🎯 Create Your Own List!")
        user_list = []
        print("Let's create a list of your favorite things!")
        
        for i in range(3):
            item = input(f"Enter favorite thing #{i+1}: ")
            user_list.append(item)
        
        print(f"\nYour list: {user_list}")
        print(f"You added {len(user_list)} items!")
        
        self.progress["lists"] = True
    
    def lesson_conditionals(self):
        """Teach conditional statements."""
        print("\n🤔 Lesson 4: Conditional Statements (if/else)")
        print("-" * 40)
        
        print("Conditionals help programs make decisions!")
        print("Just like: 'IF it's raining, THEN take an umbrella'\n")
        
        # Demonstrate conditionals
        weather = "sunny"
        print(f"weather = '{weather}'")
        print("\nif weather == 'sunny':")
        print("    print('Perfect day for a picnic!')")
        print("else:")
        print("    print('Maybe stay inside today')")
        
        if weather == "sunny":
            print("→ Perfect day for a picnic!")
        else:
            print("→ Maybe stay inside today")
        
        print("\n🎯 Number Guessing Challenge!")
        secret_number = random.randint(1, 10)
        
        try:
            guess = int(input("I'm thinking of a number between 1-10. Guess: "))
            
            if guess == secret_number:
                print("🎉 Amazing! You guessed it!")
            elif guess < secret_number:
                print(f"Too low! The number was {secret_number}")
            else:
                print(f"Too high! The number was {secret_number}")
                
            self.progress["conditionals"] = True
            
        except ValueError:
            print("Please enter a valid number next time!")
    
    def lesson_loops(self):
        """Teach loops and iteration."""
        print("\n🔄 Lesson 5: Loops and Iteration")
        print("-" * 40)
        
        print("Loops help us repeat actions without writing the same code over and over!")
        print("There are two main types: 'for' loops and 'while' loops\n")
        
        print("🔁 For Loop Example:")
        print("for i in range(5):")
        print("    print(f'Count: {i}')")
        print("\nOutput:")
        
        for i in range(5):
            print(f"Count: {i}")
            time.sleep(0.5)
        
        print("\n🔁 While Loop Example:")
        print("countdown = 3")
        print("while countdown > 0:")
        print("    print(f'{countdown}...')")
        print("    countdown -= 1")
        print("print('Blast off! 🚀')")
        print("\nOutput:")
        
        countdown = 3
        while countdown > 0:
            print(f"{countdown}...")
            countdown -= 1
            time.sleep(0.8)
        print("Blast off! 🚀")
        
        print("\n🎯 Create Your Pattern!")
        try:
            num_stars = int(input("How many lines of stars do you want? "))
            for i in range(1, num_stars + 1):
                print("⭐ " * i)
                
            self.progress["loops"] = True
            
        except ValueError:
            print("Please enter a valid number!")
    
    def lesson_functions(self):
        """Teach function basics."""
        print("\n🛠️ Lesson 6: Functions Basics")
        print("-" * 40)
        
        print("Functions are like recipes - they take ingredients (inputs)")
        print("and create something useful (outputs)!\n")
        
        def greet_person(name):
            return f"Hello, {name}! Nice to meet you!"
        
        def add_numbers(x, y):
            return x + y
        
        def create_story(character, place):
            return f"Once upon a time, {character} went to {place} and had an amazing adventure!"
        
        print("Here are some example functions:")
        print("\ndef greet_person(name):")
        print("    return f'Hello, {name}! Nice to meet you!'")
        print(f"\nResult: {greet_person(self.user_name)}")
        
        print("\ndef add_numbers(x, y):")
        print("    return x + y")
        print(f"\nResult: add_numbers(5, 3) = {add_numbers(5, 3)}")
        
        print("\n🎯 Create Your Story!")
        character = input("Enter a character name: ")
        place = input("Enter a place: ")
        
        story = create_story(character, place)
        print(f"\n📚 Your Story:")
        print(story)
        
        self.progress["functions"] = True
    
    def simple_games(self):
        """Play simple games to reinforce learning."""
        print("\n🎮 Lesson 7: Simple Games")
        print("-" * 40)
        
        games = [
            "Number Guessing Game",
            "Word Length Challenge",
            "Math Quiz"
        ]
        
        print("Choose a game:")
        for i, game in enumerate(games, 1):
            print(f"{i}. {game}")
        
        try:
            choice = int(input("Enter game number: "))
            
            if choice == 1:
                self.number_guessing_game()
            elif choice == 2:
                self.word_length_game()
            elif choice == 3:
                self.math_quiz_game()
            else:
                print("Invalid choice!")
                
        except ValueError:
            print("Please enter a valid number!")
    
    def number_guessing_game(self):
        """Number guessing game."""
        print("\n🎯 Number Guessing Game")
        print("I'm thinking of a number between 1 and 20!")
        
        secret = random.randint(1, 20)
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts:
            try:
                guess = int(input(f"Attempt {attempts + 1}/{max_attempts} - Your guess: "))
                attempts += 1
                
                if guess == secret:
                    print(f"🎉 Congratulations! You got it in {attempts} attempts!")
                    self.progress["games"] = True
                    return
                elif guess < secret:
                    print("Too low! 📈")
                else:
                    print("Too high! 📉")
                    
            except ValueError:
                print("Please enter a valid number!")
                
        print(f"Game over! The number was {secret}. Better luck next time!")
    
    def word_length_game(self):
        """Word length challenge."""
        print("\n📝 Word Length Challenge")
        print("I'll give you words, and you guess how many letters they have!")
        
        words = ["python", "programming", "computer", "algorithm", "function"]
        score = 0
        
        for word in random.sample(words, 3):
            try:
                guess = int(input(f"How many letters in '{word}'? "))
                actual = len(word)
                
                if guess == actual:
                    print("✅ Correct!")
                    score += 1
                else:
                    print(f"❌ Close! '{word}' has {actual} letters.")
                    
            except ValueError:
                print("Please enter a number!")
        
        print(f"\nFinal Score: {score}/3")
        if score >= 2:
            self.progress["games"] = True
    
    def math_quiz_game(self):
        """Simple math quiz."""
        print("\n🔢 Math Quiz Challenge")
        print("Solve these math problems!")
        
        score = 0
        for i in range(3):
            a = random.randint(1, 10)
            b = random.randint(1, 10)
            operation = random.choice(['+', '-', '*'])
            
            if operation == '+':
                answer = a + b
            elif operation == '-':
                answer = a - b
            else:
                answer = a * b
            
            try:
                user_answer = int(input(f"Problem {i+1}: {a} {operation} {b} = "))
                
                if user_answer == answer:
                    print("✅ Correct!")
                    score += 1
                else:
                    print(f"❌ The answer was {answer}")
                    
            except ValueError:
                print("Please enter a number!")
        
        print(f"\nQuiz Score: {score}/3")
        if score >= 2:
            self.progress["games"] = True
    
    def mini_projects(self):
        """Mini coding projects."""
        print("\n🚀 Lesson 8: Mini Projects")
        print("-" * 40)
        
        projects = [
            "Personal Information Display",
            "Simple Calculator",
            "To-Do List Manager"
        ]
        
        print("Choose a project:")
        for i, project in enumerate(projects, 1):
            print(f"{i}. {project}")
        
        try:
            choice = int(input("Enter project number: "))
            
            if choice == 1:
                self.personal_info_project()
            elif choice == 2:
                self.calculator_project()
            elif choice == 3:
                self.todo_project()
            else:
                print("Invalid choice!")
                
        except ValueError:
            print("Please enter a valid number!")
    
    def personal_info_project(self):
        """Personal information display project."""
        print("\n👤 Personal Information Display")
        print("Let's create a program that displays personal information!")
        
        name = input("Enter your name: ")
        age = input("Enter your age: ")
        hobby = input("Enter your favorite hobby: ")
        color = input("Enter your favorite color: ")
        
        print("\n" + "=" * 40)
        print("📋 PERSONAL PROFILE")
        print("=" * 40)
        print(f"Name: {name}")
        print(f"Age: {age}")
        print(f"Favorite Hobby: {hobby}")
        print(f"Favorite Color: {color}")
        print("=" * 40)
        
        self.progress["projects"] = True
    
    def calculator_project(self):
        """Simple calculator project."""
        print("\n🔢 Simple Calculator")
        print("Let's build a basic calculator!")
        
        try:
            num1 = float(input("Enter first number: "))
            operation = input("Enter operation (+, -, *, /): ")
            num2 = float(input("Enter second number: "))
            
            if operation == '+':
                result = num1 + num2
            elif operation == '-':
                result = num1 - num2
            elif operation == '*':
                result = num1 * num2
            elif operation == '/':
                if num2 != 0:
                    result = num1 / num2
                else:
                    print("Error: Cannot divide by zero!")
                    return
            else:
                print("Invalid operation!")
                return
            
            print(f"\n🧮 Result: {num1} {operation} {num2} = {result}")
            self.progress["projects"] = True
            
        except ValueError:
            print("Please enter valid numbers!")
    
    def todo_project(self):
        """Simple to-do list project."""
        print("\n📝 To-Do List Manager")
        print("Let's create a simple to-do list!")
        
        todo_list = []
        
        while True:
            print(f"\nCurrent Tasks ({len(todo_list)} items):")
            if todo_list:
                for i, task in enumerate(todo_list, 1):
                    print(f"{i}. {task}")
            else:
                print("No tasks yet!")
            
            print("\nOptions:")
            print("1. Add task")
            print("2. Remove task")
            print("3. Exit")
            
            try:
                choice = int(input("Choose option: "))
                
                if choice == 1:
                    task = input("Enter new task: ")
                    todo_list.append(task)
                    print(f"✅ Added: {task}")
                    
                elif choice == 2:
                    if todo_list:
                        task_num = int(input("Enter task number to remove: "))
                        if 1 <= task_num <= len(todo_list):
                            removed = todo_list.pop(task_num - 1)
                            print(f"❌ Removed: {removed}")
                        else:
                            print("Invalid task number!")
                    else:
                        print("No tasks to remove!")
                        
                elif choice == 3:
                    print("📋 Final to-do list:")
                    for i, task in enumerate(todo_list, 1):
                        print(f"{i}. {task}")
                    self.progress["projects"] = True
                    break
                    
                else:
                    print("Invalid choice!")
                    
            except ValueError:
                print("Please enter a valid number!")
    
    def view_progress(self):
        """Show learning progress."""
        print("\n📊 Your Learning Progress")
        print("-" * 40)
        
        lessons = [
            ("Variables & Data Types", "variables"),
            ("Math & Operations", "math"),
            ("Lists & Collections", "lists"),
            ("Conditional Statements", "conditionals"),
            ("Loops & Iteration", "loops"),
            ("Functions Basics", "functions"),
            ("Games", "games"),
            ("Projects", "projects")
        ]
        
        completed = 0
        total = len(lessons)
        
        for lesson_name, key in lessons:
            status = "✅ Completed" if self.progress.get(key, False) else "⏳ Not Started"
            print(f"{lesson_name}: {status}")
            if self.progress.get(key, False):
                completed += 1
        
        print(f"\nOverall Progress: {completed}/{total} lessons completed")
        
        if completed == total:
            print("🎉 Congratulations! You've completed all lessons!")
            print("You're well on your way to becoming a Python programmer!")
        elif completed >= total // 2:
            print("🚀 Great progress! Keep going!")
        else:
            print("📚 Just getting started! Every expert was once a beginner.")
    
    def run(self):
        """Main program loop."""
        self.welcome()
        
        while True:
            self.show_menu()
            
            try:
                choice = input(f"\n{self.user_name}, choose an option (0-9): ").strip()
                
                if choice == '0':
                    print(f"\n👋 Goodbye, {self.user_name}!")
                    print("Thanks for learning Python with us!")
                    print("Keep practicing and happy coding! 🐍✨")
                    break
                elif choice == '1':
                    self.lesson_variables()
                elif choice == '2':
                    self.lesson_math()
                elif choice == '3':
                    self.lesson_lists()
                elif choice == '4':
                    self.lesson_conditionals()
                elif choice == '5':
                    self.lesson_loops()
                elif choice == '6':
                    self.lesson_functions()
                elif choice == '7':
                    self.simple_games()
                elif choice == '8':
                    self.mini_projects()
                elif choice == '9':
                    self.view_progress()
                else:
                    print("❌ Invalid choice! Please select a number from 0-9.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print(f"\n\n👋 Goodbye, {self.user_name}!")
                print("Thanks for learning with us!")
                break
            except Exception as e:
                print(f"⚠️ Something went wrong: {e}")
                print("Let's try again!")


def main():
    """Main function to run the educational script."""
    try:
        learning_tool = PythonLearningTool()
        learning_tool.run()
    except KeyboardInterrupt:
        print("\n\nThanks for using Python Learning Adventure! 👋")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please try running the script again.")


if __name__ == "__main__":
    main()