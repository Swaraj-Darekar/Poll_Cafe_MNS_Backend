import requests

def test_api():
    print("Testing /superadmin/stats...")
    try:
        response = requests.get("http://localhost:8000/superadmin/stats")
        if response.status_code == 200:
            print("Response:", response.json())
        else:
            print(f"Failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
