#!/usr/bin/env python3
"""
Simple HTTP testing script for your Flask application
"""
import requests

# Test the main endpoint
def test_home():
    try:
        response = requests.get('http://localhost:5000')
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Flask application...")
    test_home()