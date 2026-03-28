import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000/superadmin/wallet/add"

def test_add_money():
    print(f"Testing wallet addition at {API_URL}...")
    try:
        response = requests.post(API_URL, json={"amount": 100.0})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_add_money()
