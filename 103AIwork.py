
import requests
import json

# OpenAI API configuration
url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_KEY_HERE"  # Replace with your actual API key
}

data = {
    "model": "gpt-4o-mini",
    "store": True,
    "messages": [
        {"role": "user", "content": "write a haiku about ai"}
    ]
}

try:
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"An error occurred: {e}")
