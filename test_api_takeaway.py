import requests
import json

def test_takeaway():
    url = "http://localhost:8000/takeaway/pay"
    data = {"total_amount": 123.45, "payment_method": "cash"}
    try:
        response = requests.post(url, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_takeaway()
