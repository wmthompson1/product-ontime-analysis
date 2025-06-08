#!/usr/bin/env python3
"""
Comprehensive HTTP testing script for your Flask API
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

def test_home():
    """Test the home endpoint"""
    print("=== Testing Home Endpoint ===")
    try:
        response = requests.get(f'{BASE_URL}/')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")
    except Exception as e:
        print(f"Error: {e}\n")

def test_health_check():
    """Test the health check endpoint"""
    print("=== Testing Health Check ===")
    try:
        response = requests.get(f'{BASE_URL}/api/health')
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

def test_create_user():
    """Test creating a new user"""
    print("=== Testing Create User (POST) ===")
    user_data = {
        "name": "John Doe",
        "email": "john@example.com"
    }
    try:
        response = requests.post(f'{BASE_URL}/api/users', json=user_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        return response.json().get('id') if response.status_code == 201 else None
    except Exception as e:
        print(f"Error: {e}\n")
        return None

def test_get_users():
    """Test getting all users"""
    print("=== Testing Get All Users (GET) ===")
    try:
        response = requests.get(f'{BASE_URL}/api/users')
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

def test_get_single_user(user_id):
    """Test getting a single user"""
    if not user_id:
        print("=== Skipping Get Single User (no user ID) ===\n")
        return
    
    print(f"=== Testing Get Single User (GET /api/users/{user_id}) ===")
    try:
        response = requests.get(f'{BASE_URL}/api/users/{user_id}')
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

def test_update_user(user_id):
    """Test updating a user"""
    if not user_id:
        print("=== Skipping Update User (no user ID) ===\n")
        return
    
    print(f"=== Testing Update User (PUT /api/users/{user_id}) ===")
    update_data = {
        "name": "John Smith",
        "email": "johnsmith@example.com"
    }
    try:
        response = requests.put(f'{BASE_URL}/api/users/{user_id}', json=update_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

def test_delete_user(user_id):
    """Test deleting a user"""
    if not user_id:
        print("=== Skipping Delete User (no user ID) ===\n")
        return
    
    print(f"=== Testing Delete User (DELETE /api/users/{user_id}) ===")
    try:
        response = requests.delete(f'{BASE_URL}/api/users/{user_id}')
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"Error: {e}\n")

if __name__ == "__main__":
    print("🚀 Testing Flask API Endpoints...\n")
    
    # Test basic endpoints
    test_home()
    test_health_check()
    
    # Test user CRUD operations
    user_id = test_create_user()
    test_get_users()
    test_get_single_user(user_id)
    test_update_user(user_id)
    test_get_single_user(user_id)  # Check if update worked
    test_delete_user(user_id)
    test_get_users()  # Check if delete worked
    
    print("✅ API testing complete!")